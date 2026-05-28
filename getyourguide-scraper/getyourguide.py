# -*- coding: utf-8 -*-

import time
import re
import json
import logging
import traceback

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

try:
    import undetected_chromedriver as uc
    USE_UC = True
except ImportError:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    USE_UC = False

GYG_BASE = 'https://www.getyourguide.com'
GYG_SEARCH = '/s/?q={}&searchSource=1'
MAX_WAIT = 15
MAX_RETRY = 3
SCROLL_PAUSE = 1.5


class GetYourGuide:

    def __init__(self, debug=False, lang='en', currency='USD'):
        self.debug = debug
        self.lang = lang
        self.currency = currency
        self.driver = self._get_driver()
        self.logger = self._get_logger()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
        self.driver.close()
        self.driver.quit()
        return True

    # ── Search ──────────────────────────────────────────────────────────

    def search_activities(self, query, max_pages=3):
        """Search for activities and return a list of result dicts."""
        url = GYG_BASE + GYG_SEARCH.format(query.replace(' ', '+'))
        self.logger.info('Searching: %s', url)
        self.driver.get(url)
        self._random_wait(3, 5)
        self._dismiss_popups()

        all_activities = []

        for page in range(1, max_pages + 1):
            self.logger.info('Parsing search results page %d', page)
            self._scroll_to_bottom()

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            activities = self._parse_search_results(soup)

            if not activities:
                self.logger.info('No results found on page %d, stopping.', page)
                break

            all_activities.extend(activities)
            self.logger.info('Found %d activities on page %d', len(activities), page)

            if not self._go_next_page():
                break

        return all_activities

    # ── Activity Detail ─────────────────────────────────────────────────

    def get_activity_detail(self, url):
        """Scrape full details from an activity page."""
        self.logger.info('Scraping activity: %s', url)

        for attempt in range(MAX_RETRY):
            try:
                self.driver.get(url)
                self._random_wait(3, 5)
                self._dismiss_popups()

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                detail = self._parse_activity_page(soup)
                detail['url'] = url
                return detail
            except Exception as e:
                self.logger.warning('Attempt %d failed for %s: %s', attempt + 1, url, e)
                time.sleep(2)

        self.logger.error('Failed to scrape activity after %d retries: %s', MAX_RETRY, url)
        return {'url': url, 'error': 'Failed to scrape'}

    # ── Reviews ─────────────────────────────────────────────────────────

    def get_reviews(self, url, max_reviews=50):
        """Scrape reviews from an activity page."""
        self.logger.info('Scraping reviews from: %s', url)
        self.driver.get(url)
        self._random_wait(3, 5)
        self._dismiss_popups()

        # scroll to reviews section
        self._scroll_to_reviews()

        all_reviews = []
        pages_scraped = 0

        while len(all_reviews) < max_reviews:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            reviews = self._parse_reviews(soup)

            if not reviews:
                break

            # only add new reviews (deduplicate)
            existing_ids = {r.get('review_id') for r in all_reviews}
            new_reviews = [r for r in reviews if r.get('review_id') not in existing_ids]

            if not new_reviews:
                break

            all_reviews.extend(new_reviews)
            pages_scraped += 1
            self.logger.info('Scraped %d reviews so far (%d pages)', len(all_reviews), pages_scraped)

            if not self._next_review_page():
                break

        return all_reviews[:max_reviews]

    # ── Parsing: Search Results ─────────────────────────────────────────

    def _parse_search_results(self, soup):
        results = []

        # Primary: clickable-href links are the activity card wrappers
        cards = soup.select('a.clickable-href[href*="-t"]')

        # Fallback: find all links matching activity URL pattern
        if not cards:
            cards = soup.find_all('a', href=re.compile(r'/[a-z].*-l\d+/.*-t\d+'))

        for card in cards:
            try:
                activity = self._extract_card_data(card)
                if activity.get('title'):
                    results.append(activity)
            except Exception as e:
                self.logger.debug('Failed to parse card: %s', e)
                continue

        return results

    def _extract_card_data(self, card):
        """Extract data from a single activity card element."""
        activity = {}

        # Extract activity ID from the URL (e.g. -t381474)
        href = card.get('href', '')
        id_match = re.search(r'-t(\d+)', href)
        activity_id = id_match.group(1) if id_match else ''

        # URL
        activity['url'] = href if href.startswith('http') else GYG_BASE + href

        # Title — use data-block-id="{id}-title"
        title_el = card.select_one(f'[data-block-id="{activity_id}-title"]') if activity_id else None
        if not title_el:
            title_el = card.select_one('.text-atom--title-4')
        activity['title'] = title_el.get_text(strip=True) if title_el else ''

        # Duration/attributes — data-block-id="{id}-attributes"
        attrs_el = card.select_one(f'[data-block-id="{activity_id}-attributes"]') if activity_id else None
        if not attrs_el:
            attrs_el = card.select_one('.text-atom--caption')
        activity['duration'] = attrs_el.get_text(strip=True) if attrs_el else ''

        # Rating — data-block-id="{id}-one-star-review-text"
        rating_el = card.select_one(f'[data-block-id="{activity_id}-one-star-review-text"]') if activity_id else None
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            try:
                activity['rating'] = float(rating_text)
            except ValueError:
                activity['rating'] = rating_text
        else:
            activity['rating'] = None

        # Review count — data-block-id="{id}-one-star-review-description"
        review_el = card.select_one(f'[data-block-id="{activity_id}-one-star-review-description"]') if activity_id else None
        if review_el:
            review_text = review_el.get_text(strip=True)
            # format is like "(16,145)" — extract digits
            count_match = re.search(r'[\d,]+', review_text)
            if count_match:
                activity['review_count'] = int(count_match.group().replace(',', ''))
            else:
                activity['review_count'] = review_text
        else:
            activity['review_count'] = None

        # Price — data-block-id="{id}-inline-price-text"
        price_el = card.select_one(f'[data-block-id="{activity_id}-inline-price-text"]') if activity_id else None
        if price_el:
            price_text = price_el.get_text(strip=True)
            activity['price'] = price_text
            # extract numeric values (may have original + discounted)
            prices = re.findall(r'[\d,.]+', price_text)
            activity['price_value'] = float(prices[-1].replace(',', '')) if prices else None
        else:
            activity['price'] = ''
            activity['price_value'] = None

        # Image
        img = card.select_one('img')
        activity['image_url'] = img.get('src', '') if img else ''

        return activity

    # ── Parsing: Activity Detail Page ───────────────────────────────────

    def _parse_activity_page(self, soup):
        detail = {}

        # Title
        title_el = (
            soup.select_one('h1') or
            soup.select_one('[class*="activity-title"]') or
            soup.select_one('[data-test*="title"]')
        )
        detail['title'] = title_el.get_text(strip=True) if title_el else ''

        # Description
        desc_el = (
            soup.select_one('[class*="description"]') or
            soup.select_one('[class*="about"]') or
            soup.select_one('[data-test*="description"]')
        )
        detail['description'] = desc_el.get_text(strip=True)[:2000] if desc_el else ''

        # Price
        price_el = (
            soup.select_one('[class*="current-price"]') or
            soup.select_one('[class*="Price"]') or
            soup.select_one('[class*="price"]')
        )
        if price_el:
            detail['price'] = price_el.get_text(strip=True)
        else:
            detail['price'] = ''

        # Rating and review count
        rating_el = (
            soup.select_one('[class*="overall-rating"]') or
            soup.select_one('[class*="rating-value"]') or
            soup.select_one('[class*="Rating"]') or
            soup.select_one('[class*="rating"]')
        )
        if rating_el:
            text = rating_el.get_text(strip=True)
            match = re.search(r'(\d[.,]\d)', text)
            detail['rating'] = float(match.group().replace(',', '.')) if match else text
        else:
            detail['rating'] = None

        review_count_el = (
            soup.select_one('[class*="review-count"]') or
            soup.select_one('[class*="ReviewCount"]') or
            soup.select_one('[class*="reviews"]')
        )
        if review_count_el:
            text = review_count_el.get_text(strip=True)
            match = re.search(r'[\d,]+', text.replace(',', ''))
            detail['review_count'] = int(match.group()) if match else text
        else:
            detail['review_count'] = None

        # Duration
        duration_el = (
            soup.select_one('[class*="duration"]') or
            soup.select_one('[class*="Duration"]')
        )
        detail['duration'] = duration_el.get_text(strip=True) if duration_el else ''

        # Highlights / Inclusions
        highlights = []
        highlights_section = (
            soup.select_one('[class*="highlights"]') or
            soup.select_one('[class*="Highlights"]') or
            soup.select_one('[class*="inclusions"]')
        )
        if highlights_section:
            for li in highlights_section.select('li'):
                highlights.append(li.get_text(strip=True))
        detail['highlights'] = highlights

        # What's included
        inclusions = []
        included_section = (
            soup.select_one('[class*="included"]') or
            soup.select_one('[class*="Included"]')
        )
        if included_section:
            for li in included_section.select('li'):
                inclusions.append(li.get_text(strip=True))
        detail['inclusions'] = inclusions

        # Meeting point
        meeting_el = (
            soup.select_one('[class*="meeting-point"]') or
            soup.select_one('[class*="MeetingPoint"]') or
            soup.select_one('[class*="location"]')
        )
        detail['meeting_point'] = meeting_el.get_text(strip=True) if meeting_el else ''

        # Try to extract structured data (JSON-LD)
        json_ld = self._extract_json_ld(soup)
        if json_ld:
            detail['structured_data'] = json_ld

        return detail

    def _extract_json_ld(self, soup):
        """Extract JSON-LD structured data — often the most reliable source."""
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ('Product', 'TouristAttraction', 'Event', 'Offer'):
                    return data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') in ('Product', 'TouristAttraction', 'Event', 'Offer'):
                            return item
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    # ── Parsing: Reviews ────────────────────────────────────────────────

    def _parse_reviews(self, soup):
        reviews = []

        # Look for review containers
        review_cards = (
            soup.select('[class*="review-card"]') or
            soup.select('[class*="ReviewCard"]') or
            soup.select('[class*="review-item"]') or
            soup.select('[class*="review"][class*="container"]') or
            soup.select('[data-test*="review"]') or
            []
        )

        for idx, card in enumerate(review_cards):
            try:
                review = self._extract_review(card, idx)
                if review.get('text') or review.get('title'):
                    reviews.append(review)
            except Exception as e:
                self.logger.debug('Failed to parse review: %s', e)
                continue

        return reviews

    def _extract_review(self, card, idx):
        review = {}
        review['review_id'] = card.get('data-review-id', card.get('id', f'review_{idx}'))

        # Author
        author_el = (
            card.select_one('[class*="author"]') or
            card.select_one('[class*="Author"]') or
            card.select_one('[class*="user"]') or
            card.select_one('[class*="name"]')
        )
        review['author'] = author_el.get_text(strip=True) if author_el else ''

        # Rating
        rating_el = (
            card.select_one('[class*="rating"]') or
            card.select_one('[class*="stars"]') or
            card.select_one('[aria-label*="star"]')
        )
        if rating_el:
            aria = rating_el.get('aria-label', '')
            match = re.search(r'(\d[.,]?\d?)', aria or rating_el.get_text(strip=True))
            review['rating'] = float(match.group().replace(',', '.')) if match else None
        else:
            review['rating'] = None

        # Title
        title_el = (
            card.select_one('[class*="review-title"]') or
            card.select_one('[class*="Title"]') or
            card.select_one('h3') or
            card.select_one('h4')
        )
        review['title'] = title_el.get_text(strip=True) if title_el else ''

        # Review text
        text_el = (
            card.select_one('[class*="review-text"]') or
            card.select_one('[class*="review-body"]') or
            card.select_one('[class*="ReviewText"]') or
            card.select_one('[class*="content"]') or
            card.select_one('p')
        )
        review['text'] = text_el.get_text(strip=True) if text_el else ''

        # Date
        date_el = (
            card.select_one('[class*="date"]') or
            card.select_one('[class*="Date"]') or
            card.select_one('time')
        )
        if date_el:
            review['date'] = date_el.get('datetime', date_el.get_text(strip=True))
        else:
            review['date'] = ''

        return review

    # ── Navigation helpers ──────────────────────────────────────────────

    def _go_next_page(self):
        """Click the next page button in search results."""
        try:
            next_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                'a[aria-label="Next"], button[aria-label="Next"], '
                '[class*="pagination"] a:last-child, [class*="next"]'
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(1)
            next_btn.click()
            self._random_wait(2, 4)
            return True
        except Exception:
            self.logger.info('No next page button found.')
            return False

    def _next_review_page(self):
        """Click next page within the reviews section."""
        try:
            # look for review-specific pagination
            next_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                '[class*="review"] [aria-label="Next"], '
                '[class*="review"] [class*="next"], '
                '[class*="Review"] button[class*="next"]'
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(1)
            next_btn.click()
            self._random_wait(2, 3)
            return True
        except Exception:
            return False

    def _scroll_to_reviews(self):
        """Scroll to the reviews section of an activity page."""
        try:
            reviews_section = self.driver.find_element(
                By.CSS_SELECTOR,
                '[class*="review"], [id*="review"], [data-test*="review"]'
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", reviews_section)
            time.sleep(2)
        except Exception:
            self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll page to load lazy content."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _dismiss_popups(self):
        """Close cookie banners or popups."""
        popup_selectors = [
            'button[id*="cookie" i]',
            'button[class*="cookie" i]',
            'button[class*="accept" i]',
            'button[class*="consent" i]',
            '[class*="modal"] button[class*="close"]',
            'button[aria-label="Close"]',
            '[data-test*="cookie"] button',
        ]
        for sel in popup_selectors:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                btn.click()
                time.sleep(0.5)
            except Exception:
                continue

    def _random_wait(self, min_s=1, max_s=3):
        """Wait a random amount to appear human."""
        import random
        time.sleep(random.uniform(min_s, max_s))

    # ── Driver setup ────────────────────────────────────────────────────

    def _get_driver(self):
        # Try undetected-chromedriver first, fall back to standard Selenium
        if USE_UC:
            try:
                options = uc.ChromeOptions()
                if not self.debug:
                    options.add_argument('--headless=new')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--disable-notifications')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument(f'--lang={self.lang}')
                return uc.Chrome(options=options)
            except Exception as e:
                print(f'undetected-chromedriver failed ({e}), falling back to standard Selenium')

        from selenium import webdriver as std_webdriver
        from selenium.webdriver.chrome.options import Options
        options = Options()
        if not self.debug:
            options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--lang={self.lang}')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/148.0.7778.179 Safari/537.36')
        return std_webdriver.Chrome(options=options)

    def _get_logger(self):
        logger = logging.getLogger('getyourguide-scraper')
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            fh = logging.FileHandler('gyg-scraper.log')
            fh.setLevel(logging.DEBUG)

            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)

            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)

            logger.addHandler(fh)
            logger.addHandler(ch)

        return logger
