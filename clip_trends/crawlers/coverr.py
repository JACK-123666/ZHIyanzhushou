# clip_trends/crawlers/coverr.py
from bs4 import BeautifulSoup
from .base import BaseCrawler, RawVideo
import re, json


class CoverrCrawler(BaseCrawler):
    site_name = "coverr"

    def crawl(self) -> list[RawVideo]:
        videos = []
        resp = self._get('https://coverr.co/')
        soup = BeautifulSoup(resp.text, 'html.parser')

        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '__NEXT_DATA__' in (script.string or ''):
                match = re.search(r'window\.__NEXT_DATA__\s*=\s*({.*?});', script.string, re.DOTALL)
                if not match:
                    # Try another approach: the JSON might be embedded differently
                    try:
                        json_str = script.string.split('__NEXT_DATA__ = ')[1].rstrip(';')
                        state = json.loads(json_str)
                    except (IndexError, json.JSONDecodeError):
                        continue
                else:
                    try:
                        state = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        continue

                # Navigate Next.js state to find videos
                props = state.get('props', {}).get('pageProps', {})
                all_videos = (props.get('videos', []) or
                              props.get('popularVideos', []) or
                              props.get('items', []))
                for i, v in enumerate(all_videos[:self.max_per_site]):
                    videos.append(RawVideo(
                        site='coverr',
                        source_url=v.get('url', '') or v.get('videoUrl', '') or v.get('source', ''),
                        source_id=str(v.get('id', '') or v.get('_id', '')),
                        title=v.get('title', '') or v.get('name', ''),
                        thumbnail_url=v.get('poster', '') or v.get('thumbnail', '') or v.get('image', ''),
                        duration_sec=float(v.get('duration', 0)) if v.get('duration') else None,
                        resolution=None,
                        tags=[t.lower().strip() for t in (v.get('tags', []) or [])],
                        description=v.get('description', '') or '',
                        popularity_score=100 * (1 - i / max(self.max_per_site, 1)),
                    ))
                break

        return videos
