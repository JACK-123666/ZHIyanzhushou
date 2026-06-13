"""流水线指标采集 — 耗时、成功率、API 调用量"""

import time
import json
import os
from datetime import datetime


class MetricsCollector:
    """单例指标采集器，记录每步耗时和关键计数。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.steps = {}          # {step_name: {count, total_ms, ...}}
        self.current = {}        # {step_name: start_time}
        self.session_count = 0
        self.total_api_calls = 0
        self.total_reused = 0
        self.total_retries = 0
        self.successful_retries = 0
        self.total_shots_processed = 0
        self.total_shots_failed = 0
        self.failures_by_category = {}  # {category: count}
        self.session_timeline = []      # [{step, duration_ms, ...}]
        self.start_time = None

    def start_session(self):
        """整个 session 开始计时"""
        self.start_time = time.time()
        self.session_count += 1

    def start_step(self, step_name: str):
        """某一步开始计时"""
        self.current[step_name] = time.time()

    def end_step(self, step_name: str, **counts):
        """
        某一步结束。counts 可以是任意 kv，如:
          shots_total=10, shots_done=9, api_calls=6, reused=3, retries=2, retries_success=1
        """
        elapsed = (time.time() - self.current.pop(step_name, time.time())) * 1000

        if step_name not in self.steps:
            self.steps[step_name] = {'count': 0, 'total_ms': 0, 'min_ms': float('inf'),
                                     'max_ms': 0, 'counts': {}}
        rec = self.steps[step_name]
        rec['count'] += 1
        rec['total_ms'] += elapsed
        rec['min_ms'] = min(rec['min_ms'], elapsed)
        rec['max_ms'] = max(rec['max_ms'], elapsed)

        # 累积 counts
        for k, v in counts.items():
            rec['counts'][k] = rec['counts'].get(k, 0) + v

        # 全局累积
        self.total_api_calls += counts.get('api_calls', 0)
        self.total_reused += counts.get('reused', 0)
        self.total_retries += counts.get('retries', 0)
        self.successful_retries += counts.get('retries_success', 0)

        self.session_timeline.append({
            'step': step_name, 'duration_ms': round(elapsed),
            'counts': counts, 'time': datetime.now().isoformat()
        })

    def record_failure(self, category: str):
        """记录一次失败分类"""
        self.failures_by_category[category] = self.failures_by_category.get(category, 0) + 1
        self.total_shots_failed += 1

    def record_shot(self, success: bool):
        self.total_shots_processed += 1
        if not success:
            self.total_shots_failed += 1

    def report(self) -> dict:
        """生成完整指标报告"""
        total_ms = (time.time() - self.start_time) * 1000 if self.start_time else 0

        # 计算复用节省率
        total_with_reuse = self.total_api_calls + self.total_reused
        reuse_save_rate = (self.total_reused / total_with_reuse * 100) if total_with_reuse > 0 else 0

        # 重试成功率
        retry_success_rate = (self.successful_retries / self.total_retries * 100) if self.total_retries > 0 else 0

        # 整体成功率
        total_ops = self.total_shots_processed or (self.total_api_calls + self.total_reused)
        success_rate = ((total_ops - self.total_shots_failed) / total_ops * 100) if total_ops > 0 else 0

        # 每步平均耗时
        step_avg = {}
        for name, rec in self.steps.items():
            step_avg[name] = {
                'avg_ms': round(rec['total_ms'] / rec['count']) if rec['count'] else 0,
                'count': rec['count'],
                'counts': rec['counts'],
            }

        return {
            'total_time_sec': round(total_ms / 1000, 1),
            'sessions': self.session_count,
            'steps': step_avg,
            # Resume-ready 指标
            'api_calls_saved_by_reuse': self.total_reused,
            'reuse_save_rate_pct': round(reuse_save_rate, 1),
            'retry_success_rate_pct': round(retry_success_rate, 1),
            'overall_success_rate_pct': round(success_rate, 1),
            'failures_by_category': self.failures_by_category,
            'total_api_calls': self.total_api_calls,
            'total_retries': self.total_retries,
            'successful_retries': self.successful_retries,
        }

    def resume_lines(self) -> list:
        """生成可直接贴进简历的量化语句列表"""
        r = self.report()
        lines = []

        if r['reuse_save_rate_pct'] > 0:
            lines.append(
                f"同场景首帧复用策略节省 {r['api_calls_saved_by_reuse']} 次 API 调用"
                f"（复用率 {r['reuse_save_rate_pct']}%），降低生图成本")

        if r['retry_success_rate_pct'] > 0:
            lines.append(
                f"指数退避重试机制成功率 {r['retry_success_rate_pct']}%，"
                f"共挽救 {r['successful_retries']} 次失败调用")

        if r['overall_success_rate_pct'] > 0:
            lines.append(f"全流程自动化成功率 {r['overall_success_rate_pct']}%")

        # 步骤耗时
        for name, info in r['steps'].items():
            d = info['counts']
            if 'shots_done' in d and d.get('shots_total', 1) > 0:
                lines.append(
                    f"{name} 步骤：{d['shots_done']}/{d.get('shots_total', '?')} 镜成功，"
                    f"平均耗时 {info['avg_ms']}ms")

        return lines

    def pp(self):
        """打印报告"""
        r = self.report()
        print('\n' + '=' * 60)
        print('  📊 Zhiyan 运行指标报告')
        print('=' * 60)
        print(f'  会话数: {r["sessions"]}')
        print(f'  总耗时: {r["total_time_sec"]}s')
        print(f'  API 调用: {r["total_api_calls"]} 次')
        print(f'  首帧复用: {r["api_calls_saved_by_reuse"]} 次 (节省 {r["reuse_save_rate_pct"]}%)')
        print(f'  重试成功率: {r["retry_success_rate_pct"]}% ({r["successful_retries"]}/{r["total_retries"]})')
        print(f'  整体成功率: {r["overall_success_rate_pct"]}%')
        if r['failures_by_category']:
            print(f'  失败分类: {r["failures_by_category"]}')
        print('-' * 60)
        for name, info in r['steps'].items():
            print(f'  {name}: 调用 {info["count"]} 次, 平均 {info["avg_ms"]}ms')
        print('=' * 60)
        print('\n  📝 简历可用语句:')
        for line in self.resume_lines():
            print(f'  • {line}')
        print()

    def reset(self):
        self._init()

    def save(self, path='metrics.json'):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.report(), f, ensure_ascii=False, indent=2)


# 全局单例
metrics = MetricsCollector()
