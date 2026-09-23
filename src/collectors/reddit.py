import os
import urllib.parse
from typing import List
from playwright.sync_api import sync_playwright

from src.collectors.base import BaseCollector
from src.classifier.schema import RawItem
from src.utils.logger import log, log_warning
from src.utils.io import load_config

class RedditCollector(BaseCollector):
    """Playwright-based collector for Reddit (using old.reddit.com for easier scraping)."""
    
    def collect(self, target_volume: int) -> List[RawItem]:
        log("COLLECT", f"Starting Reddit collection. Target: {target_volume}", "reddit")
        items = []
        
        config = load_config()
        reddit_config = config.get("collection", {}).get("reddit", {})
        subreddits = reddit_config.get("subreddits", ["googlephotos"])
        queries = reddit_config.get("search_queries", ["google photos search"])
        
        urls_to_visit = []
        for q in queries:
            q_enc = urllib.parse.quote(q)
            urls_to_visit.append(f"https://old.reddit.com/search/?q={q_enc}&sort=new")
            for sub in subreddits:
                urls_to_visit.append(f"https://old.reddit.com/r/{sub}/search/?q={q_enc}&restrict_sr=1&sort=new")
        
        auth_file = os.path.join(os.path.dirname(__file__), "..", "..", "reddit_auth.json")
        auth_file = os.path.abspath(auth_file)
        
        with sync_playwright() as p:
            if not os.path.exists(auth_file):
                log("COLLECT", "No reddit_auth.json found. Launching manual login window...", "reddit")
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
                page = context.new_page()
                page.goto("https://old.reddit.com/login")
                print("\n========================================================")
                print("ACTION REQUIRED: A browser window has opened.")
                print("Please log into Reddit. After you are logged in and see the homepage,")
                print("return to this terminal and press ENTER to continue.")
                print("========================================================\n")
                input()
                context.storage_state(path=auth_file)
                log("COLLECT", f"Saved authenticated session to {auth_file}", "reddit")
                browser.close()
                
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                storage_state=auth_file,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            post_links = []
            
            # Step 1: Collect post URLs
            for list_url in urls_to_visit:
                if len(post_links) >= target_volume:
                    break
                log("COLLECT", f"Navigating to {list_url}", "reddit")
                try:
                    page.goto(list_url, timeout=30000)
                    try:
                        page.wait_for_selector("a.search-title, a.title", timeout=10000)
                    except:
                        pass
                    
                    links = page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('a')).map(a => a.href).filter(href => href.includes('/comments/'));
                    }''')
                    
                    for link in links:
                        if link and link not in post_links:
                            post_links.append(link)
                            if len(post_links) >= target_volume:
                                break
                except Exception as e:
                    log_warning("COLLECT", f"Error loading {list_url}: {e}", "reddit")
                    continue
            
            # Step 2: Visit each post and extract data
            for url in post_links:
                if len(items) >= target_volume:
                    break
                try:
                    # ensure it's old.reddit.com
                    url = url.replace("www.reddit.com", "old.reddit.com")
                    page.wait_for_timeout(3000)  # Wait 3 seconds to avoid 429 Too Many Requests
                    page.goto(url, timeout=30000)
                    page.wait_for_selector(".sitetable", timeout=10000)
                    
                    # Extract title
                    title_el = page.locator("a.title").first
                    title = title_el.inner_text() if title_el.count() > 0 else ""
                    
                    # Extract body (original post body is typically the first .usertext-body inside .sitetable)
                    # But it might be missing if it's just a title post.
                    body_el = page.locator(".sitetable .usertext-body .md").first
                    body = body_el.inner_text() if body_el.count() > 0 else ""
                    
                    # Comments (first 5)
                    comments = []
                    comment_els = page.locator(".commentarea .comment .usertext-body .md").all()
                    for i in range(min(5, len(comment_els))):
                        try:
                            comments.append(comment_els[i].inner_text())
                        except:
                            continue
                            
                    full_text = f"Title: {title}\nBody: {body}\nComments: {' | '.join(comments)}"
                    
                    # Date from timestamp
                    ts_el = page.locator("time.live-timestamp").first
                    date_str = None
                    if ts_el.count() > 0:
                        dt = ts_el.get_attribute("datetime")
                        if dt:
                            # e.g. "2024-05-10T12:00:00+00:00" -> "2024-05-10"
                            date_str = dt[:10]
                            
                    items.append(RawItem(
                        source="reddit",
                        text=full_text,
                        date=date_str,
                        rating=None,
                        url=url
                    ))
                    log("COLLECT", f"Scraped reddit post: {title[:30]}...", "reddit")
                except Exception as e:
                    log_warning("COLLECT", f"Failed to scrape post {url}: {e}", "reddit")
                    
            browser.close()
            
        log("COLLECT", f"Scraped {len(items)} reddit items", "reddit")
        return items
