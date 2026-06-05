# clip_trends/crawlers/base.py
import time, requests, hashlib, os
from dataclasses import dataclass
from typing import Optional
from ..config import CRAWL_CONFIG, VIDEO_ANALYSIS


@dataclass
class RawVideo:
    site: str
    source_url: str
    source_id: Optional[str]
    title: str
    thumbnail_url: Optional[str]
    duration_sec: Optional[float]
    resolution: Optional[str]
    tags: list
    description: Optional[str]
    popularity_score: float


class BaseCrawler:
    site_name: str = "base"

    def __init__(self, config: dict = None):
        cfg = config or CRAWL_CONFIG
        self.max_per_site = cfg['max_per_site']
        self.request_interval = cfg['request_interval']
        self.request_timeout = cfg['request_timeout']
        self.retry_times = cfg['retry_times']
        self.retry_backoff = cfg['retry_backoff']
        self._last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request = time.time()

    def _get(self, url, params=None, headers=None):
        """带限速+重试的 GET"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        if headers:
            default_headers.update(headers)

        last_error = None
        for attempt in range(self.retry_times + 1):
            self._rate_limit()
            try:
                resp = requests.get(
                    url, params=params, headers=default_headers,
                    timeout=self.request_timeout
                )
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_error = e
                if attempt < self.retry_times:
                    time.sleep(self.retry_backoff[attempt])
        raise last_error

    def _head_content_length(self, url: str) -> Optional[int]:
        """HEAD 请求探测文件大小"""
        try:
            resp = requests.head(url, timeout=10)
            length = resp.headers.get('Content-Length')
            return int(length) if length else None
        except Exception:
            return None

    def _download_video(self, url: str, dest_path: str,
                        max_size_mb: int = None, timeout: int = None) -> bool:
        """下载视频到临时路径，返回是否成功"""
        max_size_mb = max_size_mb or VIDEO_ANALYSIS['max_file_size_mb']
        timeout = timeout or VIDEO_ANALYSIS['download_timeout']

        size = self._head_content_length(url)
        if size and size > max_size_mb * 1024 * 1024:
            return False

        try:
            resp = requests.get(url, stream=True, timeout=timeout)
            resp.raise_for_status()
            downloaded = 0
            max_bytes = max_size_mb * 1024 * 1024
            with open(dest_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        f.close()
                        os.remove(dest_path)
                        return False
            return True
        except Exception:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return False

    def crawl(self) -> list:
        raise NotImplementedError
