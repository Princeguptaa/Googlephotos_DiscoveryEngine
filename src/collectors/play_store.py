from typing import List
import hashlib
from google_play_scraper import Sort, reviews

from src.collectors.base import BaseCollector
from src.classifier.schema import RawItem
from src.utils.logger import log


class PlayStoreCollector(BaseCollector):
    def collect(self, target_volume: int) -> List[RawItem]:
        package_id = "com.google.android.apps.photos"
        collected_items = []
        seen_hashes = set()

        for sort_order in [Sort.MOST_RELEVANT, Sort.NEWEST]:
            log("COLLECT", f"Fetching reviews with sort order: {sort_order}", "play_store")
            continuation_token = None
            
            while len(collected_items) < target_volume:
                # Fetch reviews
                result, continuation_token = reviews(
                    package_id,
                    lang='en',
                    country='us',
                    sort=sort_order,
                    count=100,
                    continuation_token=continuation_token
                )
                
                if not result:
                    break
                
                for r in result:
                    text = r.get("content")
                    if not text:
                        continue
                    
                    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                    if text_hash in seen_hashes:
                        continue
                        
                    seen_hashes.add(text_hash)
                    
                    item = RawItem(
                        source="play_store",
                        text=text,
                        date=r.get("at").strftime("%Y-%m-%d") if r.get("at") else None,
                        rating=float(r.get("score")) if r.get("score") else None,
                        url=None
                    )
                    collected_items.append(item)
                    
                    if len(collected_items) >= target_volume:
                        break
                
                if not continuation_token:
                    break

            if len(collected_items) >= target_volume:
                break
                
        log("COLLECT", f"Scraped {len(collected_items)} items", "play_store")
        return collected_items[:target_volume]
