# -*- coding: utf-8 -*-

"""
Unified Tour Scraper — runs GetYourGuide + TripAdvisor in parallel.

Uses Selenium for GYG, omkarcloud API for TripAdvisor (1,000 free requests/month).

Usage:
    # Search both platforms at once
    python unified_scraper.py search "paris tours"

    # Search + get reviews from both
    python unified_scraper.py search "rome" --reviews --max-pages 2

    # Only one platform
    python unified_scraper.py search "london" --sources gyg
    python unified_scraper.py search "london" --sources ta

    # Get reviews for a specific place
    python unified_scraper.py reviews "Eiffel Tower Paris" --max-pages 3

    # Set API key (only needed once, saved to .env)
    python unified_scraper.py set-key YOUR_API_KEY
"""

import sys
import os
import argparse
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add GYG scraper to path
SCRAPER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SCRAPER_ROOT, 'getyourguide-scraper'))

from getyourguide import GetYourGuide
from tripadvisor_api import TripAdvisorAPI

SEARCH_FIELDS = ['source', 'title', 'url', 'rating', 'review_count', 'price', 'duration', 'description', 'categories', 'image_url']
REVIEW_FIELDS = ['source', 'place', 'review_id', 'title', 'text', 'rating', 'author', 'date', 'trip_type', 'language']

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')


# ── API Key ─────────────────────────────────────────────────────────────

def load_api_key():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith('TRIPADVISOR_API_KEY='):
                    return line.split('=', 1)[1].strip()
    return os.environ.get('TRIPADVISOR_API_KEY', '')


def save_api_key(key):
    with open(ENV_FILE, 'w') as f:
        f.write(f'TRIPADVISOR_API_KEY={key}\n')
    print(f'API key saved to {ENV_FILE}')


# ── GYG Wrapper ─────────────────────────────────────────────────────────

def run_gyg_search(query, max_pages, debug):
    print('[GYG] Starting search...')
    with GetYourGuide(debug=debug) as scraper:
        raw = scraper.search_activities(query, max_pages=max_pages)

    results = []
    for item in raw:
        results.append({
            'source': 'getyourguide',
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'rating': item.get('rating'),
            'review_count': item.get('review_count'),
            'price': item.get('price', ''),
            'duration': item.get('duration', ''),
            'description': '',
            'categories': '',
            'image_url': item.get('image_url', ''),
        })
    print(f'[GYG] Found {len(results)} activities')
    return results


# ── TripAdvisor API Wrapper ─────────────────────────────────────────────

def run_ta_search(query, max_pages, api_key):
    # TA attractions API expects a city name, not a full search phrase
    # Extract first word as city (e.g. "paris tours" -> "paris")
    city = query.strip().split()[0]
    print(f'[TA] Searching attractions in "{city}"...')
    api = TripAdvisorAPI(api_key)
    raw = api.search_attractions(city, max_pages=max_pages)

    results = []
    for item in raw:
        categories = ', '.join(c['name'] for c in item.get('categories', []))
        results.append({
            'source': 'tripadvisor',
            'title': item.get('name', ''),
            'url': item.get('link', ''),
            'rating': item.get('rating'),
            'review_count': item.get('reviews'),
            'price': item.get('pricing_text', ''),
            'duration': '',
            'description': item.get('description', ''),
            'categories': categories,
            'image_url': item.get('featured_image', ''),
        })
    print(f'[TA] Found {len(results)} attractions')
    return results


def run_ta_reviews(query, max_pages, api_key):
    print(f'[TA] Fetching reviews for "{query}"...')
    api = TripAdvisorAPI(api_key)
    raw = api.get_reviews(query, max_pages=max_pages)

    results = []
    for rev in raw:
        reviewer = rev.get('reviewer', {})
        trip = rev.get('trip', {})
        results.append({
            'source': 'tripadvisor',
            'place': query,
            'review_id': rev.get('review_id', ''),
            'title': rev.get('title', ''),
            'text': rev.get('text', ''),
            'rating': rev.get('rating'),
            'author': reviewer.get('username', ''),
            'date': rev.get('published_at_date', ''),
            'trip_type': trip.get('type', ''),
            'language': rev.get('language', ''),
        })
    print(f'[TA] Got {len(results)} reviews')
    return results


# ── Output ──────────────────────────────────────────────────────────────

def save_csv(data, fields, filepath):
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    print(f'  Saved {len(data)} rows to {filepath}')


def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f'  Saved {len(data)} items to {filepath}')


