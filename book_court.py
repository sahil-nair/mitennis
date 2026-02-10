import os
import time
import datetime
import logging
import re
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# --- CONFIGURATION ---
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

def get_target_date_day():
    """
    Returns just the day number (e.g., "12") for the target date.
    Logic: If it's Mon night (Feb 9), target is Wed (Feb 11).
    Wait... your generated code clicked '12'.
    Let's stick to the 'Midnight + 2 days' rule.
    """
    now = datetime.datetime.now()
    # If running late night (e.g. 10PM), 'midnight' is tomorrow's date
    if now.hour > 12: 
        midnight_date = now.date() + datetime.timedelta(days=1)
    else:
        midnight_date = now.date()
        
    target_date = midnight_date + datetime.timedelta(days=2)
    # Return just the day number as a string (e.g., "12" or "05" -> "5")
    return str(int(target_date.strftime("%d")))

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
            logging.info("--- STARTING BOT (GENERATED CODE VERSION) ---")
            
            # 1. LOGIN
            logging.info("Logging in...")
            page.goto("https://mit.clubautomation.com/")
            
            # Using your specific test_id selectors
            page.get_by_test_id("loginAccountUsername").click()
            page.get_by_test_id("loginAccountUsername").fill(USERNAME)
            page.get_by_test_id("loginAccountPassword").click()
            page.get_by_test_id("loginAccountPassword").fill(PASSWORD)
            page.get_by_test_id("loginFormSubmitButton").click()
            
            page.wait_for_load_state("networkidle")

            # 2. NAVIGATE TO RESERVATIONS
            logging.info("Navigating to Reservations...")
            # Your code used clicking links. We can trust that or go direct.
            # Going direct is usually safer, but let's follow your flow to be sure.
            page.get_by_role("link", name="Reservations").click()
            
            # 3. SELECT SERVICE: TENNIS
            logging.info("Selecting Tennis...")
            # Click the dropdown container (currently shows "Swimming" or default)
            # The filter(has_text="Swimming") might be risky if it defaults to something else.
            # Better to target the ID directly if possible, but let's use the 'chosen' ID from line 9
            
            # Click the dropdown arrow/container
            page.locator("#component_chosen a").first.click() 
            # Click "Tennis" in the dropdown list
            page.locator("#component_chosen").get_by_text("Tennis").click()
            
            # 4. SELECT LOCATION: BUBBLE
            logging.info("Selecting Bubble...")
            time.sleep(1) # Wait for previous dropdown to trigger update
            page.locator("#location_chosen a").first.click()
            page.locator("#location_chosen").get_by_text("Bubble").click()

            # 5. SELECT DATE
            target_day = get_target_date_day()
            logging.info(f"Selecting Date: Day {target_day}")
            
            # Open the calendar (Your code had a regex click, likely the calendar icon)
            # page.get_by_role("link").filter(has_text=re.compile(r"^$")).click() 
            # Use a more robust selector for the calendar icon if that regex fails
            page.locator(".ui-datepicker-trigger").click() # Standard jQuery UI calendar trigger
            
            # Click the day number
            page.get_by_role("link", name=target_day, exact=True).first.click()
            time.sleep(1) # Allow date to set

            # 6. SELECT TIME: 4:00 PM
            logging.info("Selecting Time: 4:00 PM...")
            
            # Click the "From" dropdown container
            # Your code: page.locator("a").filter(has_text=":00 PM").click()
            # Safer: Target the ID container
            page.locator("#timeFrom_chosen a").first.click()
            
            # Click "04:00 PM"
            page.locator("#timeFrom_chosen").get_by_text("04:00 PM").click()

            # 7. SLEEP UNTIL MIDNIGHT
            wait_until_snipe_time()

            # 8. THE SNIPER TRIGGER
            while True:
                now = datetime.datetime.now()
                if (now.hour == 23 and now.minute == 59 and now.second >= 58) or (now.hour == 0 and now.minute == 0):
                    logging.info("MIDNIGHT HIT! Clicking Search...")
                    page.get_by_role("button", name="Search").click()
                    break
                time.sleep(0.1)

            # 9. BOOKING
            logging.info("Scanning for 'Select' buttons...")
            
            # Wait for results
            try:
                # We need to find a "Select" or "Book" link.
                # Your code had: page.get_by_role("link", name="[placeholder for time]").click()
                # This implies the results are Links, not Buttons.
                
                # Strategy: Grab the FIRST available "Select" link
                # We verify it's a booking link by checking its class or text
                # Usually text is "Select"
                
                # Wait for at least one result
                select_button = page.wait_for_selector('a:has-text("Select"), button:has-text("Select")', timeout=5000)
                
                if select_button:
                    logging.info("Found a slot! Clicking Select...")
                    select_button.click()
                    
                    # 10. CONFIRM
                    logging.info("Confirming...")
                    page.get_by_role("button", name="Confirm").click()
                    
                    # 11. FINAL OK
                    page.wait_for_selector('button:has-text("Ok")', timeout=5000)
                    page.get_by_role("button", name="Ok").click()
                    
                    logging.info("SUCCESS! Screenshotting...")
                    page.screenshot(path="success.png")
                else:
                    logging.error("No booking buttons found.")
                    page.screenshot(path="no_results.png")
                    
            except Exception as e:
                logging.error(f"Error during booking: {e}")
                page.screenshot(path="booking_error.png")

        except Exception as e:
            logging.error(f"CRITICAL FAILURE: {e}")
            page.screenshot(path="crash.png")
        
        finally:
            browser.close()

if __name__ == "__main__":
    run()
