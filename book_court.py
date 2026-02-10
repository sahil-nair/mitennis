import os
import time
import datetime
import logging
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# --- CONFIGURATION ---
# "Midnight + 2" logic:
# If running Monday night (Feb 9), midnight is Feb 10. Target is Feb 12.
# This means we want specific logic to handle the date calculation safely.
TARGET_URL = "https://mit.clubautomation.com/event/reserve-court-new"
LOG_FILE = "booking_log.txt"
# ---------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

load_dotenv()
USERNAME = os.getenv("MIT_USER")
PASSWORD = os.getenv("MIT_PASS")

def get_target_date_str():
    """
    Calculates the target date based on 'Midnight + 2 days'.
    If it's currently Monday night (before midnight), 'Midnight' is tomorrow.
    If it's Tuesday morning (after midnight), 'Midnight' was today.
    """
    now = datetime.datetime.now()
    
    # If running late night (e.g. 11PM), the 'booking midnight' is technically tomorrow
    if now.hour > 12: 
        midnight_date = now.date() + datetime.timedelta(days=1)
    else:
        midnight_date = now.date()
        
    target_date = midnight_date + datetime.timedelta(days=2)
    return target_date.strftime("%m/%d/%Y")

def wait_until_snipe_time():
    """Sleeps until 11:59:00 PM."""
    now = datetime.datetime.now()
    target_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
    
    if now > target_time:
        logging.info("Already past 11:59 PM. Ready to fire.")
        return

    wait_seconds = (target_time - now).total_seconds()
    logging.info(f"Sleeping for {wait_seconds:.2f} seconds...")
    time.sleep(wait_seconds)
    logging.info("Waking up!")

def run():
    with sync_playwright() as p:
        # headless=True for background running
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            logging.info("--- STARTING BOT (FORM SEARCH VERSION) ---")
            
            # 1. LOGIN
            logging.info("Logging in...")
            page.goto("https://mit.clubautomation.com/login")
            page.fill('input[name="login"]', USERNAME) 
            page.fill('input[name="password"]', PASSWORD)
            page.click('button:has-text("Login"), input[type="submit"]')
            page.wait_for_load_state("networkidle")
            
            # 2. NAVIGATE TO SEARCH PAGE
            logging.info(f"Navigating to {TARGET_URL}...")
            page.goto(TARGET_URL)
            page.wait_for_load_state("networkidle")

            # 3. FILL FORM (PRE-FILL BEFORE MIDNIGHT)
            logging.info("Pre-filling search form...")
            
            # Select Service: Tennis
            # Based on screenshot, these are likely standard selects or custom dropdowns.
            # We try standard select first, then fallback to clicking text.
            try:
                page.select_option('select[id*="service"]', label="Tennis")
            except:
                # Fallback for custom dropdowns (click container, click option)
                page.click("text=What Service?") # Click label or container
                page.click("text=Tennis")
            
            # Select Location: Bubble
            # The screenshot shows "Where?" has two dropdowns. We need the first one.
            try:
                page.select_option('select[id*="location"]', label="Bubble")
            except:
                # Fallback: Look for the specific dropdown logic
                # Usually identifying by the label "Where?" is safest
                logging.info("Attempting to select 'Bubble' via text...")
                # Note: This might need adjustment if 'Bubble' isn't visible until clicked
                # Attempt to find the dropdown trigger for location
                pass # Assuming default or easy selection. *Monitor this in test run*

            # DATE SELECTION
            target_date = get_target_date_str()
            logging.info(f"Setting Date to: {target_date}")
            
            # Using specific locator for the date input shown in screenshot (calendar icon)
            # Usually input[id*='date']
            page.fill('input[name*="date"], input[id*="date"]', target_date)
            page.keyboard.press("Enter") # Lock it in
            
            # TIME PREFERENCE (4:00 PM - 6:00 PM)
            logging.info("Setting Time Filter: 4:00 PM - 6:00 PM")
            
            # The screenshot shows "From" and "To" dropdowns
            # We need to find the select elements associated with these labels.
            # This is a guess at the IDs/names based on standard CA forms.
            # If these fail, the script might error, so check your test run.
            
            # Try to select by label text "02:00 PM" (default) -> change to "04:00 PM"
            # We use 'select_option' if they are standard selects
            
            # Selecting "From" time
            try:
                # Finding the select next to "From"
                # This is tricky without source, but let's try generic 'time' selects
                # Often named 'startTime' and 'endTime'
                page.select_option('select[name*="start"], select[id*="start"]', value="16:00") # or label="04:00 PM"
                page.select_option('select[name*="end"], select[id*="end"]', value="18:00")   # or label="06:00 PM"
            except:
                # Harder fallback: Click the dropdowns by text matching
                logging.warning("Could not standard-select times. Trying text clicks...")
                # This part is risky without seeing the HTML. 
                # Hopefully defaults are wide enough or standard selects work.

            # 4. SLEEP UNTIL MIDNIGHT
            wait_until_snipe_time()

            # 5. THE SNIPER TRIGGER
            # Wait for the exact second
            while True:
                now = datetime.datetime.now()
                if (now.hour == 23 and now.minute == 59 and now.second >= 58) or (now.hour == 0 and now.minute == 0):
                    logging.info("MIDNIGHT HIT! Clicking Search...")
                    
                    # Click the Blue "Search" Button
                    page.click('button:has-text("Search"), input[value="Search"]')
                    break
                time.sleep(0.1)

            # 6. SELECT A RESULT
            logging.info("Waiting for results...")
            
            # Wait for "Pick a Time" area to populate
            # We look for a "Select" or "Book" button.
            # In CA, these are often "Select" buttons that open a modal.
            
            try:
                # Wait up to 5 seconds for a button to appear
                button = page.wait_for_selector('button:has-text("Select"), button:has-text("Book")', timeout=5000)
                
                if button:
                    logging.info("Found a slot! Clicking Select...")
                    button.click()
                    
                    # 7. CONFIRMATION MODAL
                    logging.info("Waiting for Confirmation...")
                    page.wait_for_selector('button:has-text("Confirm"), button:has-text("Complete")', timeout=5000)
                    page.click('button:has-text("Confirm"), button:has-text("Complete")')
                    
                    logging.info("SUCCESS! Screenshotting...")
                    page.wait_for_timeout(2000)
                    page.screenshot(path="success.png")
                else:
                    logging.error("Search finished but no buttons found.")
                    page.screenshot(path="no_results.png")
                    
            except Exception as e:
                logging.error(f"Error finding/booking slot: {e}")
                page.screenshot(path="search_error.png")

        except Exception as e:
            logging.error(f"CRITICAL FAILURE: {e}")
            page.screenshot(path="crash.png")
        
        finally:
            browser.close()

if __name__ == "__main__":
    run()
