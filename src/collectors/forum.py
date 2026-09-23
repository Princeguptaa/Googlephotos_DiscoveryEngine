import os
from typing import List
from playwright.sync_api import sync_playwright

from src.collectors.base import BaseCollector
from src.classifier.schema import RawItem
from src.utils.logger import log, log_warning
from src.utils.io import load_config

class ForumCollector(BaseCollector):
    """Playwright-based collector for Google Photos Community Forum."""
    
    def collect(self, target_volume: int) -> List[RawItem]:
        log("COLLECT", f"Starting Forum collection. Target: {target_volume}", "forum")
        items = []
        
        config = load_config()
        forum_config = config.get("collection", {}).get("forum", {})
        base_url = forum_config.get("base_url", "https://support.google.com/photos/community")
        queries = forum_config.get("search_queries", ["google photos search"])
        
        import urllib.parse
        urls_to_visit = []
        for q in queries:
            q_enc = urllib.parse.quote(q)
            urls_to_visit.append(f"https://support.google.com/photos/search?q={q_enc}")
            
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            page = context.new_page()
            
            thread_links = []
            
            # Step 1: Collect thread URLs
            for list_url in urls_to_visit:
                if len(thread_links) >= target_volume:
                    break
                    
                log("COLLECT", f"Navigating to {list_url}", "forum")
                try:
                    page.goto(list_url, timeout=30000)
                    page.wait_for_timeout(5000) # give page time to load dynamic content
                    
                    # get all links that look like thread links
                    links = page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('a')).map(a => a.href).filter(href => href.includes('/thread/'));
                    }''')
                    
                    for link in links:
                        if link and link not in thread_links:
                            thread_links.append(link)
                            if len(thread_links) >= target_volume:
                                break
                except Exception as e:
                    log_warning("COLLECT", f"Error loading {list_url}: {e}", "forum")
                
            # Step 2: Visit each thread and extract data
            for url in thread_links:
                if len(items) >= target_volume:
                    break
                try:
                    page.goto(url, timeout=30000)
                    page.wait_for_timeout(3000) # give page time to load dynamic content
                    
                    # title
                    title = page.evaluate("() => document.title")
                    
                    # body
                    body = page.evaluate('''() => {
                        const contentNode = document.querySelector("[class*='Questioncardcontent']");
                        return contentNode ? contentNode.innerText.substring(0, 5000) : "";
                    }''')
                        
                    full_text = f"Title: {title}\nBody: {body}"
                    
                    items.append(RawItem(
                        source="forum",
                        text=full_text,
                        date=None,
                        rating=None,
                        url=url
                    ))
                    log("COLLECT", f"Scraped forum thread: {title[:30]}...", "forum")
                except Exception as e:
                    log_warning("COLLECT", f"Failed to scrape thread {url}: {e}", "forum")
                    
            browser.close()
            
        log("COLLECT", f"Scraped {len(items)} forum items", "forum")
        return items
