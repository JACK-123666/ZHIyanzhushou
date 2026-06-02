# clip_trends/crawlers/__init__.py
from .pexels import PexelsCrawler
from .pixabay import PixabayCrawler
from .coverr import CoverrCrawler
from .mixkit import MixkitCrawler

CRAWLERS = {
    'pexels': PexelsCrawler,
    'pixabay': PixabayCrawler,
    'coverr': CoverrCrawler,
    'mixkit': MixkitCrawler,
}
