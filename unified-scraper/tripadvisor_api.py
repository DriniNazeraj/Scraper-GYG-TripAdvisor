# -*- coding: utf-8 -*-

"""
TripAdvisor API client using omkarcloud's TripAdvisor Scraper API.
Free tier: 1,000 requests/month.

API docs: https://github.com/omkarcloud/tripadvisor-scraper
"""

import requests
import logging

BASE_URL = 'https://tripadvisor-scraper-api.omkar.cloud'
TIMEOUT = 30


class TripAdvisorAPI:

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {'API-Key': api_key}
        self.logger = self._get_logger()

    def search_attractions(self, query, max_pages=1):
        """Search for attractions/activities by city or query.

        Returns list of attraction dicts with: name, rating, reviews,
        description, link, categories, pricing, image.
        """
        all_results = []

        for page in range(1, max_pages + 1):
            self.logger.info('Fetching attractions page %d for "%s"', page, query)
            resp = requests.get(
                f'{BASE_URL}/tripadvisor/attractions/list',
                params={'query': query, 'page': page},
                headers=self.headers,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get('results', [])
            if not results:
                break

            all_results.extend(results)
            self.logger.info('Got %d attractions (page %d/%d)',
                             len(results), page, data.get('total_pages', '?'))

            if page >= data.get('total_pages', 1):
                break

        return all_results

    def search_hotels(self, query, page=1):
        """Search for hotels by city or query."""
        self.logger.info('Searching hotels for "%s"', query)
        resp = requests.get(
            f'{BASE_URL}/tripadvisor/hotels/list',
            params={'query': query, 'page': page},
            headers=self.headers,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get('results', [])

    def search_restaurants(self, query, page=1):
        """Search for restaurants by city or query."""
        self.logger.info('Searching restaurants for "%s"', query)
        resp = requests.get(
            f'{BASE_URL}/tripadvisor/restaurants/search',
            params={'query': query},
            headers=self.headers,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get('results', [])

    def get_reviews(self, query, max_pages=1, **filters):
        """Get reviews for an attraction/hotel/restaurant.

        Args:
            query: Name, URL, or entity ID
            max_pages: Number of review pages to fetch (20 reviews per page)
            **filters: Optional filters (rating, sort, language, etc.)

        Returns list of review dicts with: review_id, title, text, rating,
        reviewer info, date, trip type, images, etc.
        """
        all_reviews = []

        for page in range(1, max_pages + 1):
            self.logger.info('Fetching reviews page %d for "%s"', page, query)
            params = {'query': query, 'page': page}
            params.update(filters)

            resp = requests.get(
                f'{BASE_URL}/tripadvisor/reviews',
                params=params,
                headers=self.headers,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get('results', [])
            if not results:
                break

            all_reviews.extend(results)

            if page >= data.get('total_pages', 1):
                break

        return all_reviews

    def get_hotel_detail(self, query):
        """Get detailed info for a specific hotel."""
        self.logger.info('Getting hotel details for "%s"', query)
        resp = requests.get(
            f'{BASE_URL}/tripadvisor/hotels/detail',
            params={'query': query},
            headers=self.headers,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _get_logger(self):
        logger = logging.getLogger('tripadvisor-api')
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
        return logger
