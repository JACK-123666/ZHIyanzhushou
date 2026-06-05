# clip_trends/qwen_client.py
"""Qwen-VL API 封装：逐帧分析 + 帧间对比 + 综合标签映射"""
import json, base64, time
from openai import OpenAI
from .config import DASHSCOPE_API_KEY, VIDEO_ANALYSIS


_client = None


def _get_client():
    """懒加载 Qwen-VL 客户端，避免 API Key 未配时模块导入就崩溃"""
    global _client
    if _client is None:
        if not DASHSCOPE_API_KEY:
            raise RuntimeError("DASHSCOPE_API_KEY is not set")
        _client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        )
    return _client

QWEN_MODEL = VIDEO_ANALYSIS.get('qwen_model', 'qwen-vl-max')


def _encode_image(path: str) -> str:
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


def analyze_frame(frame_path: str) -> dict:
    """分析单帧画面 → 视觉要素 JSON"""
    prompt = """分析这张视频关键帧，描述以下视觉要素，仅输出JSON：
{
  "shot_size": "远景/全景/中景/近景/特写/大特写",
  "camera_angle": "平视/俯拍/仰拍/鸟瞰",
  "composition": "三分法/对称/引导线/框架/负空间/中央 选一",
  "color_tone": "暖/冷/中性",
  "color_temp_k": 5600,
  "lighting": "高调/低调/剪影/自然光",
  "main_light_direction": "左/右/上/正面/背光/无",
  "subject_count": 1,
  "subject_action": "简短描述主体在做什么（中文10字以内）",
  "depth_of_field": "浅/深/正常"
}"""
    try:
        resp = _get_client().chat.completions.create(
            model=QWEN_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_encode_image(frame_path)}"}},
                    {"type": "text", "text": prompt},
                ]
            }],
            max_tokens=500,
            temperature=0.1,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content[:-3]
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


def compare_frames(frame_a_desc: dict, frame_b_desc: dict) -> dict:
    """帧间对比 → 转场类型 + 节奏感知"""
    prompt = f"""以下两张关键帧（间隔3秒）的视觉分析：
帧A: {json.dumps(frame_a_desc, ensure_ascii=False)}
帧B: {json.dumps(frame_b_desc, ensure_ascii=False)}

对比分析两张帧之间的变化，仅输出JSON：
{{
  "transition": "硬切/淡入淡出/叠化/滑入/闪白/无明显转场",
  "camera_change": "同角度/30度以上变化/越轴/无明显变化",
  "shot_size_change": "推进/拉远/同景别/跳级/无明显变化",
  "subject_movement": "左移/右移/前移/后移/静止/画外移动",
  "pace_perception": "快/中/慢",
  "analysis": "一句话描述帧间变化（中文15字以内）"
}}"""
    try:
        resp = _get_client().chat.completions.create(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content[:-3]
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


def map_to_taxonomy(frame_analyses: list, comparisons: list,
                    audio_info: dict, tags: list,
                    taxonomy_entries: list) -> list[dict]:
    """综合所有数据 → 7维 taxonomy 标签映射"""
    prompt = f"""你是电影剪辑分析专家。请根据以下视频多帧分析数据，从7个维度匹配适用的剪辑技法标签。

=== 多帧画面分析 ===
{json.dumps(frame_analyses, ensure_ascii=False, indent=2)[:2000]}

=== 帧间对比 ===
{json.dumps(comparisons, ensure_ascii=False, indent=2)[:1000]}

=== 音频特征 ===
{json.dumps(audio_info, ensure_ascii=False)}

=== 原始标签 ===
{tags[:20]}

=== 7维分类体系（完整 taxonomy）===
{json.dumps([{{
    "id": t["id"],
    "dimension": t["dimension"],
    "category": t["category"],
    "subcategory": t["subcategory"],
    "detail": t["detail"]
}} for t in taxonomy_entries], ensure_ascii=False)}

请根据以上数据，匹配适用的剪辑技法标签。仅输出JSON数组：
[{{"taxonomy_id": 3, "evidence": "基于帧2→帧3的分析发现跳切特征", "confidence": 0.85}}, ...]
confidence 0-1。每个维度最多匹配3个最相关的 subcategory。
如果没有足够证据，不要硬匹配。只输出有把握的。"""
    try:
        from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
        ds_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        resp = ds_client.chat.completions.create(
            model='deepseek-v4-pro',
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content[:-3]
        results = json.loads(content)
        for r in results:
            r['method'] = 'qwen-vl'
        return results
    except Exception:
        return []


def analyze_video_frames(analysis_result: dict, taxonomy_entries: list) -> list[dict]:
    """
    完整的 Qwen-VL 视频分析：
    1. 逐帧分析
    2. 帧间对比
    3. 综合映射 taxonomy
    返回 video_techniques 列表
    """
    frames = analysis_result.get('frames', [])
    if not frames:
        return []

    # 1. 逐帧分析
    frame_analyses = []
    for fp in frames:
        result = analyze_frame(fp)
        if 'error' not in result:
            frame_analyses.append(result)
        time.sleep(0.5)

    if not frame_analyses:
        return []

    # 2. 帧间对比
    comparisons = []
    for i in range(len(frame_analyses) - 1):
        cmp = compare_frames(frame_analyses[i], frame_analyses[i + 1])
        if 'error' not in cmp:
            comparisons.append(cmp)
        time.sleep(0.3)

    # 3. 综合映射 taxonomy
    techniques = map_to_taxonomy(
        frame_analyses, comparisons,
        analysis_result.get('audio', {}),
        analysis_result.get('tags', []),
        taxonomy_entries
    )

    return techniques
