import os
import time
import datetime
import logging
import random
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# --- CONFIGURATION ---
TARGET_DAY_OFFSET = 2  # 2 days ahead (Monday night -> Wednesday booking)
PREFERRED_START_HOUR = 14  # 2 PM
PREFERRED_END_HOUR = 18    # 6 PM
LOG_FILE = "booking_log.txt"
# ---------------------

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

load_dotenv()
USERNAME = os.getenv("MIT_USER")
PASSWORD = os.getenv("MIT_PASS")

def get_target_date_str():
    """Returns the target date string in MM/DD/YYYY format."""
    # If run on Monday night (before midnight), target is Wednesday.
    # If run on Tuesday morning (after midnight), target is Wednesday.
    # We base it on 'today's' date.
    target_date = datetime.date.today() + datetime.timedelta(days=TARGET_DAY_OFFSET)
    return target_date.strftime("%m/%d/%Y")

def wait_until_snipe_time():
    """Sleeps the script until 11:59:00 PM to save resources."""
    now = datetime.datetime.now()
    
    # Calculate target time: Tonight at 23:59:00
    target_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
    
    # If it's already past 11:59 PM (e.g. 00:00:00), we are ready to go immediately.
    if now > target_time:
        logging.info("It is already past 11:59 PM. Starting sniper mode immediately.")
        return

    wait_seconds = (target_time - now).total_seconds()
    logging.info(f"Sleeping for {wait_seconds:.2f} seconds until 11:59 PM...")
    time.sleep(wait_seconds)
    logging.info("Waking up! Preparing for midnight trigger.")

def run():
    with sync_playwright() as p:
        # HEADLESS=TRUE is critical for background execution while you sleep
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
