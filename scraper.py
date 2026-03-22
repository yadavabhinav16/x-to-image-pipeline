import requests
import os
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultiTierScraper")

# Environment Variables
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")

class TwitterScraper:
    def __init__(self, tweet_id):
        self.tweet_id = tweet_id

    def unified_format(self, user, handle, text, avatar, timestamp):
        return {
            'user': user or "Unknown",
            'handle': f"@{handle.replace('@', '')}" if handle else "@user",
            'text': (text or "") + " ⚽",
            'avatar': avatar or "",
            'timestamp': timestamp or "Recently",
            'media': [], # Can be expanded with 'expansions' in V2
            'parent_id': None
        }

    # --- TIER 0: OFFICIAL TWITTER V2 API (The method from the video) ---
    def scrap_official_v2(self):
        if not TWITTER_BEARER_TOKEN:
            raise ValueError("Missing TWITTER_BEARER_TOKEN")

        # As explained in the video, we use expansions to get user data (hydration)
        url = f"https://api.twitter.com/2/tweets/{self.tweet_id}"
        params = {
            "tweet.fields": "created_at,text",
            "expansions": "author_id",
            "user.fields": "name,username,profile_image_url"
        }
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
        
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        tweet_data = data.get("data", {})
        user_data = data.get("includes", {}).get("users", [{}])[0]
        
        return self.unified_format(
            user=user_data.get("name"),
            handle=user_data.get("username"),
            text=tweet_data.get("text"),
            avatar=user_data.get("profile_image_url"),
            timestamp=tweet_data.get("created_at")
        )

    # --- TIER 1: Twitter AIO (RapidAPI) ---
    def scrap_aio(self):
        url = f"https://twitter-aio.p.rapidapi.com/tweet/{self.tweet_id}"
        headers = {
            "x-rapidapi-host": "twitter-aio.p.rapidapi.com",
            "x-rapidapi-key": RAPID_API_KEY
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        u = data.get("user", {})
        return self.unified_format(u.get("name"), u.get("screen_name"), data.get("text"), u.get("profile_image_url_https"), data.get("created_at"))

    # --- TIER 2: XScraper Hidden (RapidAPI) ---
    def scrap_hidden(self):
        url = "https://xscraper.p.rapidapi.com/tweet-hidden"
        headers = {
            "x-rapidapi-host": "xscraper.p.rapidapi.com",
            "x-rapidapi-key": RAPID_API_KEY
        }
        res = requests.get(url, headers=headers, params={"tweet_id": self.tweet_id}, timeout=10)
        res.raise_for_status()
        data = res.json()
        return self.unified_format(data.get("author_name"), data.get("author_handle"), data.get("tweet_text"), data.get("author_avatar"), data.get("date"))

def fallback_scrape(tweet_id):
    scraper = TwitterScraper(tweet_id)
    tiers = [
        ("Tier 0: Official V2", scraper.scrap_official_v2),
        ("Tier 1: Rapid AIO", scraper.scrap_aio),
        ("Tier 2: Rapid Hidden", scraper.scrap_hidden)
    ]

    for name, method in tiers:
        try:
            logger.info(f"Attempting {name}...")
            result = method()
            if result:
                logger.info(f"✅ Success with {name}")
                return [result]
        except Exception as e:
            logger.warning(f"⚠️ {name} failed: {str(e)}")
            continue
    return []

def scrape_thread(tweet_id):
    """
    This is the primary entry point called by app.py.
    It triggers the tiered fallback system.
    """
    return fallback_scrape(tweet_id)