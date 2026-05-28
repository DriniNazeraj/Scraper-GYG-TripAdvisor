# -*- coding: utf-8 -*-

"""
Selector Inspector — helps you tune CSS selectors for GetYourGuide.

Opens a GetYourGuide page in debug mode (visible browser) and dumps
the page HTML so you can find the right selectors. Also prints a
summary of common element patterns found on the page.

Usage:
    python inspect_page.py "https://www.getyourguide.com/s/?q=paris"
    python inspect_page.py "https://www.getyourguide.com/paris-l16/some-tour-t12345/"
"""

import sys
import re
import time
import json
from collections import Counter

try:
    import undetected_chromedriver as uc
    USE_UC = True
except ImportError:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    USE_UC = False

from bs4 import BeautifulSoup


def get_driver():
    if USE_UC:
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        return uc.Chrome(options=options)
    else:
        options = Options()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        return webdriver.Chrome(options=options)


def inspect(url):
    print(f'Opening: {url}')
    driver = get_driver()
    driver.get(url)
    time.sleep(5)

    # dismiss popups
    from selenium.webdriver.common.by import By
    for sel in ['button[id*="cookie" i]', 'button[class*="accept" i]', 'button[class*="consent" i]']:
        try:
            driver.find_element(By.CSS_SELECTOR, sel).click()
            time.sleep(0.5)
        except Exception:
            pass

    # scroll to load content
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # save raw HTML
    with open('data/inspected_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print('Saved HTML to data/inspected_page.html')

    # Analyze classes used on the page
    print('\n=== CLASS PATTERNS ===')
    class_counter = Counter()
    for tag in soup.find_all(True):
        for cls in tag.get('class', []):
            class_counter[cls] += 1

    # show classes containing key terms
    keywords = ['card', 'activity', 'price', 'rating', 'review', 'title', 'duration',
                'result', 'listing', 'tour', 'name', 'score', 'star', 'author', 'date']
    for kw in keywords:
        matches = [(cls, count) for cls, count in class_counter.items() if kw.lower() in cls.lower()]
        if matches:
            print(f'\n  "{kw}" classes:')
            for cls, count in sorted(matches, key=lambda x: -x[1])[:10]:
                print(f'    .{cls}  ({count}x)')

    # Show data attributes
    print('\n=== DATA ATTRIBUTES ===')
    data_attrs = Counter()
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            if attr.startswith('data-'):
                data_attrs[attr] += 1
    for attr, count in data_attrs.most_common(30):
        print(f'  {attr}  ({count}x)')

    # Show activity-like links
    print('\n=== ACTIVITY LINKS (sample) ===')
    activity_links = soup.find_all('a', href=re.compile(r'-t\d+'))
    for link in activity_links[:10]:
        print(f'  {link.get("href", "")}')
        if link.get('class'):
            print(f'    classes: {" ".join(link["class"])}')

    # Show JSON-LD
    print('\n=== JSON-LD STRUCTURED DATA ===')
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
            print('  ...')
        except Exception:
            pass

    print('\nBrowser is still open — inspect elements manually with F12.')
    print('Press Enter to close...')
    input()
    driver.quit()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python inspect_page.py <url>')
        sys.exit(1)
    inspect(sys.argv[1])
