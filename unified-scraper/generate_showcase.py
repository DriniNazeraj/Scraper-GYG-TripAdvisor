# -*- coding: utf-8 -*-
"""Generate the HTML showcase report with real data."""

import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load data
with open('data/_showcase_restaurant.json', 'r', encoding='utf-8') as f:
    rest_data = json.load(f)

with open('data/_showcase_reviews.json', 'r', encoding='utf-8') as f:
    rev_data = json.load(f)

with open('data/gyg_search.json', 'r', encoding='utf-8') as f:
    gyg_data = json.load(f)

rest = rest_data['results'][0]
review = rev_data['results'][0]
meta = {k: v for k, v in rev_data.items() if k != 'results'}
reviewer = review.get('reviewer', {})
trip = review.get('trip', {})

# Build subratings rows
subratings_html = ''
for sr in review.get('subratings', []):
    subratings_html += f'<tr><td style="padding-left:30px">{sr["label"]}</td><td>{sr["rating"]}/5</td></tr>\n'

# Build subratings inline
subratings_inline = ' | '.join(f'{sr["label"]}: {sr["rating"]}/5' for sr in review.get('subratings', []))

# GYG example rows
gyg_rows = ''
for g in gyg_data[:5]:
    gyg_rows += f'''<tr>
    <td>{g['title']}</td>
    <td>{g['rating'] or '-'}</td>
    <td>{g['review_count'] or '-'}</td>
    <td>{g['price']}</td>
    <td>{g['duration']}</td>
    </tr>\n'''

