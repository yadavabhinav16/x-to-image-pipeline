import requests
from bs4 import BeautifulSoup

NITTER_MIRRORS = ['https://nitter.net', 'https://nitter.poast.org', 'https://nitter.esmailelbob.xyz']  # Add more for reliability

def scrape_tweet(tweet_id, base_url):
    try:
        url = f"{base_url}/status/{tweet_id}"
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
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

def fallback_scrape(tweet_id):
    for i in range(1, len(NITTER_MIRRORS)):
        try:
            thread = scrape_thread(tweet_id, 0, 3, set(), i)
            if thread and len(thread) > 0:
                return thread
        except Exception as e:
            print(f"Fallback mirror {i} failed: {e}")
    return []