import requests
from bs4 import BeautifulSoup
import random
import time

# 2026 Active/High-Uptime Mirrors
NITTER_MIRRORS = [
    "https://nitter.privacydev.net",
    "https://nitter.perennialte.ch",
    "https://nitter.uni-sonia.com",
    "https://nitter.skane.xyz",
    "https://nitter.hostux.net",
]

def scrape_tweet(tweet_id, base_url):
    # Mimic a real browser to bypass basic bot detection
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Referer': f"{base_url}/"
    }
    
    try:
        url = f"{base_url}/status/{tweet_id}"
        # Add a small random delay so you don't look like a rapid-fire bot
        time.sleep(random.uniform(1.0, 2.5)) 
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Mirror {base_url} returned status {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        # ... (rest of your existing parsing logic)
        if not soup.select_one('.tweet-content'):
            return None
        tweet = {
            'user': soup.select_one('.fullname').text.strip() if soup.select_one('.fullname') else '',
            'handle': soup.select_one('.username').text.strip() if soup.select_one('.username') else '',
            'avatar': base_url + (soup.select_one('.tweet-avatar img')['src'] if soup.select_one('.tweet-avatar img') else ''),
            'timestamp': soup.select_one('.tweet-date a')['title'] if soup.select_one('.tweet-date a') else soup.select_one('.tweet-date').text.strip(),
            'text': (soup.select_one('.tweet-content').text.strip() + ' ⚽') if soup.select_one('.tweet-content') else '',
            'media': [],
            'parent_id': None
        }
        # Extract parent ID if replying
        replying_to = soup.select_one('.replying-to a')
        if replying_to:
            match = replying_to['href'].split('/status/')[-1] if '/status/' in replying_to['href'] else None
            if match:
                tweet['parent_id'] = match
        # Extract media thumbnails
        for img in soup.select('.tweet-body .attachment.image img, .tweet-body .still-image img'):
            src = img.get('src')
            if src:
                tweet['media'].append(base_url + src)
        return tweet
    except Exception as e:
        print(f"Scrape error for {tweet_id}: {e}")
        return None

def scrape_thread(tweet_id, level=0, max_levels=3, visited=set(), mirror_index=0):
    if level >= max_levels or tweet_id in visited:
        return []
    base_url = NITTER_MIRRORS[mirror_index]
    visited.add(tweet_id)
    tweet = scrape_tweet(tweet_id, base_url)
    if not tweet:
        return []
    thread = []
    if tweet['parent_id']:
        parent_thread = scrape_thread(tweet['parent_id'], level + 1, max_levels, visited, mirror_index)
        thread = parent_thread
    thread.append(tweet)
    return thread

def fallback_scrape(tweet_id):   # renamed for clarity
    for i, mirror in enumerate(NITTER_MIRRORS):
        try:
            print(f"Trying mirror {i+1}: {mirror}")
            thread = scrape_thread(tweet_id, 0, 3, set(), i)
            if thread and len(thread) > 0:
                print(f"✅ Success on mirror {mirror}")
                return thread
        except Exception as e:
            print(f"Mirror {mirror} failed: {e}")
            continue
    print("❌ All mirrors failed")
    return []