"""
智能状态摘要 — 瓶颈检测、镜头分级、失败聚合
替代原始 get_state_for_llm() 的全量 dump
"""

import time


def _now_ts():
    return time.time()


def detect_bottlenecks(memory) -> list:
    """检测卡住 >5分钟的镜头、同类失败聚集、限流模式。"""
    bottlenecks = []
    now = _now_ts()
    stuck_threshold = 300  # 5 minutes

    # 检查 generating 状态卡住的镜头
    for sid, ss in memory.shots.items():
        if ss.status in ('image_generating', 'video_generating'):
            # 从 thought_history 找该镜头的最近一次 tool_call
            last_call = None
            for h in reversed(memory.thought_history):
                if sid in h.get('content', ''):
                    last_call = h
                    break
            if last_call:
                try:
                    ts = last_call['timestamp']
                    if 'T' in ts:
                        age = now - time.mktime(time.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S'))
                        if age > stuck_threshold:
                            bottlenecks.append({
                                'type': 'stuck', 'shot_id': sid,
                                'status': ss.status,
                                'stuck_seconds': int(age),
                                'detail': f'{sid} 卡在 {ss.status} 已 {int(age/60)} 分钟'
                            })
                except (ValueError, OSError):
                    pass

    # 检测限流模式：最近 5 条错误中 ≥3 条是 rate_limit
    recent_errors = [h for h in memory.thought_history[-10:]
                     if h.get('type') in ('error', 'eval')]
    rate_limit_count = sum(1 for e in recent_errors
                          if 'rate_limit' in e.get('content', '').lower())
    if rate_limit_count >= 3:
        bottlenecks.append({
            'type': 'rate_limit_pattern',
            'count': rate_limit_count,
            'detail': f'最近 10 条记录中 {rate_limit_count} 次限流，建议降低并发或暂停'
        })

    # 检测大量同类失败
    image_failed = memory.count_by_status('image_failed')
    video_failed = memory.count_by_status('video_failed')
    total = len(memory.shots)
    if total > 0:
        if image_failed / total > 0.3:
            bottlenecks.append({
                'type': 'mass_image_failure',
                'count': image_failed,
                'total': total,
                'detail': f'图片失败率 {image_failed}/{total} (>30%)，检查 API Key 或网络'
            })
        if video_failed / total > 0.3:
            bottlenecks.append({
                'type': 'mass_video_failure',
                'count': video_failed,
                'total': total,
                'detail': f'视频失败率 {video_failed}/{total} (>30%)，检查 Seedance 配额'
            })

    return bottlenecks


def prioritize_shots(memory) -> dict:
    """将镜头分为关键(角色出场/高潮/转折)和过渡(空镜/建立)。"""
    critical, transition = [], []

    critical_moods = {'紧张', '恐惧', '激昂', '高潮', '转折', '振奋', '悬疑'}
    transition_moods = {'平和', '轻松', '起始', '结束'}

    for sid, ss in memory.shots.items():
        raw = getattr(ss, '_raw', {})
        mood = raw.get('mood', '')
        chars = raw.get('characters', [])
        camera = raw.get('camera_hint', '')
        action = raw.get('action_summary', '')

        score = 0
        if mood in critical_moods:
            score += 2
        if mood in transition_moods:
            score -= 1
        if chars and len(chars) > 0:
            score += 1
        if camera in ('建立远景',):
            score -= 1
        if action and any(kw in action for kw in ('出场', '高潮', '转折', '对峙', '揭示')):
            score += 2

        entry = {'shot_id': sid, 'mood': mood, 'status': ss.status,
                 'characters': [c.get('name', '') for c in chars],
                 'camera': camera, 'failure_reason': ss.failure_reason}

        if score >= 1:
            critical.append(entry)
        else:
            transition.append(entry)

    return {'critical': critical, 'transition': transition}


def summarize_failures(memory) -> str:
    """按类别聚合失败，不逐条罗列。"""
    by_category = {}
    for sid, ss in memory.shots.items():
        if '_failed' not in ss.status:
            continue
        reason = ss.failure_reason or '未知'
        cat = 'unknown'
        for kw, ct in [('rate_limit', 'rate_limit'), ('network', 'network'),
                        ('timeout', 'network'), ('quality', 'quality'),
                        ('config', 'config')]:
            if kw in reason.lower():
                cat = ct
                break
        by_category.setdefault(cat, []).append(sid)

    if not by_category:
        return '无失败'

    lines = ['失败分析:']
    for cat, shots in by_category.items():
        cat_names = {'rate_limit': '限流', 'network': '网络', 'quality': '质量', 'config': '配置', 'unknown': '未知'}
        critical_ids = [s['shot_id'] for s in prioritize_shots(memory).get('critical', [])]
        critical_in = [s for s in shots if s in critical_ids]
        note = ''
        if critical_in:
            note = f' (含关键镜头: {",".join(critical_in)})'
        lines.append(f'- {cat_names.get(cat, cat)}: {len(shots)}次 {",".join(shots)}{note}')

    return '\n'.join(lines)


def cost_summary(memory) -> str:
    """API 调用成本估算。"""
    ce = memory.cost_estimates
    made = ce.get('api_calls_made', 0)
    saved_batch = ce.get('api_calls_saved_by_batch', 0)
    saved_reuse = ce.get('api_calls_saved_by_reuse', 0)
    remaining = ce.get('estimated_remaining', 0)
    return (f'已用: ~{made} API calls | '
            f'批量节省: ~{saved_batch} | 复用节省: ~{saved_reuse} | '
            f'预估剩余: ~{remaining} calls')


def generate_smart_summary(memory) -> str:
    """生成结构化状态摘要，替代原始的 get_state_for_llm()。"""
    total = len(memory.shots)
    image_done = memory.count_by_status('image_done')
    video_done = memory.count_by_status('video_done')
    narration_done = memory.count_by_status('narration_done')
    image_failed = memory.count_by_status('image_failed')
    video_failed = memory.count_by_status('video_failed')
    narration_failed = memory.count_by_status('narration_failed')

    lines = ['=== 整体进度 ===']
    lines.append(f'阶段: {memory.phase}')
    lines.append(f'总镜头: {total}')
    lines.append(f'图片: {image_done}完成 {image_failed}失败')
    lines.append(f'视频: {video_done}完成 {video_failed}失败')
    lines.append(f'配音: {narration_done}完成 {narration_failed}失败')

    bottlenecks = detect_bottlenecks(memory)
    if bottlenecks:
        lines.append('\n=== 瓶颈警报 ===')
        for b in bottlenecks:
            lines.append(f'- {b["detail"]}')

    priority = prioritize_shots(memory)
    critical = priority['critical']
    if critical:
        lines.append('\n=== 关键镜头 ===')
        for s in critical:
            must = ' [必须成功]' if s['status'].endswith('_failed') else ''
            lines.append(f'  {s["shot_id"]}: {s["status"]} | {s["mood"]} | {s["camera"]}{must}')

    transition = priority['transition']
    if transition:
        lines.append('\n=== 过渡镜头 ===')
        for s in transition:
            skip_ok = ' [可跳过]' if s['status'].endswith('_failed') else ''
            lines.append(f'  {s["shot_id"]}: {s["status"]} | {s["camera"]}{skip_ok}')

    failures = summarize_failures(memory)
    if failures != '无失败':
        lines.append(f'\n=== {failures}')

    cs = cost_summary(memory)
    lines.append(f'\n=== 成本 ===')
    lines.append(cs)

    return '\n'.join(lines)
