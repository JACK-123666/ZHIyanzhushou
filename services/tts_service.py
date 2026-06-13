"""Edge TTS 语音合成"""

import os, asyncio, re, time, logging

log = logging.getLogger(__name__)


async def _generate_tts(text, out_path, voice):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def generate_narration(text, output_path, voice="zh-CN-XiaoxiaoNeural", max_retries=3):
    clean = re.sub(r'<[^>]+>', '', text).strip()
    if not clean:
        clean = text.strip()
    if not clean or len(clean) < 2:
        raise ValueError("旁白文本为空")

    # 截断保护: Edge TTS 对大段文本可能超时
    if len(clean) > 500:
        clean = clean[:500]

    for attempt in range(max_retries):
        try:
            asyncio.run(_generate_tts(clean, output_path, voice))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                return output_path
        except Exception as e:
            log.warning(f"TTS 尝试 {attempt+1}/{max_retries} 失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)

    raise RuntimeError(f"TTS 失败，已重试 {max_retries} 次")
