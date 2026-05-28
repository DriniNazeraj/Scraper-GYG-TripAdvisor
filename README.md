# Scraper - GetYourGuide & TripAdvisor

A unified tour/activity scraper that pulls data from **GetYourGuide** and **TripAdvisor** simultaneously, running both in parallel from a single command.

- **GetYourGuide**: Selenium + BeautifulSoup (scrapes search results with ratings, prices, durations)
- **TripAdvisor**: [omkarcloud API](https://github.com/omkarcloud/tripadvisor-scraper) (attractions, reviews, ratings - 1,000 free requests/month)

---

## Setup

### 1. Install dependencies

```bash
pip install selenium beautifulsoup4 lxml requests undetected-chromedriver selenium-stealth
```

> Requires **Python 3.10+** and **Google Chrome** installed.

### 2. Get a TripAdvisor API key (free)

1. Create an account at [omkar.cloud](https://www.omkar.cloud) (takes 2 minutes)
2. Copy your API key
3. Save it:

```bash
cd unified-scraper
python unified_scraper.py set-key YOUR_API_KEY_HERE
```

---

## Usage

All commands are run from the `unified-scraper/` directory.

### Search both platforms at once

```bash
python unified_scraper.py search "paris tours"
```

This runs GYG (Selenium) and TripAdvisor (API) **in parallel** and outputs:

| File | Content |
|------|---------|
| `data/gyg_search.csv` | GetYourGuide results only |
| `data/ta_search.csv` | TripAdvisor results only |
| `data/combined_search.csv` | Both merged, with `source` column |

All files also saved as `.json`.

### Search options

```bash
# More pages of results
python unified_scraper.py search "rome" --max-pages 3

# Only one platform
python unified_scraper.py search "london" --sources gyg
python unified_scraper.py search "london" --sources ta

# JSON only
python unified_scraper.py search "barcelona" --format json

# Debug mode (shows browser window for GYG)
python unified_scraper.py search "paris" --debug
```

### Get TripAdvisor reviews

```bash
# 20 reviews per page
python unified_scraper.py reviews "Eiffel Tower Paris"

# More reviews
python unified_scraper.py reviews "Louvre Museum Paris" --max-pages 5
```

Output: `data/ta_reviews.csv` and `data/ta_reviews.json`

### Use GetYourGuide scraper standalone

```bash
cd getyourguide-scraper

# Search
python scraper.py --search "paris tours" --max-pages 3

# Scrape activity details (put URLs in urls.txt first)
python scraper.py --detail --i urls.txt

# Scrape reviews
python scraper.py --reviews --i urls.txt --max-reviews 100
```

---

## Project Structure

```
Scraper/
    unified-scraper/           # Main entry point - runs both in parallel
        unified_scraper.py     # CLI + parallel orchestration
        tripadvisor_api.py     # TripAdvisor API client (omkarcloud)
        .env                   # Your API key (not committed)
        data/                  # Output directory

    getyourguide-scraper/      # GYG Selenium scraper
        getyourguide.py        # GetYourGuide scraper class
        scraper.py             # GYG standalone CLI
        inspect_page.py        # Selector debugging tool
        data/                  # Output directory

    tripadvisor-scraper-reviews/  # Original TA Selenium scraper (reference)
        tripadvisor.py         # TripAdvisor class (fixed, but TA blocks Selenium in 2026)
        scraper.py             # TA standalone CLI
```

---

## Data Fields

### Search results (`combined_search.csv`)

| Field | GYG | TripAdvisor |
|-------|-----|-------------|
| `source` | getyourguide | tripadvisor |
| `title` | Activity name | Attraction name |
| `url` | Full link | Full link |
| `rating` | 1-5 score | 1-5 score |
| `review_count` | Number | Number |
| `price` | Price text | Ticket price |
| `duration` | Time + extras | - |
| `description` | - | Short description |
| `categories` | - | Category tags |

### Reviews (`ta_reviews.csv`)

| Field | Description |
|-------|-------------|
| `review_id` | Unique review ID |
| `title` | Review title |
| `text` | Full review text |
| `rating` | 1-5 star rating |
| `author` | Reviewer username |
| `date` | Published date |
| `trip_type` | Solo, couple, family, etc. |
| `language` | Review language |

---

## Notes

- **GetYourGuide** is scraped via Selenium (headless Chrome). The CSS selectors may need updating if GYG changes their HTML structure. Use `inspect_page.py` to recalibrate.
- **TripAdvisor** blocks all Selenium/automated access (Cloudflare Datadome) as of 2026. That's why we use the omkarcloud API instead.
- The free API tier gives **1,000 requests/month**. Each search page or review page = 1 request.
- API key is stored locally in `.env` and never committed to git.

---

## Credits & Attribution

This project includes modified code from the following open-source projects:

- **[gaspa93/tripadvisor-scraper](https://github.com/gaspa93/tripadvisor-scraper)** - Original TripAdvisor Selenium + BeautifulSoup scraper. Our `tripadvisor-scraper-reviews/` directory is a modified version with bug fixes and updated Selenium API calls. The scraper class pattern (context manager, search/reviews/place methods) inspired the GetYourGuide scraper architecture.

- **[omkarcloud/tripadvisor-scraper](https://github.com/omkarcloud/tripadvisor-scraper)** - TripAdvisor Scraper API used for the TripAdvisor data in the unified scraper. Provides the API that powers all TripAdvisor search and review functionality.

- **[scrapehero-code/tripadvisor-scraper](https://github.com/scrapehero-code/tripadvisor-scraper)** - Referenced for scraping patterns (requests + selectorlib approach).

- **[gkzz/deephotel](https://github.com/gkzz/deephotel)** - Referenced for Scrapy spider architecture (TripAdvisor + Booking.com). Based on [monkeylearn/hotel-review-analysis](https://github.com/monkeylearn/hotel-review-analysis).

The GetYourGuide scraper (`getyourguide-scraper/`) and the unified orchestrator (`unified-scraper/`) are original code written for this project.

---

## License

MIT License - see individual credited repositories for their respective licenses.
