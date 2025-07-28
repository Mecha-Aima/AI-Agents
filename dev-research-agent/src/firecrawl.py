from firecrawl import FirecrawlApp, ScrapeOptions
from dotenv import load_dotenv
import os 
import time
import random

load_dotenv()

class FirecrawlService:
    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable not set")
        self.app = FirecrawlApp(api_key=api_key)
    
    def _handle_rate_limit(self, retry_count=0, max_retries=2):
        """Handle rate limiting with exponential backoff"""
        if retry_count >= max_retries:
            return False
        
        # Exponential backoff: 2^retry_count seconds + random jitter
        wait_time = (2 ** retry_count) + random.uniform(0, 1)
        print(f"⏳ Rate limit hit. Waiting {wait_time:.1f} seconds before retry {retry_count + 1}/{max_retries}...")
        time.sleep(wait_time)
        return True


    def search_companies(self, query: str, num_results: int = 3):
        for retry_count in range(3):  # Try up to 3 times
            try:
                result = self.app.search(
                    query=f"{query} company pricing",
                    limit=num_results,
                    scrape_options=ScrapeOptions(
                        format=["markdown"]
                    )
                )
                return result
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    print(f"⚠️ Rate limit exceeded (attempt {retry_count + 1}/3).")
                    if not self._handle_rate_limit(retry_count):
                        print("❌ Max retries reached. Please try again later.")
                        return type('SearchResult', (), {'data': []})()
                    continue  # Retry
                else:
                    print(f"❌ Exception occurred: {e}")
                    return type('SearchResult', (), {'data': []})()
        
        # If we get here, all retries failed
        return type('SearchResult', (), {'data': []})()


    def scrape_company_page(self, url: str):
        for retry_count in range(3):  # Try up to 3 times
            try:
                result = self.app.scrape_url(
                    url,
                    formats=["markdown"]
                ) 
                return result
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    print(f"⚠️ Rate limit exceeded while scraping {url} (attempt {retry_count + 1}/3).")
                    if not self._handle_rate_limit(retry_count):
                        print(f"❌ Max retries reached for {url}. Please try again later.")
                        return None
                    continue  # Retry
                else:
                    print(f"❌ Exception occurred while scraping {url}: {e}")
                    return None
        
        # If we get here, all retries failed
        return None 
            
        
