import os
from playwright.sync_api import sync_playwright

auth_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "reddit_auth.json"))

print("Launching browser...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    page = context.new_page()
    page.goto("https://old.reddit.com/login")
    
    print("\n========================================================")
    print("ACTION REQUIRED: A browser window should have opened on your screen.")
    print("Please log into Reddit in that window.")
    print("After you are logged in and see the homepage,")
    print("return to this terminal and press ENTER to continue.")
    print("========================================================\n")
    
    input()
    
    context.storage_state(path=auth_file)
    print(f"Success! Saved authenticated session to {auth_file}")
    browser.close()
