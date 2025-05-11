import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from google.api_core.exceptions import GoogleAPIError
import schedule
import time
from datetime import datetime
import pytz

# Load API Key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("daily_digest.log"), logging.StreamHandler()]
)

# Topics
TECH_TOPICS = ["AI", "Flutter", "React Native", "SQL", "DevOps"]

# 🔔 Dummy notification (for now, use print instead of real notification or FCM)
def send_notification(title, message):
    print(f"\n[{title}]\n{message}\n")

# 🧠 Learning content generator
def get_learning_content(topic):
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        prompt = f"Explain a useful concept or coding technique in {topic} with an example in 5-7 lines."
        response = model.generate_content(prompt)
        content = response.text.strip()
        logging.info(f"Generated content for {topic}")
        return content
    except GoogleAPIError as e:
        logging.error(f"API error: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return f"Error: {str(e)}"

# 🌐 News fetcher
def get_news_update():
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        prompt = "Give me a 2-line summary of today’s latest global tech or AI news."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error fetching news: {e}"

# 😂 Meme fetcher
def get_meme_update():
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        prompt = "Share a short, funny programming meme or joke in 1-2 lines."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error fetching meme: {e}"

# 📚 First half tech tips
def send_tech_digest():
    for topic in TECH_TOPICS[:2]:
        content = get_learning_content(topic)
        send_notification(f"💻 Learn {topic}", content)

# 📚 Second half tech tips
def send_evening_tech_digest():
    for topic in TECH_TOPICS[2:]:
        content = get_learning_content(topic)
        send_notification(f"💻 Learn {topic}", content)

# 🌍 News
def send_news():
    news = get_news_update()
    send_notification("🌐 Tech News Update", news)

# 🤣 Meme
def send_meme():
    meme = get_meme_update()
    send_notification("😂 Programming Meme", meme)

# ⏰ Check active hours (11:30 AM to 11:30 PM)
def is_within_active_hours():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).time()  # <-- This ensures IST
    start = time(11, 30)
    end = time(23, 30)
    return start <= now <= end

    
# 🔄 Scheduler runner
def run_scheduler():
    # Schedule jobs
    schedule.every().day.at("11:30").do(send_tech_digest)
    schedule.every().day.at("17:00").do(send_evening_tech_digest)
    schedule.every().day.at("13:00").do(send_news)
    schedule.every().day.at("20:00").do(send_meme)

    logging.info("Scheduler started. Waiting for tasks...")

    while True:
        if is_within_active_hours():
            schedule.run_pending()
        else:
            logging.info("Outside active hours (11:30 AM - 11:30 PM). Idle...")
        time.sleep(30)

if __name__ == "__main__":
    run_scheduler()
