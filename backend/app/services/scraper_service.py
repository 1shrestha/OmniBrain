"""
services/scraper_service.py

Fetches a website and crawls same-domain pages up to a page limit.
Kept dependency-light: `requests` + `BeautifulSoup` rather than a
headless browser (Playwright/Puppeteer), which is a reasonable
trade-off for a first pass — it won't execute JavaScript, so
JS-rendered single-page apps will yield thin content. Swapping in
Playwright later only requires changing `fetch_page()` below; every
caller works against the same return shape.
"""

from collections import deque
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.exceptions import InvalidURLError, WebsiteFetchError
from app.core.logger import get_logger

logger = get_logger(__name__)


def normalize_url(url: str) -> str:
    """Add a scheme if missing and validate the result looks like a real URL."""
    url = url.strip()
    if not url:
        raise InvalidURLError(url)
    if "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.netloc or "." not in parsed.netloc:
        raise InvalidURLError(url)
    return url


class ScraperService:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": settings.SCRAPER_USER_AGENT})

    def fetch_page(self, url: str) -> dict[str, Any]:
        """
        Fetch a single page and return its parsed content.

        Returns:
            dict with keys: url, title, text, links (list[str], absolute,
            same-domain only), forms_count, status_code
        """
        try:
            resp = self._session.get(url, timeout=settings.SCRAPER_TIMEOUT_SECONDS)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise WebsiteFetchError(url, str(exc)) from exc

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else urlparse(url).netloc

        text = " ".join(soup.get_text(separator=" ").split())
        text = text[: settings.SCRAPER_MAX_CONTENT_CHARS_PER_PAGE]

        domain = urlparse(url).netloc
        links: set[str] = set()
        for a in soup.find_all("a", href=True):
            absolute = urljoin(url, a["href"])
            parsed = urlparse(absolute)
            if parsed.scheme in ("http", "https") and parsed.netloc == domain:
                # strip fragments/query noise for de-duplication
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                links.add(clean.rstrip("/"))

        forms_count = len(soup.find_all("form"))

        return {
            "url": url,
            "title": title,
            "text": text,
            "links": links,
            "forms_count": forms_count,
            "status_code": resp.status_code,
        }

    def crawl(self, start_url: str, max_pages: int = 15) -> list[dict[str, Any]]:
        """
        Breadth-first crawl of same-domain pages starting from start_url.

        Returns a list of page dicts (see fetch_page). Stops at max_pages
        or when the frontier is exhausted, whichever comes first.
        """
        start_url = normalize_url(start_url)
        domain = urlparse(start_url).netloc

        visited: set[str] = set()
        queue: deque[str] = deque([start_url])
        pages: list[dict[str, Any]] = []

        while queue and len(pages) < max_pages:
            url = queue.popleft()
            normalized = url.rstrip("/")
            if normalized in visited:
                continue
            visited.add(normalized)

            try:
                page = self.fetch_page(url)
            except WebsiteFetchError as exc:
                logger.warning(f"Skipping page (fetch failed): {url} — {exc.message}")
                if url == start_url:
                    # If the homepage itself fails, the whole analysis should fail loudly.
                    raise
                continue

            pages.append(page)

            for link in page["links"]:
                if link.rstrip("/") not in visited and urlparse(link).netloc == domain:
                    queue.append(link)

        logger.info(f"Crawl complete | start={start_url} | pages_fetched={len(pages)}")
        return pages
