# -*- coding: utf-8 -*-

"""
GetYourGuide Scraper — CLI entry point
Based on the tripadvisor-scraper-reviews pattern (Selenium + BeautifulSoup)

Usage examples:
    # Search for activities and save to CSV
    python scraper.py --search "paris tours" --max-pages 3

    # Scrape details for specific activity URLs
    python scraper.py --detail --i urls.txt

    # Scrape reviews for specific activity URLs
    python scraper.py --reviews --i urls.txt --max-reviews 100

    # Debug mode (shows browser window)
    python scraper.py --search "rome" --debug
"""

import argparse
import csv
import json
import os

from getyourguide import GetYourGuide

SEARCH_FIELDS = ['title', 'url', 'price', 'price_value', 'rating', 'review_count', 'duration', 'image_url']
DETAIL_FIELDS = ['title', 'url', 'price', 'rating', 'review_count', 'duration', 'description', 'meeting_point', 'highlights', 'inclusions']
REVIEW_FIELDS = ['review_id', 'author', 'rating', 'title', 'text', 'date']


def save_csv(data, fields, outfile):
    os.makedirs(os.path.dirname(outfile) or '.', exist_ok=True)
    with open(outfile, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            # convert lists to semicolon-separated strings for CSV
            cleaned = {}
            for k, v in row.items():
                if isinstance(v, list):
                    cleaned[k] = '; '.join(str(i) for i in v)
                else:
                    cleaned[k] = v
            writer.writerow(cleaned)
    print(f'Saved {len(data)} rows to {outfile}')


def save_json(data, outfile):
    os.makedirs(os.path.dirname(outfile) or '.', exist_ok=True)
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f'Saved {len(data)} items to {outfile}')


def load_urls(filepath):
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GetYourGuide Scraper')
    parser.add_argument('--search', type=str, help='Search query (e.g. "paris tours")')
    parser.add_argument('--detail', action='store_true', help='Scrape activity detail pages')
    parser.add_argument('--reviews', action='store_true', help='Scrape reviews from activity pages')
    parser.add_argument('--i', type=str, default='urls.txt', help='Input file with URLs (one per line)')
    parser.add_argument('--max-pages', type=int, default=3, help='Max search result pages to scrape')
    parser.add_argument('--max-reviews', type=int, default=50, help='Max reviews per activity')
    parser.add_argument('--output', type=str, default='data/', help='Output directory')
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='both', help='Output format')
    parser.add_argument('--debug', action='store_true', help='Debug mode (show browser)')
    args = parser.parse_args()

    with GetYourGuide(debug=args.debug) as scraper:

        # ── Search mode ──
        if args.search:
            print(f'Searching for: {args.search}')
            activities = scraper.search_activities(args.search, max_pages=args.max_pages)
            print(f'Found {len(activities)} activities')

            if activities:
                if args.format in ('csv', 'both'):
                    save_csv(activities, SEARCH_FIELDS, os.path.join(args.output, 'search_results.csv'))
                if args.format in ('json', 'both'):
                    save_json(activities, os.path.join(args.output, 'search_results.json'))

        # ── Detail mode ──
        elif args.detail:
            urls = load_urls(args.i)
            print(f'Scraping details for {len(urls)} activities')
            details = []

            for url in urls:
                detail = scraper.get_activity_detail(url)
                details.append(detail)
                print(f'  Scraped: {detail.get("title", "Unknown")}')

            if details:
                if args.format in ('csv', 'both'):
                    save_csv(details, DETAIL_FIELDS, os.path.join(args.output, 'activity_details.csv'))
                if args.format in ('json', 'both'):
                    save_json(details, os.path.join(args.output, 'activity_details.json'))

        # ── Reviews mode ──
        elif args.reviews:
            urls = load_urls(args.i)
            print(f'Scraping reviews for {len(urls)} activities')
            all_reviews = []

            for url in urls:
                reviews = scraper.get_reviews(url, max_reviews=args.max_reviews)
                # tag each review with the source URL
                for r in reviews:
                    r['source_url'] = url
                all_reviews.extend(reviews)
                print(f'  Got {len(reviews)} reviews from {url}')

            if all_reviews:
                review_fields = REVIEW_FIELDS + ['source_url']
                if args.format in ('csv', 'both'):
                    save_csv(all_reviews, review_fields, os.path.join(args.output, 'reviews.csv'))
                if args.format in ('json', 'both'):
                    save_json(all_reviews, os.path.join(args.output, 'reviews.json'))

        else:
            parser.print_help()