# Stars helper
def stars(n):
    return '&#9733;' * int(n) + '&#9734;' * (5 - int(n))

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scraper Showcase - What We Can Extract</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
  h1 {{ text-align: center; color: #1a1a2e; font-size: 2.2em; margin: 30px 0 10px; }}
  .subtitle {{ text-align: center; color: #666; font-size: 1.1em; margin-bottom: 40px; }}
  h2 {{ color: #16213e; margin: 35px 0 15px; padding-bottom: 8px; border-bottom: 3px solid #0f3460; }}
  h3 {{ color: #0f3460; margin: 20px 0 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 15px 0 25px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  th {{ background: #0f3460; color: white; padding: 12px 15px; text-align: left; font-weight: 600; }}
  td {{ padding: 10px 15px; border-bottom: 1px solid #eee; }}
  tr:hover td {{ background: #f0f4ff; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600; }}
  .badge-gyg {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-ta {{ background: #e3f2fd; color: #1565c0; }}
  .section {{ background: white; border-radius: 12px; padding: 25px 30px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .cmd {{ background: #1a1a2e; color: #00ff88; padding: 15px 20px; border-radius: 8px; font-family: monospace; font-size: 0.95em; margin: 10px 0; overflow-x: auto; }}
  .review-box {{ background: #fafafa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin: 15px 0; }}
  .star {{ color: #ffc107; font-size: 1.2em; }}
  .field-name {{ font-weight: 600; color: #0f3460; }}
  .four-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; }}
  @media (max-width: 768px) {{ .four-col {{ grid-template-columns: 1fr 1fr; }} }}
  .stat-box {{ text-align: center; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }}
  .stat-num {{ font-size: 2.5em; font-weight: 700; color: #0f3460; }}
  .stat-label {{ color: #666; font-size: 0.9em; }}
</style>
</head>
<body>
<div class="container">

<h1>Scraper Showcase</h1>
<p class="subtitle">GetYourGuide + TripAdvisor | Unified Tour &amp; Activity Scraper</p>

<div class="four-col" style="margin-bottom: 30px;">
  <div class="stat-box">
    <div class="stat-num">2</div>
    <div class="stat-label">Platforms</div>
  </div>
  <div class="stat-box">
    <div class="stat-num">54+</div>
    <div class="stat-label">Results per search</div>
  </div>
  <div class="stat-box">
    <div class="stat-num">25+</div>
    <div class="stat-label">Data fields per review</div>
  </div>
  <div class="stat-box">
    <div class="stat-num">&lt;25s</div>
    <div class="stat-label">Both platforms parallel</div>
  </div>
</div>

<!-- SECTION 1: HOW IT WORKS -->
<h2>How It Works</h2>
<div class="section">
  <p>A single command searches <span class="badge badge-gyg">GetYourGuide</span> and <span class="badge badge-ta">TripAdvisor</span> simultaneously using parallel threads.</p>
  <div class="cmd">python unified_scraper.py search "paris tours"</div>
  <p style="margin-top:10px">Output: <code>combined_search.csv</code> + <code>combined_search.json</code> with all results merged.</p>
  <div class="cmd">python unified_scraper.py reviews "Ostro Beach Bar Restaurant" --max-pages 4</div>
  <p style="margin-top:10px">Output: <code>ta_reviews.csv</code> + <code>ta_reviews.json</code> with full review data.</p>
</div>

<!-- SECTION 2: GETYOURGUIDE -->
<h2><span class="badge badge-gyg">GetYourGuide</span> Data Fields</h2>

<div class="section">
<h3>Search Results (per activity)</h3>
<table>
<tr><th>Field</th><th>Type</th><th>Description</th></tr>
<tr><td class="field-name">title</td><td>string</td><td>Activity name</td></tr>
<tr><td class="field-name">url</td><td>string</td><td>Full GetYourGuide link</td></tr>
<tr><td class="field-name">rating</td><td>float</td><td>Average rating (1.0 - 5.0)</td></tr>
<tr><td class="field-name">review_count</td><td>integer</td><td>Total number of reviews</td></tr>
<tr><td class="field-name">price</td><td>string</td><td>Price text (includes original + discounted)</td></tr>
<tr><td class="field-name">price_value</td><td>float</td><td>Extracted numeric price (lowest)</td></tr>
<tr><td class="field-name">duration</td><td>string</td><td>Duration + extras (e.g. "6 hours - Skip the line")</td></tr>
<tr><td class="field-name">image_url</td><td>string</td><td>Activity thumbnail URL</td></tr>
</table>

<h3>Activity Detail Page (additional fields)</h3>
<table>
<tr><th>Field</th><th>Type</th><th>Description</th></tr>
<tr><td class="field-name">description</td><td>string</td><td>Full activity description (up to 2000 chars)</td></tr>
<tr><td class="field-name">meeting_point</td><td>string</td><td>Meeting point / location info</td></tr>
<tr><td class="field-name">highlights</td><td>list</td><td>Activity highlights</td></tr>
<tr><td class="field-name">inclusions</td><td>list</td><td>What's included</td></tr>
<tr><td class="field-name">structured_data</td><td>JSON-LD</td><td>Schema.org structured data (if available)</td></tr>
</table>

<h3>Live Example Data</h3>
<table>
<tr><th>Title</th><th>Rating</th><th>Reviews</th><th>Price</th><th>Duration</th></tr>
{gyg_rows}
</table>
</div>

<!-- SECTION 3: TRIPADVISOR -->
<h2><span class="badge badge-ta">TripAdvisor</span> Data Fields</h2>

<div class="section">
<h3>Restaurant / Attraction Info</h3>
<table>
<tr><th>Field</th><th>Type</th><th>Example (Ostro Beach Bar)</th></tr>
<tr><td class="field-name">name</td><td>string</td><td>{rest['name']}</td></tr>
<tr><td class="field-name">tripadvisor_entity_id</td><td>integer</td><td>{rest['tripadvisor_entity_id']}</td></tr>
<tr><td class="field-name">link</td><td>string</td><td><a href="{rest['link']}" style="color:#1565c0">TripAdvisor Link</a></td></tr>
<tr><td class="field-name">place_type</td><td>string</td><td>{rest['place_type']}</td></tr>
<tr><td class="field-name">coordinates.latitude</td><td>float</td><td>{rest['coordinates']['latitude']}</td></tr>
<tr><td class="field-name">coordinates.longitude</td><td>float</td><td>{rest['coordinates']['longitude']}</td></tr>
<tr><td class="field-name">featured_image</td><td>URL</td><td><img src="{rest['featured_image']}" height="50" style="border-radius:4px"></td></tr>
<tr><td class="field-name">parent_location</td><td>object</td><td>{rest['parent_location']['name']} (ID: {rest['parent_location']['tripadvisor_entity_id']})</td></tr>
</table>

<h3>Attraction Search Fields (additional)</h3>
<table>
<tr><th>Field</th><th>Type</th><th>Description</th></tr>
<tr><td class="field-name">rating</td><td>float</td><td>Average rating (1.0 - 5.0)</td></tr>
<tr><td class="field-name">reviews</td><td>integer</td><td>Total review count</td></tr>
<tr><td class="field-name">description</td><td>string</td><td>Place description</td></tr>
<tr><td class="field-name">neighborhood</td><td>string</td><td>Neighborhood name</td></tr>
<tr><td class="field-name">categories</td><td>list</td><td>Category tags (e.g. "Art Museums", "Landmarks")</td></tr>
<tr><td class="field-name">award</td><td>object</td><td>Award name, year, type (e.g. Travelers Choice)</td></tr>
<tr><td class="field-name">pricing_text</td><td>string</td><td>Ticket pricing (e.g. "Admission from $51")</td></tr>
<tr><td class="field-name">commerce.tickets_link</td><td>URL</td><td>Direct tickets link</td></tr>
<tr><td class="field-name">commerce.tours_link</td><td>URL</td><td>Related tours link</td></tr>
<tr><td class="field-name">experiences_count</td><td>integer</td><td>Number of related experiences</td></tr>
</table>

<h3>Review Fields ({meta['count']} reviews available for Ostro)</h3>
<table>
<tr><th>Field</th><th>Type</th><th>Example</th></tr>
<tr><td class="field-name">review_id</td><td>integer</td><td>{review['review_id']}</td></tr>
<tr><td class="field-name">review_link</td><td>URL</td><td><a href="{review['review_link']}" style="color:#1565c0">View on TripAdvisor</a></td></tr>
<tr><td class="field-name">title</td><td>string</td><td>{review['title']}</td></tr>
<tr><td class="field-name">text</td><td>string</td><td>Full review text (unlimited length)</td></tr>
<tr><td class="field-name">rating</td><td>integer</td><td>{review['rating']}/5 <span class="star">{stars(review['rating'])}</span></td></tr>
<tr><td class="field-name">subratings</td><td>list</td><td>Breakdown by category:</td></tr>
{subratings_html}
<tr><td class="field-name">like_count</td><td>integer</td><td>{review['like_count']}</td></tr>
<tr><td class="field-name">language</td><td>string</td><td>{review['language']}</td></tr>
<tr><td class="field-name">is_translated</td><td>boolean</td><td>{review['is_translated']}</td></tr>
<tr><td class="field-name">original_language</td><td>string</td><td>{review['original_language']}</td></tr>
<tr><td class="field-name">owner_response</td><td>string/null</td><td>{review['owner_response'] or 'None (restaurant has not replied)'}</td></tr>
<tr><td class="field-name">trip.trip_type</td><td>string</td><td>{trip.get('trip_type', '-')}</td></tr>
<tr><td class="field-name">trip.stay_date</td><td>date</td><td>{trip.get('stay_date', '-')}</td></tr>
<tr><td class="field-name">reviewer.name</td><td>string</td><td>{reviewer.get('name', '-')}</td></tr>
<tr><td class="field-name">reviewer.username</td><td>string</td><td>{reviewer.get('username', '-')}</td></tr>
<tr><td class="field-name">reviewer.profile_link</td><td>URL</td><td><a href="{reviewer.get('profile_link', '#')}" style="color:#1565c0">View Profile</a></td></tr>
<tr><td class="field-name">reviewer.avatar</td><td>URL</td><td><img src="{reviewer.get('avatar', '')}" height="30" style="border-radius:50%"></td></tr>
<tr><td class="field-name">reviewer.contribution_count</td><td>integer</td><td>{reviewer.get('contribution_count', '-')}</td></tr>
<tr><td class="field-name">reviewer.hometown</td><td>string/null</td><td>{reviewer.get('hometown') or 'Not provided'}</td></tr>
<tr><td class="field-name">reviewer.is_verified</td><td>boolean</td><td>{reviewer.get('is_verified', '-')}</td></tr>
<tr><td class="field-name">images</td><td>list</td><td>Photo URLs attached to review</td></tr>
<tr><td class="field-name">created_at_date</td><td>date</td><td>{review.get('created_at_date', '-')}</td></tr>
<tr><td class="field-name">published_at_date</td><td>date</td><td>{review.get('published_at_date', '-')}</td></tr>
</table>

<h3>Review Metadata (per query)</h3>
<table>
<tr><th>Field</th><th>Type</th><th>Description</th></tr>
<tr><td class="field-name">count</td><td>integer</td><td>Total reviews available ({meta['count']})</td></tr>
<tr><td class="field-name">per_page</td><td>integer</td><td>Reviews per API request ({meta['per_page']})</td></tr>
<tr><td class="field-name">total_pages</td><td>integer</td><td>Pages available ({meta['total_pages']})</td></tr>
<tr><td class="field-name">rating_distribution</td><td>object</td><td>Count of reviews per star rating (1-5)</td></tr>
<tr><td class="field-name">language_distribution</td><td>object</td><td>Count of reviews per language</td></tr>
<tr><td class="field-name">review_keywords</td><td>list</td><td>Most common keywords found in reviews</td></tr>
</table>
</div>

<!-- SECTION 4: REAL REVIEW EXAMPLE -->
<h2>Full Review Example (Real Data)</h2>
<div class="section">
<div class="review-box">
  <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px">
    <img src="{reviewer.get('avatar', '')}" height="45" style="border-radius:50%">
    <div>
      <strong>{reviewer.get('name', '')}</strong> <span style="color:#888">(@{reviewer.get('username', '')})</span><br>
      <span style="color:#888; font-size:0.9em">{reviewer.get('contribution_count', 0)} contributions | Trip: {trip.get('trip_type', '-')} | {review.get('published_at_date', '')}</span>
    </div>
  </div>
  <div class="star" style="margin-bottom:8px">{stars(review['rating'])} {review['rating']}/5</div>
  <p style="font-size:1.05em; margin-bottom:12px"><strong>"{review['title']}"</strong></p>
  <p style="color:#444">{review['text']}</p>
  <div style="margin-top:15px; padding-top:12px; border-top:1px solid #eee">
    <strong>Sub-ratings:</strong> {subratings_inline}
  </div>
</div>
</div>

<div style="text-align:center; padding:30px; color:#888; font-size:0.9em">
  Generated by Unified Tour Scraper | GetYourGuide (Selenium) + TripAdvisor (omkarcloud API)<br>
  GitHub: <a href="https://github.com/DriniNazeraj/Scraper-GYG-TripAdvisor" style="color:#1565c0">DriniNazeraj/Scraper-GYG-TripAdvisor</a>
</div>

</div>
</body>
</html>'''

with open('scraper_showcase.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Generated scraper_showcase.html ({len(html):,} bytes)')
