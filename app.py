import os
import asyncio
from flask import Flask, request, jsonify
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)
from scraper import scrape_thread, fallback_scrape
from image_generator import generate_thread_image

app = Flask(__name__)

# Global application (we'll build and run it later)
application = None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    import re
    url_match = re.search(r'https://(x\.com|twitter\.com)/[^/]+/status/(\d+)', text)
    if not url_match:
        await update.message.reply_text('Invalid X URL.')
        return
    tweet_id = url_match.group(2)
    await update.message.reply_text('Processing thread... ⚽')
    try:
        # Primary scrape
        thread = scrape_thread(tweet_id)
        if not thread or len(thread) == 0:
            # Fallback: Call internal endpoint (synchronous requests inside async)
            response = requests.post(f"{os.environ.get('APP_URL')}/fallback", json={'tweet_id': tweet_id})
            thread = response.json()
        if not thread or len(thread) == 0:
            raise ValueError('Scrape failed.')
        # Generate image in-memory (this is sync, but fine for low traffic)
        image_bytes = generate_thread_image(thread)
        # Send to Telegram
        await update.message.reply_photo(photo=image_bytes, caption='Your Football Gem! Save & post to IG. #GemsOfFootballTwitter')
    except Exception as e:
        print(e)
        await update.message.reply_text('Error processing. Try again later.')

# Flask routes remain the same
@app.route('/telegram-webhook', methods=['GET', 'POST'])
async def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
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

def run_flask():
    from waitress import serve
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))

if __name__ == '__main__':
    # Build the application (no Dispatcher!)
    application = (
        ApplicationBuilder()
        .token(os.environ.get('TELEGRAM_TOKEN'))
        .build()
    )

    # Add the handler (use filters.TEXT instead of old Filters)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # For Render: we run Flask in main thread, but need to start async bot polling or webhook setup
    # Since we're using webhook (preferred on Render), we don't need polling
    # But we must set the webhook manually via BotFather or once after deploy

    # Run Flask synchronously (waitress)
    run_flask()