"""分类编排：Qwen-VL 主路径 → 规则降级 → LLM 兜底"""
import json
from .config import DASHSCOPE_API_KEY
from .db import get_conn, save_techniques
from .taxonomy import get_all_taxonomy_entries
from .video_analyzer import analyze_video, cleanup_temp
from .qwen_client import analyze_video_frames


# 预加载 taxonomy entries 列表（含 id）
_taxonomy_cache = None


def _get_taxonomy_with_ids():
    global _taxonomy_cache
    if _taxonomy_cache is not None:
        return _taxonomy_cache
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, dimension, category, subcategory, detail, keywords FROM technique_taxonomy")
        rows = cur.fetchall()
        _taxonomy_cache = [
            {"id": r[0], "dimension": r[1], "category": r[2],
             "subcategory": r[3], "detail": r[4],
             "keywords": json.loads(r[5]) if isinstance(r[5], str) else r[5]}
            for r in rows
        ]
    return _taxonomy_cache


def classify_by_rules(tags: list, title: str = '', description: str = '') -> list[dict]:
    """规则引擎：关键词匹配 taxonomy"""
    entries = _get_taxonomy_with_ids()
    text = ' '.join((tags or []) + [title, description or '']).lower()
    results = []
    for entry in entries:
        keywords = entry.get('keywords', [])
        for kw in keywords:
            if kw.lower() in text:
                results.append({
                    'taxonomy_id': entry['id'],
                    'confidence': 0.7,
                    'evidence': f'关键词匹配: "{kw}"',
                    'method': 'rule',
                })
                break  # 一个 entry 只记录一次
    return results


def classify_by_llm_text(video_info: dict) -> list[dict]:
    """DeepSeek 文本兜底：基于 tags + title + description"""
    try:
        from openai import OpenAI
        from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        entries = _get_taxonomy_with_ids()

        prompt = f"""你是剪辑分析专家。根据视频标签和描述，从以下分类体系匹配适用的剪辑技法。
视频信息: title={video_info.get('title')}, tags={video_info.get('tags', [])}, description={video_info.get('description', '')}
分类体系: {json.dumps([{{
    "id": e["id"], "dimension": e["dimension"],
    "category": e["category"], "subcategory": e["subcategory"],
    "detail": e["detail"]
}} for e in entries], ensure_ascii=False)}

输出JSON数组: [{{"taxonomy_id": 1, "evidence": "...", "confidence": 0.8}}, ...]"""

        resp = client.chat.completions.create(
            model='deepseek-v4-pro',
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.1,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].split('```')[0]
        results = json.loads(content)
        for r in results:
            r['method'] = 'llm'
        return results
    except Exception:
        return []


def classify(video_record: dict, download_func) -> int:
    """
    主分类编排，返回命中的技法数。
    video_record: {'id': 123, 'source_url': '...', 'tags': [...], 'title': '...', 'description': '...'}
    """
    video_id = video_record['id']
    techniques = []
    temp_dir = None

    # 路径1: Qwen-VL 抽帧分析（优先）
    if DASHSCOPE_API_KEY:
        try:
            analysis = analyze_video(video_record['source_url'], download_func)
            if analysis:
                analysis['tags'] = video_record.get('tags', [])
                temp_dir = analysis.get('temp_dir')
                techniques = analyze_video_frames(analysis, _get_taxonomy_with_ids())
        except Exception:
            pass

    # 路径2: 若 Qwen-VL 无结果，尝试规则匹配
    if not techniques:
        techniques = classify_by_rules(
            video_record.get('tags', []),
            video_record.get('title', ''),
            video_record.get('description', '')
        )

    # 路径3: 规则也没结果，LLM 文本兜底
    if not techniques:
        techniques = classify_by_llm_text(video_record)

    # 保存
    if techniques:
        save_techniques(video_id, techniques)

    # 清理临时文件
    if temp_dir:
        cleanup_temp(temp_dir)

    return len(techniques)
