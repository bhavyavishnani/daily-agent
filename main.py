import schedule
import time as time_module
import logging
import datetime
import pytz
from datetime import time as datetime_time
from dotenv import load_dotenv
import os
import sys
import signal
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import json
import tempfile
import unicodedata
import google.generativeai as genai

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logging.error("GEMINI_API_KEY not found in .env file")
    raise ValueError("GEMINI_API_KEY is required")
genai.configure(api_key=api_key)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("daily_digest.log", encoding='utf-8'),  # UTF-8 for file
        logging.StreamHandler(sys.stdout)  # Use stdout for console
    ]
)

# FCM Setup
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
FCM_PROJECT_ID = os.getenv("FCM_PROJECT_ID", "daily-agent-d042e")  # Your Firebase Project ID
FCM_SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
FCM_ENDPOINT = f"https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send"

def get_fcm_access_token():
    """Generate OAuth 2.0 access token for FCM V1 API."""
    if not SERVICE_ACCOUNT_JSON:
        logging.error("SERVICE_ACCOUNT_JSON not found in .env file")
        return None

    try:
        # Create a temporary file with the JSON content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(json.loads(SERVICE_ACCOUNT_JSON), temp_file)
            temp_file_path = temp_file.name

        credentials = service_account.Credentials.from_service_account_file(
            temp_file_path, scopes=FCM_SCOPES)
        credentials.refresh(Request())
        token = credentials.token

        # Clean up temporary file
        os.unlink(temp_file_path)
        return token
    except Exception as e:
        logging.error(f"Failed to get FCM access token: {str(e)}")
        return None

# Topics
TECH_TOPICS = ["AI", "Flutter", "React Native", "SQL", "DevOps"]

