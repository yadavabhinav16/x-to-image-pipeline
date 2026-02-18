import os
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
from scraper import scrape_thread, fallback_scrape
from image_generator import generate_thread_image

app = Flask(__name__)
bot = Bot(token=os.environ.get('TELEGRAM_TOKEN'))

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    import re
    url_match = re.search(r'https://(x\.com|twitter\.com)/[^/]+/status/(\d+)', text)
    if not url_match:
        update.message.reply_text('Invalid X URL.')
        return
    tweet_id = url_match.group(2)
    update.message.reply_text('Processing thread... ⚽')
    try:
        # Primary scrape
        thread = scrape_thread(tweet_id)
        if not thread or len(thread) == 0:
            # Fallback: Call internal endpoint
            response = requests.post(f"{os.environ.get('APP_URL')}/fallback", json={'tweet_id': tweet_id})
            thread = response.json()
        if not thread or len(thread) == 0:
            raise ValueError('Scrape failed.')
        # Generate image in-memory
        image_bytes = generate_thread_image(thread)
        # Send to Telegram
        update.message.reply_photo(photo=image_bytes, caption='Your Football Gem! Save & post to IG. #GemsOfFootballTwitter')
    except Exception as e:
        print(e)
        update.message.reply_text('Error processing. Try again later.')

dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

@app.route('/telegram-webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(), bot)
        dispatcher.process_update(update)
    return 'ok'

@app.route('/fallback', methods=['POST'])
def fallback():
    data = request.json
    tweet_id = data.get('tweet_id')
    try:
        thread = fallback_scrape(tweet_id)
        return jsonify(thread)
    except Exception as e:
        return jsonify({'error': 'Fallback failed'}), 500

if __name__ == '__main__':
    from waitress import serve  # Use waitress for local serving
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))