# Telegram Price & Stock Tracker Bot

A versatile Telegram bot that monitors product prices and stock availability on Shopify-based e-commerce sites. Users can track products, set a target price, and receive instant notifications for price drops and restocks.

![Bot Mascot](https://i.imgur.com/your-mascot-image-url.png) 
*Note: You would replace the URL above with a link to the bot mascot image after uploading it.*

---

## ✨ Features

- **Price Tracking**: Set a target price for a product and get an alert when the price drops to or below your target.
- **Stock Monitoring**: Get notified as soon as an "Out of Stock" item becomes available again.
- **Simple Commands**: Easy-to-use commands (`/track`, `/list`, `/untrack`) for managing your tracked items.
- **Persistent Data**: The bot remembers your tracked items even if it restarts.
- **Reliable Scraping**: Uses a fast and stable JSON endpoint method to fetch product data, avoiding issues with bot detection.
- **24/7 Monitoring**: Designed to be deployed on a cloud server for continuous, around-the-clock tracking.

---

## 🛠️ How It Works

The bot leverages the `.json` endpoints available on Shopify-powered websites. Instead of "hard scraping" the HTML of a product page (which is slow and often blocked), the bot makes a direct request to a URL like `.../product-name.json`.

This returns a clean JSON object containing all product variant information, including price and availability, making the data retrieval process fast, efficient, and reliable.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A Telegram Bot Token. You can get one from the [BotFather](https://t.me/botfather).
- A free [Heroku](https://www.heroku.com/) or [Render](https://render.com/) account for deployment.

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/telegram-price-tracker-bot.git](https://github.com/your-username/telegram-price-tracker-bot.git)
    cd telegram-price-tracker-bot
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set your Bot Token:**
    Rename the `.env.example` file to `.env` and add your Telegram Bot Token:
    ```
    BOT_TOKEN="12345:ABC-DEF12345"
    ```

4.  **Run the bot locally:**
    ```bash
    python bot.py
    ```

---

## ☁️ Deployment

This bot is designed to be deployed to a cloud service like Heroku or Render to run 24/7.

### Deploying to Heroku

1.  **Create a Heroku app and set up the Heroku CLI.**

2.  **Add the Python buildpack:**
    ```bash
    heroku buildpacks:set heroku/python
    ```

3.  **Set your bot token as a config var (DO NOT hardcode it):**
    ```bash
    heroku config:set BOT_TOKEN="YOUR_ACTUAL_BOT_TOKEN"
    ```

4.  **Push the code to Heroku:**
    ```bash
    git push heroku master
    ```

5.  **Scale the worker to start the bot:**
    ```bash
    heroku ps:scale worker=1
    ```

6.  **Check the logs to ensure it's running:**
    ```bash
    heroku logs --tail
    ```

---

## 💬 Bot Commands

- `/start` - Displays a welcome message and instructions.
- `/track <URL> <TARGET_PRICE>` - Starts tracking a new product.
- `/list` - Shows all the products you are currently tracking.
- `/untrack <URL>` - Stops tracking a specific product.

---

## 📝 License

This project is open source and available under the MIT License.
