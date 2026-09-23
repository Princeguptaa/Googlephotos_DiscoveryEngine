import hashlib
from typing import List

from app_store_scraper import AppStore
from src.collectors.base import BaseCollector
from src.classifier.schema import RawItem
from src.utils.logger import log, log_warning


class AppStoreCollector(BaseCollector):
    COUNTRIES = ["us", "gb", "in", "au", "ca"]
    APP_ID = "962194608"
    APP_NAME = "google-photos"

    def collect(self, target_volume: int) -> List[RawItem]:
        items = []
        seen_hashes = set()
        
        for country in self.COUNTRIES:
            if len(items) >= target_volume:
                break
                
            log("COLLECT", f"Fetching App Store reviews for country: {country}", "app_store")
            try:
                app = AppStore(country=country, app_name=self.APP_NAME, app_id=self.APP_ID)
                # fetch slightly more to account for duplicates/short reviews
                app.review(how_many=target_volume - len(items))
                
                for review in app.reviews:
                    content = review.get("review")
                    if not content:
                        continue
                        
                    author = review.get("userName", "unknown")
                    hash_key = hashlib.sha256(f"{author}:{content}".encode('utf-8')).hexdigest()
                    if hash_key in seen_hashes:
                        continue
                        
                    seen_hashes.add(hash_key)
                    
                    rating = review.get("rating")
                    date_val = review.get("date")
                    date_str = date_val.strftime("%Y-%m-%d") if date_val else None
                    
                    item = RawItem(
                        source="app_store",
                        text=content,
                        date=date_str,
                        rating=float(rating) if rating else None,
                        url=None
                    )
                    items.append(item)
                    
                    if len(items) >= target_volume:
                        break
                        
            except Exception as e:
                log_warning("COLLECT", f"Error fetching for {country}: {e}", "app_store")
                
        log("COLLECT", f"Scraped {len(items)} items", "app_store")
        return items
