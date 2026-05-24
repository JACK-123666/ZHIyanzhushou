import os
import asyncio


async def _generate_tts(text, output_path, voice="zh-CN-XiaoxiaoNeural"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_narration(text, output_path, voice="zh-CN-XiaoxiaoNeural"):
    """使用 Edge TTS 生成旁白音频"""
    asyncio.run(_generate_tts(text, output_path, voice))
    return output_path
