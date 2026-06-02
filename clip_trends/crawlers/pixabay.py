# clip_trends/crawlers/pixabay.py
from .base import BaseCrawler, RawVideo
from config import PIXABAY_API_KEY


class PixabayCrawler(BaseCrawler):
    site_name = "pixabay"

    def crawl(self) -> list[RawVideo]:
        videos = []
        resp = self._get('https://pixabay.com/api/videos/', params={
            'key': PIXABAY_API_KEY,
            'order': 'popular',
            'per_page': self.max_per_site,
            'safesearch': 'true',
        })
        data = resp.json()
        for i, v in enumerate(data.get('hits', [])):
            video_size = v.get('videos', {}).get('large') or v.get('videos', {}).get('medium')
            video_url = video_size.get('url', '') if video_size else ''
            resolution = f"{video_size.get('width',0)}x{video_size.get('height',0)}" if video_size else None

            tags = v.get('tags', '').split(', ') if isinstance(v.get('tags'), str) else v.get('tags', [])

            videos.append(RawVideo(
                site='pixabay',
                source_url=video_url,
                source_id=str(v.get('id')),
                title=v.get('tags', '').split(',')[0].strip() if v.get('tags') else '',
                thumbnail_url=v.get('videos', {}).get('large', {}).get('thumbnail'),
                duration_sec=v.get('duration'),
                resolution=resolution,
                tags=[t.lower().strip() for t in tags] if tags else [],
                description=v.get('tags', ''),
                popularity_score=100 * (1 - i / max(self.max_per_site, 1)),
            ))
        return videos
