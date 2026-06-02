# clip_trends/crawlers/mixkit.py
from bs4 import BeautifulSoup
from .base import BaseCrawler, RawVideo


class MixkitCrawler(BaseCrawler):
    site_name = "mixkit"

    def crawl(self) -> list[RawVideo]:
        videos = []
        resp = self._get('https://mixkit.co/free-stock-video/')
        soup = BeautifulSoup(resp.text, 'html.parser')

        cards = soup.select('div.item-grid__card, a[href*="/free-stock-video/"], .video-card, [class*="card"]')
        seen_urls = set()
        count = 0
        for card in cards:
            if count >= self.max_per_site:
                break

            link = card.get('href', '') if card.name == 'a' else ''
            if not link:
                a_tag = card.find('a', href=True)
                if a_tag:
                    link = a_tag['href']

            if not link or '/free-stock-video/' not in link:
                continue

            full_url = link if link.startswith('http') else f'https://mixkit.co{link}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            img = card.find('img')
            title = img.get('alt', '') if img else ''
            thumbnail = img.get('src', '') or img.get('data-src', '') if img else ''

            tags_el = card.select('.item-grid-card__tags span, .tags span, [class*="tag"]')
            tags = [t.get_text(strip=True).lower() for t in tags_el if t.get_text(strip=True)]

            videos.append(RawVideo(
                site='mixkit',
                source_url=full_url,
                source_id=None,
                title=title,
                thumbnail_url=thumbnail,
                duration_sec=None,
                resolution=None,
                tags=tags,
                description=title,
                popularity_score=100 * (1 - count / max(self.max_per_site, 1)),
            ))
            count += 1

        return videos