# 🔔 Notification function
def send_notification(title: str, message: str, image_url: str = None) -> None:
    ist = pytz.timezone('Asia/Kolkata')
    ist_time = datetime.datetime.now(ist)
    print(f"\n[{title} at {ist_time}]\n{message}\n")
    logging.info(f"Sent notification: {title} at {ist_time}")

    access_token = get_fcm_access_token()
    if not access_token:
        logging.error("Cannot send FCM notification: No access token")
        return

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        "message": {
            "topic": "all_users",
            "notification": {
                "title": title,
                "body": message
            },
            "android": {
                "notification": {
                    "channel_id": "high_importance_channel",
                    "priority": "high"
                }
            },
            "data": {
                "image": image_url or "",
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            }
        }
    }

    try:
        response = requests.post(FCM_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        logging.info(f"FCM notification sent: {response.json()}")
    except requests.RequestException as e:
        logging.error(f"Failed to send FCM notification: {str(e)}")

# 🧠 Learning content generator
def get_learning_content(topic: str) -> str:
    """Generate learning content for a topic using Gemini API."""
    if not topic or not isinstance(topic, str):
        logging.warning(f"Invalid topic: {topic}")
        return "Error: Topic must be a non-empty string."
    
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        prompt = f"Explain a useful concept or coding technique in {topic} with an example in 5-7 lines in hinglish."
        response = model.generate_content(prompt)
        content = response.text.strip() if response.text else ""
        if not content:
            logging.warning(f"Empty content received for {topic}")
            return f"Error: No content generated for {topic}"
        logging.info(f"Generated content for {topic}")
        return content
    except Exception as e:
        logging.error(f"Unexpected error for {topic}: {str(e)}")
        return f"Error: {str(e)}"

# 🌐 News fetcher
def get_news_update() -> str:
    """Fetch a 2-line summary of today's tech/AI news."""
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        prompt = "Give me a 2-line summary of today’s latest global tech or AI news in hinglish."
        response = model.generate_content(prompt)
        content = response.text.strip() if response.text else ""
        if not content:
            logging.warning("Empty news content received")
            return "Error: No news content generated"
        logging.info("Generated news update")
        return content
    except Exception as e:
        logging.error(f"Unexpected error for news: {str(e)}")
        return f"Error: {str(e)}"

# 😂 Meme fetcher
def get_meme_update() -> str:
    """Fetch a short programming meme or joke."""
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        prompt = "Share a short, funny programming meme or joke in 1-2 lines in hinglish."
        response = model.generate_content(prompt)
        content = response.text.strip() if response.text else ""
        if not content:
            logging.warning("Empty meme content received")
            return "Error: No meme content generated"
        logging.info("Generated meme update")
        return content
    except Exception as e:
        logging.error(f"Unexpected error for meme: {str(e)}")
        return f"Error: {str(e)}"

# 📚 First half tech tips
def send_tech_digest() -> None:
    """Send learning tips for the first two topics."""
    if not is_within_active_hours():
        logging.info("Tech digest skipped: Outside active hours")
        return
    for topic in TECH_TOPICS[:2]:
        content = get_learning_content(topic)
        send_notification(f"💻 Learn {topic}", content)

# 📚 Second half tech tips
def send_evening_tech_digest() -> None:
    """Send learning tips for the remaining topics."""
    if not is_within_active_hours():
        logging.info("Evening tech digest skipped: Outside active hours")
        return
    for topic in TECH_TOPICS[2:]:
        content = get_learning_content(topic)
        send_notification(f"💻 Learn {topic}", content)

# 🌍 News
def send_news() -> None:
    """Send a tech news update."""
    if not is_within_active_hours():
        logging.info("News update skipped: Outside active hours")
        return
    news = get_news_update()
    send_notification("🌐 Tech News Update", news)

# 🤣 Meme
def send_meme() -> None:
    """Send a programming meme or joke."""
    if not is_within_active_hours():
        logging.info("Meme update skipped: Outside active hours")
        return
    meme = get_meme_update()
    send_notification("😂 Programming Meme", meme)

# ⏰ Check active hours (11:30 AM to 11:30 PM IST)
def is_within_active_hours() -> bool:
    """Check if current time is within active hours (11:30 AM to 11:30 PM IST)."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).time()
    start = datetime_time(2, 00)  # 11:30 AM IST
    end = datetime_time(8, 30)    # 11:30 PM IST
    return start <= now <= end

# 🔄 Scheduler runner
def run_scheduler() -> None:
    """Run the scheduler to execute tasks at specified times in IST."""
    ist = pytz.timezone('Asia/Kolkata')
    
    # Schedule tasks in IST (converted to UTC for the scheduler)
    schedule.every().day.at("02:15").do(send_tech_digest)          # 11:30 AM IST
    schedule.every().day.at("02:16").do(send_news)                 # 1:00 PM IST
    schedule.every().day.at("02:16").do(send_evening_tech_digest)  # 5:00 PM IST
    schedule.every().day.at("02:16").do(send_meme)                 # 8:00 PM IST

    # Log current time for debugging
    ist_time = datetime.datetime.now(ist)
    utc_time = datetime.datetime.utcnow()
    logging.info(f"Current IST time: {ist_time}")
    logging.info(f"Current UTC time: {utc_time}")
    logging.info("Scheduler started. Waiting for tasks...")

    while True:
        try:
            pending_jobs = schedule.get_jobs()
            ist_time = datetime.datetime.now(ist)
            logging.info(f"Pending jobs at {ist_time}: {pending_jobs}")
            
            if is_within_active_hours():
                schedule.run_pending()
                logging.info(f"Checked for pending tasks at {ist_time}")
            else:
                logging.debug("Outside active hours (11:30 AM - 11:30 PM IST). Idle...")
            time_module.sleep(60)
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"Unexpected error in scheduler loop: {str(e)}")
            time_module.sleep(60)

# Handle graceful shutdown
def signal_handler(sig, frame) -> None:
    """Handle Ctrl+C or system exit gracefully."""
    logging.info("Shutting down scheduler...")
    sys.exit(0)

if __name__ == "__main__":
    # Set console encoding to UTF-8 for Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # Send an immediate test notification
    send_notification("Test Notification", "This is a test notification sent immediately.")

    signal.signal(signal.SIGINT, signal_handler)
    run_scheduler()