def save_results(results, fields, output_dir, fmt, prefix='search'):
    combined = []

    for source_key, items in results.items():
        if not items:
            continue
        combined.extend(items)
        label = 'gyg' if source_key == 'gyg' else 'ta'
        if fmt in ('csv', 'both'):
            save_csv(items, fields, os.path.join(output_dir, f'{label}_{prefix}.csv'))
        if fmt in ('json', 'both'):
            save_json(items, os.path.join(output_dir, f'{label}_{prefix}.json'))

    if combined:
        if fmt in ('csv', 'both'):
            save_csv(combined, fields, os.path.join(output_dir, f'combined_{prefix}.csv'))
        if fmt in ('json', 'both'):
            save_json(combined, os.path.join(output_dir, f'combined_{prefix}.json'))


# ── Parallel Execution ──────────────────────────────────────────────────

def run_parallel(tasks):
    results = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {}
        for name, (func, args) in tasks.items():
            futures[executor.submit(func, *args)] = name

        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                label = 'GetYourGuide' if name == 'gyg' else 'TripAdvisor'
                print(f'[{label}] ERROR: {e}')
                results[name] = []

    return results


# ── CLI ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Unified Tour Scraper — GetYourGuide + TripAdvisor in parallel',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    subparsers = parser.add_subparsers(dest='command')

    # ── search ──
    search_p = subparsers.add_parser('search', help='Search both platforms')
    search_p.add_argument('query', type=str, help='Search query (e.g. "paris tours")')
    search_p.add_argument('--sources', nargs='+', default=['gyg', 'ta'],
                          choices=['gyg', 'ta'], help='Platforms (default: both)')
    search_p.add_argument('--max-pages', type=int, default=1,
                          help='Pages per platform (default: 1)')
    search_p.add_argument('--output', type=str, default='data/')
    search_p.add_argument('--format', choices=['csv', 'json', 'both'], default='both')
    search_p.add_argument('--debug', action='store_true', help='Show GYG browser')

    # ── reviews ──
    reviews_p = subparsers.add_parser('reviews', help='Get TripAdvisor reviews for a place')
    reviews_p.add_argument('query', type=str, help='Place name or URL')
    reviews_p.add_argument('--max-pages', type=int, default=1,
                           help='Review pages (20 per page, default: 1)')
    reviews_p.add_argument('--output', type=str, default='data/')
    reviews_p.add_argument('--format', choices=['csv', 'json', 'both'], default='both')

    # ── set-key ──
    key_p = subparsers.add_parser('set-key', help='Save TripAdvisor API key')
    key_p.add_argument('key', type=str, help='Your omkarcloud API key')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # ── set-key command ──
    if args.command == 'set-key':
        save_api_key(args.key)
        sys.exit(0)

    # ── Load API key for TA commands ──
    api_key = load_api_key()

    # ── search command ──
    if args.command == 'search':
        print(f'=== Unified Tour Scraper ===')
        print(f'Query: "{args.query}"')
        print(f'Sources: {", ".join(s.upper() for s in args.sources)}')

        tasks = {}
        if 'gyg' in args.sources:
            tasks['gyg'] = (run_gyg_search, (args.query, args.max_pages, args.debug))
        if 'ta' in args.sources:
            if not api_key:
                print('[TA] No API key found. Run: python unified_scraper.py set-key YOUR_KEY')
            else:
                tasks['ta'] = (run_ta_search, (args.query, args.max_pages, api_key))

        print(f'Running {len(tasks)} scraper(s) in parallel...\n')
        start = time.time()
        results = run_parallel(tasks)
        elapsed = time.time() - start

        total = sum(len(v) for v in results.values())
        print(f'\n=== Done in {elapsed:.1f}s — {total} total results ===\n')

        if total > 0:
            save_results(results, SEARCH_FIELDS, args.output, args.format, 'search')

    # ── reviews command ──
    elif args.command == 'reviews':
        if not api_key:
            print('No API key found. Run: python unified_scraper.py set-key YOUR_KEY')
            sys.exit(1)

        print(f'=== Fetching Reviews ===')
        start = time.time()
        reviews = run_ta_reviews(args.query, args.max_pages, api_key)
        elapsed = time.time() - start

        print(f'\n=== Done in {elapsed:.1f}s — {len(reviews)} reviews ===\n')

        if reviews:
            if args.format in ('csv', 'both'):
                save_csv(reviews, REVIEW_FIELDS, os.path.join(args.output, 'ta_reviews.csv'))
            if args.format in ('json', 'both'):
                save_json(reviews, os.path.join(args.output, 'ta_reviews.json'))
