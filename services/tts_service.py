"""Edge TTS 语音合成 — 免费微软中文语音（晓晓女声），异步包装为同步"""

import os, asyncio


async def _generate_tts(text, out_path, voice="zh-CN-XiaoxiaoNeural"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def generate_narration(text, output_path, voice="zh-CN-XiaoxiaoNeural"):
    """生成旁白 mp3。edge_tts 是异步库，用 asyncio.run() 包装为同步调用。"""
    asyncio.run(_generate_tts(text, output_path, voice))
    return output_path
