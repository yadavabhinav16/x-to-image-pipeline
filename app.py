import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from scraper import scrape_thread, fallback_scrape
from image_generator import generate_thread_image

# Global PTB application
application: ApplicationBuilder = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global application
    try:
        application = (
            ApplicationBuilder()
            .token(os.environ.get("TELEGRAM_TOKEN"))
            .build()
        )
    except Exception as e:
        print(f"Application build failed: {e}")
        raise

    # Add your handler
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        print(f"Received: {text}")  # Debug in Render logs

        import re
        url_match = re.search(r'https://(x\.com|twitter\.com)/[^/]+/status/(\d+)', text)
        if not url_match:
            await update.message.reply_text("Invalid X URL. Send a thread link.")
            return

        tweet_id = url_match.group(2)
        await update.message.reply_text("Processing thread... ⚽")

        try:
            thread = scrape_thread(tweet_id)
            if not thread or len(thread) == 0:
                resp = requests.post(
                    f"{os.environ.get('APP_URL')}/fallback",
                    json={"tweet_id": tweet_id},
                    timeout=15
                )
                resp.raise_for_status()
                thread = resp.json()

            if not thread:
                raise ValueError("No thread scraped")

            image_bytes = generate_thread_image(thread)
            await update.message.reply_photo(
                photo=image_bytes,
                caption="Your Football Gem! Save & post to IG. #GemsOfFootballTwitter"
            )
        except Exception as e:
            print(f"Error: {str(e)}")
            await update.message.reply_text("Error processing. Try again later.")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Startup PTB
    await application.initialize()
    await application.start()

    # Set webhook automatically on startup (optional but convenient)
    webhook_url = f"{os.environ.get('APP_URL')}/telegram-webhook"
    await application.bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

    yield  # App runs here

    # Shutdown
    await application.stop()
    await application.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/telegram-webhook")
async def webhook(request: Request):
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, application.bot)
        if update:
            await application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        print(f"Webhook error: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal error"})

@app.post("/fallback")
async def fallback(request: Request):
    data = await request.json()
    tweet_id = data.get("tweet_id")
    try:
        thread = fallback_scrape(tweet_id)
        return {"thread": thread or []}
    except Exception as e:
        print(f"Fallback error: {e}")
        return {"error": "Fallback failed"}, 500

@app.get("/")
@app.get("/health")
async def health():
    return {"status": "healthy", "bot": "running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)