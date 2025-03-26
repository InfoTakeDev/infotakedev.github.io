#!/usr/bin/env python3
import requests
import re
import time
import os
import sys
import fcntl # For file locking on Unix-like systems (macOS/Linux)
import logging

# --- Configuration ---
NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
HTML_FILE_PATH = "index.html"
# Placeholder in index.html to replace. IMPORTANT: Adjust this if needed!
HREF_PLACEHOLDER = "NGROK_HTTPS_URL_PLACEHOLDER"
CHECK_INTERVAL_SECONDS = 60 # Check every 60 seconds
LOCK_FILE_PATH = "update_ip.lock"
LOG_FILE_PATH = "update_ip.log"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler(sys.stdout) # Also print to console
    ]
)

# --- File Locking ---
class SingleInstance:
    def __init__(self, lock_file_path):
        self.lock_file_path = lock_file_path
        self.lock_file = None

    def __enter__(self):
        try:
            # Open the lock file in write mode. Creates if it doesn't exist.
            self.lock_file = open(self.lock_file_path, 'w')
            # Try to acquire an exclusive, non-blocking lock
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logging.info(f"Successfully acquired lock on {self.lock_file_path}")
            return self # Indicate success
        except (IOError, BlockingIOError):
            logging.error(f"Another instance is already running (lock file: {self.lock_file_path}). Exiting.")
            if self.lock_file:
                self.lock_file.close()
            sys.exit(1) # Exit if lock cannot be acquired
        except Exception as e:
            logging.error(f"Error acquiring lock: {e}")
            if self.lock_file:
                self.lock_file.close()
            sys.exit(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_file:
            # Release the lock and close the file
            fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
            # Optionally remove the lock file, though keeping it is fine
            # os.remove(self.lock_file_path)
            logging.info(f"Released lock on {self.lock_file_path}")

# --- Core Logic ---
def get_ngrok_https_url():
    """Fetches the public HTTPS URL from the ngrok agent API."""
    try:
        response = requests.get(NGROK_API_URL, timeout=5)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        # Find the first https tunnel
        for tunnel in data.get("tunnels", []):
            if tunnel.get("proto") == "https" and tunnel.get("public_url", "").startswith("https://"):
                return tunnel["public_url"]
        logging.warning("No HTTPS tunnel found in ngrok API response.")
        return None
    except requests.exceptions.ConnectionError:
        logging.error(f"Could not connect to ngrok API at {NGROK_API_URL}. Is ngrok running?")
        return None
    except requests.exceptions.Timeout:
        logging.error(f"Request to ngrok API timed out.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching ngrok URL: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching ngrok URL: {e}")
        return None

def update_html_file(new_url):
    """Reads index.html, replaces the placeholder href, and writes it back."""
    if not new_url:
        logging.warning("No new URL provided, skipping HTML update.")
        return False

    try:
        with open(HTML_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Use regex to find and replace the href attribute value
        # This regex looks for href="NGROK_HTTPS_URL_PLACEHOLDER"
        # It's specific to avoid replacing other hrefs. Adjust the placeholder if needed.
        pattern = re.compile(f'href="{re.escape(HREF_PLACEHOLDER)}"')
        
        if not pattern.search(content):
            logging.warning(f"Placeholder 'href=\"{HREF_PLACEHOLDER}\"' not found in {HTML_FILE_PATH}. No update made.")
            return False # Indicate placeholder not found

        # Check if the URL is already the current one
        current_url_pattern = re.compile(f'href="{re.escape(new_url)}"')
        if current_url_pattern.search(content):
            logging.info(f"URL '{new_url}' is already present in {HTML_FILE_PATH}. No update needed.")
            return False # Indicate no change needed

        new_content = pattern.sub(f'href="{new_url}"', content, count=1) # Replace only the first occurrence

        if new_content != content:
            with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logging.info(f"Successfully updated {HTML_FILE_PATH} with URL: {new_url}")
            return True # Indicate update occurred
        else:
            # This case should ideally not happen if pattern.search was true and current_url_pattern was false,
            # but included for completeness.
            logging.warning(f"Pattern found but replacement resulted in no change. Check regex and placeholder.")
            return False

    except FileNotFoundError:
        logging.error(f"HTML file not found: {HTML_FILE_PATH}")
        return False
    except Exception as e:
        logging.error(f"Error updating HTML file: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting ngrok IP updater script.")
    # Ensure only one instance runs using the lock file
    with SingleInstance(LOCK_FILE_PATH):
        logging.info("Script started successfully.")
        last_known_url = None
        while True:
            try:
                current_url = get_ngrok_https_url()

                if current_url:
                    if current_url != last_known_url:
                        logging.info(f"Detected ngrok HTTPS URL: {current_url}")
                        if update_html_file(current_url):
                            last_known_url = current_url # Update last known URL only if HTML was changed
                        else:
                            # If update failed or wasn't needed, check if placeholder exists
                            # If placeholder doesn't exist, maybe the URL is already correct?
                            # Re-read to confirm, or assume last_known_url if it exists
                            pass # Keep the old last_known_url
                    else:
                        logging.info(f"ngrok URL unchanged ({current_url}). Checking again in {CHECK_INTERVAL_SECONDS}s.")
                else:
                    # Handle case where ngrok might have stopped or URL couldn't be fetched
                    logging.warning("Could not retrieve ngrok URL. Will retry.")
                    # Consider if you want to revert the HTML or leave it as is
                    # last_known_url = None # Reset if you want to force update next time

                time.sleep(CHECK_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                logging.info("Script interrupted by user. Exiting.")
                break
            except Exception as e:
                logging.error(f"An error occurred in the main loop: {e}")
                # Avoid rapid looping on persistent errors
                time.sleep(CHECK_INTERVAL_SECONDS)

    logging.info("Script finished.")
