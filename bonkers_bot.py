import logging
import re
import json
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

# --- Configuration ---
# Replace with your actual Telegram Bot Token
BOT_TOKEN = "8117094402:AAF_AkMyf9aSP3BQPSHAaeFTfdK7lh2zxFE"
# How often to check prices, in seconds. (e.g., 3600 for 1 hour)
CHECK_INTERVAL_SECONDS = 3600

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- NEW, RELIABLE Web Scraping Logic ---
async def get_price_from_json_endpoint(url: str) -> float:
    """
    Scrapes the product price by fetching the .json endpoint of a Shopify product URL.
    This method is much faster and more reliable than browser-based scraping.

    Args:
        url: The product URL.

    Returns:
        The price as a float.

    Raises:
        Exception: If the request fails, the JSON is invalid, or the price is not found.
    """
    json_url = f"{url}.json"
    logger.info(f"Fetching JSON endpoint: {json_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(json_url, headers=headers, follow_redirects=True, timeout=20.0)
            response.raise_for_status()  # Raise an exception for non-200 status codes

        data = response.json()
        
        # ** FIX **: Extract the price from the first variant. The price is a string, not in cents.
        if 'product' in data and 'variants' in data['product'] and data['product']['variants']:
            price_str = data['product']['variants'][0]['price']
            # Convert the price string directly to a float
            price = float(price_str)
            return price
        else:
            raise Exception("Price information not found in the product's JSON data structure.")

    except httpx.RequestError as e:
        logger.error(f"HTTP Request failed for {json_url}: {e}")
        raise Exception(f"Failed to connect to the website. Please check the URL.")
    except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
        logger.error(f"Failed to parse product JSON for {json_url}: {e}")
        raise Exception("The website's data format seems to have changed. Could not extract price.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while scraping {json_url}: {e}")
        raise


# --- Bot Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    await update.message.reply_text(
        "👋 Welcome to the Price Tracker Bot!\n\n"
        "Use the following commands:\n\n"
        "🔹 `/track <URL> <TARGET_PRICE>`\n"
        "   to start tracking a new product.\n\n"
        "🔹 `/list`\n"
        "   to see all products you are tracking.\n\n"
        "🔹 `/untrack <URL>`\n"
        "   to stop tracking a product."
    )

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /track command. Adds a product to the tracking list."""
    chat_id = update.effective_chat.id
    try:
        if len(context.args) < 2:
            raise ValueError("Not enough arguments")
        
        # Clean the URL to remove tracking parameters
        url = context.args[0].split('?')[0]
        target_price = float(context.args[1])

        if 'tracked_items' not in context.chat_data:
            context.chat_data['tracked_items'] = {}
            
        if url in context.chat_data['tracked_items']:
            await update.message.reply_text("ℹ️ You are already tracking this product. Use /list to see your tracked items.")
            return

        await update.message.reply_text(f"🔍 Checking initial price for: {url}")
        
        current_price = await get_price_from_json_endpoint(url)
        
        context.chat_data['tracked_items'][url] = {'target_price': target_price, 'initial_price': current_price}
        
        await update.message.reply_text(
            f"✅ Tracking started!\n\n"
            f"Product: {url}\n"
            f"Current Price: ₹{current_price:,.2f}\n"
            f"Your Target: ₹{target_price:,.2f}\n\n"
            f"I will notify you if the price drops to or below your target."
        )

        job_name = f'job_{chat_id}'
        # Access job_queue through the application object for reliability
        job_queue = context.application.job_queue
        if not job_queue.get_jobs_by_name(job_name):
            job_queue.run_repeating(
                price_check_callback,
                interval=CHECK_INTERVAL_SECONDS,
                first=10,
                chat_id=chat_id,
                name=job_name
            )
            logger.info(f"Started new job: {job_name}")

    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Invalid format. Please use:\n/track <URL> <TARGET_PRICE>")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting up tracking: {e}")


async def list_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /list command. Shows tracked items."""
    if not context.chat_data.get('tracked_items'):
        await update.message.reply_text("You are not tracking any products yet. Use /track to add one!")
        return

    message = "🛍️ Here are the products you are tracking:\n\n"
    for url, data in context.chat_data['tracked_items'].items():
        message += f"🔗 **Product**: `{url}`\n"
        message += f"🎯 **Target Price**: ₹{data['target_price']:,.2f}\n"
        message += f"📈 **Initial Price**: ₹{data.get('initial_price'):,.2f}\n\n"
        
    await update.message.reply_text(message, parse_mode='Markdown')


