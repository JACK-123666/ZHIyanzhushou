"""
生成后质量自检 — 文件有效性 + 失败原因分类，驱动重试/降级/终止决策
"""

import os, struct


class QualityEvaluator:

    MIN_IMAGE_SIZE = 1024
    MIN_VIDEO_SIZE = 10240
    MIN_IMAGE_DIMENSION = 256

    @staticmethod
    def evaluate_image(path: str) -> dict:
        if not path or not os.path.exists(path):
            return {'pass': False, 'reason': '文件不存在', 'action': 'DEGRADE'}

        size = os.path.getsize(path)
        if size == 0:
            return {'pass': False, 'reason': '文件为空', 'action': 'RETRY'}
        if size < QualityEvaluator.MIN_IMAGE_SIZE:
            return {'pass': False, 'reason': f'文件过小({size}B)', 'action': 'RETRY'}

        try:
            dims = QualityEvaluator._read_image_dimensions(path)
            if dims:
                w, h = dims
                if w < QualityEvaluator.MIN_IMAGE_DIMENSION or h < QualityEvaluator.MIN_IMAGE_DIMENSION:
                    return {'pass': False, 'reason': f'分辨率过低({w}x{h})', 'action': 'DEGRADE'}
        except Exception:
            pass

        return {'pass': True, 'reason': 'OK', 'action': 'PASS'}

    @staticmethod
    def evaluate_video(path: str) -> dict:
        if not path or not os.path.exists(path):
            return {'pass': False, 'reason': '文件不存在', 'action': 'DEGRADE'}

        size = os.path.getsize(path)
        if size == 0:
            return {'pass': False, 'reason': '文件为空', 'action': 'RETRY'}
        if size < QualityEvaluator.MIN_VIDEO_SIZE:
            return {'pass': False, 'reason': f'文件过小({size}B)，可能损坏', 'action': 'RETRY'}

        return {'pass': True, 'reason': 'OK', 'action': 'PASS'}

    @staticmethod
    def evaluate_narration(path: str) -> dict:
        if not path or not os.path.exists(path):
            return {'pass': False, 'reason': '文件不存在', 'action': 'RETRY'}

        size = os.path.getsize(path)
        if size == 0:
            return {'pass': False, 'reason': '文件为空', 'action': 'RETRY'}
        if size < 1024:
            return {'pass': False, 'reason': f'文件过小({size}B)', 'action': 'RETRY'}

        return {'pass': True, 'reason': 'OK', 'action': 'PASS'}

    @staticmethod
    def categorize_failure(error_message: str) -> str:
        msg = str(error_message).lower()

        if any(k in msg for k in ('429', 'rate limit', 'too many requests', 'quota', 'throttl')):
            return 'rate_limit'
        if any(k in msg for k in ('timeout', 'connection', 'dns', 'resolve', 'socket',
                                    'network', 'refused', 'reset', 'eof')):
            return 'network'
        if any(k in msg for k in ('empty', 'blank', 'invalid', 'corrupt', 'decode',
                                    'nsfw', 'safety', 'content filter', 'rejected')):
            return 'quality'
        if any(k in msg for k in ('401', '403', 'unauthorized', 'forbidden', 'api key',
                                    'invalid api key', 'authentication')):
            return 'config'

        return 'unknown'

    @staticmethod
    def _read_image_dimensions(path: str) -> tuple | None:
        """纯 Python 读取 PNG/JPEG 头部获取宽高，不依赖 PIL。"""
        with open(path, 'rb') as f:
            header = f.read(32)
            if len(header) < 24:
                return None

            if header[:8] == b'\x89PNG\r\n\x1a\n':
                w = struct.unpack('>I', header[16:20])[0]
                h = struct.unpack('>I', header[20:24])[0]
                return (w, h)

            if header[:3] == b'\xff\xd8\xff':
                f.seek(2)
                for _ in range(100):
                    chunk = f.read(4)
                    if len(chunk) < 4:
                        break
                    marker, length = struct.unpack('>HH', chunk)
                    if marker == 0xFFC0:
                        data = f.read(5)
                        if len(data) >= 5:
                            h, w = struct.unpack('>HH', data[1:5])
                            return (w, h)
                    if length < 4:
                        break
                    f.seek(length - 2, 1)

        return None
