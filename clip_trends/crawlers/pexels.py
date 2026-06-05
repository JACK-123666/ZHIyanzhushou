# clip_trends/crawlers/pexels.py
from .base import BaseCrawler, RawVideo
from ..config import PEXELS_API_KEY


class PexelsCrawler(BaseCrawler):
    site_name = "pexels"

    def crawl(self) -> list[RawVideo]:
        videos = []
        headers = {'Authorization': PEXELS_API_KEY}
        resp = self._get(
            'https://api.pexels.com/videos/popular',
            params={'per_page': self.max_per_site},
            headers=headers
        )
        data = resp.json()
        for i, v in enumerate(data.get('videos', [])):
            video_files = sorted(v.get('video_files', []),
                                 key=lambda x: x.get('width', 0) or 0, reverse=True)
            video_url = video_files[0]['link'] if video_files else v.get('url', '')
            resolution = f"{video_files[0].get('width',0)}x{video_files[0].get('height',0)}" if video_files else None

            videos.append(RawVideo(
                site='pexels',
                source_url=video_url,
                source_id=str(v.get('id')),
                title=v.get('url', '').split('/')[-2].replace('-', ' ').title(),
                thumbnail_url=v.get('image'),
                duration_sec=v.get('duration'),
                resolution=resolution,
                tags=[t.lower() for t in v.get('tags', [])] if isinstance(v.get('tags', []), list)
                     else [v.get('tags', '')],
                description=v.get('url', ''),
                popularity_score=100 * (1 - i / max(self.max_per_site, 1)),
            ))
        return videos