async def untrack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /untrack command. Removes a product from tracking."""
    chat_id = update.effective_chat.id
    try:
        if not context.args:
            raise IndexError
        url_to_remove = context.args[0].split('?')[0]
        if context.chat_data.get('tracked_items', {}).pop(url_to_remove, None):
            await update.message.reply_text(f"✅ Stopped tracking: {url_to_remove}")
            
            if not context.chat_data['tracked_items']:
                job_name = f'job_{chat_id}'
                # Access job_queue through the application object for reliability
                job_queue = context.application.job_queue
                jobs = job_queue.get_jobs_by_name(job_name)
                for job in jobs:
                    job.schedule_removal()
                logger.info(f"Removed job {job_name} as no items are left.")
        else:
            await update.message.reply_text("❌ You are not tracking this product.")
    except IndexError:
        await update.message.reply_text("⚠️ Please provide a URL to untrack:\n/untrack <URL>")


# --- Recurring Job Callback ---
async def price_check_callback(context: ContextTypes.DEFAULT_TYPE):
    """The function that is called by the JobQueue to check prices."""
    job = context.job
    chat_id = job.chat_id
    
    if chat_id not in context.application.chat_data:
        logger.warning(f"Could not find chat_data for chat_id {chat_id}. Stopping job.")
        job.schedule_removal()
        return

    tracked_items = context.application.chat_data[chat_id].get('tracked_items', {})
    
    if not tracked_items:
        logger.info(f"No items to track for chat_id {chat_id}. Stopping job.")
        job.schedule_removal()
        return

    logger.info(f"Running scheduled price check for chat_id: {chat_id}")
    
    items_to_check = dict(tracked_items)
    items_to_remove = [] 

    for url, data in items_to_check.items():
        target_price = data['target_price']
        try:
            current_price = await get_price_from_json_endpoint(url)
            logger.info(f"Checked {url}: Current Price ₹{current_price:,.2f}, Target ₹{target_price:,.2f}")
            
            if current_price <= target_price:
                message = (
                    f"🎉 **Price Drop Alert!** 🎉\n\n"
                    f"The price for a product you're tracking has dropped to **₹{current_price:,.2f}**!\n\n"
                    f"🎯 Your Target: ₹{target_price:,.2f}\n"
                    f"🔗 Get it here: {url}"
                )
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                items_to_remove.append(url)

        except Exception as e:
            logger.error(f"Failed to check price for {url} for chat_id {chat_id}: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Could not check price for {url}. It may be out of stock or the page has changed. It will be untracked.")
            items_to_remove.append(url)

    if items_to_remove:
        for url in items_to_remove:
            if url in context.application.chat_data[chat_id]['tracked_items']:
                del context.application.chat_data[chat_id]['tracked_items'][url]
                logger.info(f"Removed {url} from tracking for chat_id {chat_id}.")
        
        if not context.application.chat_data[chat_id]['tracked_items']:
            logger.info(f"No items left for chat_id {chat_id}. Stopping job.")
            job.schedule_removal()


# --- Main Bot Setup ---
def main():
    """Builds and runs the Telegram bot."""
    persistence = PicklePersistence(filepath="./pricetracker_bot_data")

    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track))
    app.add_handler(CommandHandler("list", list_items))
    app.add_handler(CommandHandler("untrack", untrack))

    logger.info("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
