"""Edge TTS 语音合成 — 免费微软中文语音（晓晓女声），纯文本模式"""

import os, asyncio, re


async def _generate_tts(text, out_path, voice="zh-CN-XiaoxiaoNeural"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def generate_narration(text, output_path, voice="zh-CN-XiaoxiaoNeural"):
    """生成旁白 mp3。剥离所有 SSML/XML 标签，纯文本朗读。"""
    # 剥离 SSML 标签（LLM 生成的 SSML 值不可靠，会导致朗读标签文字）
    clean = re.sub(r'<[^>]+>', '', text).strip()
    if not clean:
        clean = text.strip()  # fallback
    asyncio.run(_generate_tts(clean, output_path, voice))
    return output_path
