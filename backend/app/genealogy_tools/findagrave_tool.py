import httpx
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry # Ensure these are installed: pip install ratelimit
from loguru import logger
import urllib.parse
import time # For citation date
from typing import List, Dict, Any, Optional

from app.genealogy_tools.base_tool import GenealogyTool
from app.db.models import Person

class FindAGraveTool(GenealogyTool):
    """
    A tool to search FindAGrave.com via web scraping.
    Note: Web scraping is brittle and subject to website changes.
    An official API, if available, is always preferred.
    """

    @property
    def name(self) -> str:
        return "FindAGrave.com"

    @sleep_and_retry # Apply on the outer method that makes network calls
    @limits(calls=1, period=5) # Limit to 1 call every 5 seconds to be polite to FindAGrave
    async def _make_request(self, url: str, params: Optional[Dict[str, str]] = None) -> httpx.Response | None:
        """Helper function to make an HTTP GET request with error handling and user agent."""
        headers = { # Mimic a common browser to reduce likelihood of being blocked
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        }
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
            try:
                logger.debug(f"[{self.name}] Requesting URL: {url} with params: {params}")
                response = await client.get(url, params=params)
                response.raise_for_status() # Will raise an exception for 4XX/5XX status
                return response
            except httpx.HTTPStatusError as e:
                logger.error(f"[{self.name}] HTTP error: {e.response.status_code} while requesting {e.request.url}")
            except httpx.RequestError as e: # Covers ConnectError, Timeout, etc.
                logger.error(f"[{self.name}] Request error for {e.request.url}: {e}")
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error during HTTP request to {url}: {e}", exc_info=True)
        return None

    async def search_person(self, person: Person) -> List[Dict[str, Any]]:
        logger.info(f"[{self.name}] Starting search for Person ID {person.id}: {person.first_name} {person.last_name}")
        findings: List[Dict[str, Any]] = []

        # Prepare search parameters based on available person data
        first_name = person.first_name if person.first_name else ""
        last_name = person.last_name if person.last_name else ""

        # Attempt to extract year for FindAGrave's year-specific search fields
        birth_year_str = ""
        if person.birth_date:
            parts = person.birth_date.replace(',', ' ').split() # Handle commas in dates
            for part in reversed(parts):
                if part.isdigit() and len(part) == 4:
                    birth_year_str = part
                    break

        death_year_str = ""
        if person.death_date:
            parts = person.death_date.replace(',', ' ').split()
            for part in reversed(parts):
                if part.isdigit() and len(part) == 4:
                    death_year_str = part
                    break

        # Construct search URL for FindAGrave
        search_params = {
            "firstname": first_name,
            "lastname": last_name,
            "birthyear": birth_year_str,
            "deathyear": death_year_str,
            "orderby": "best", # 'best' match, or 'date', 'cemname'
            "page": "1" # Start with the first page of results
        }
        # Remove empty params to make URL cleaner and potentially improve search accuracy
        search_params_cleaned = {k: v for k, v in search_params.items() if v}

        base_search_url = "https://www.findagrave.com/memorial/search"

        response = await self._make_request(base_search_url, params=search_params_cleaned)
        if not response:
            logger.warning(f"[{self.name}] No response from initial search for {first_name} {last_name}.")
            return findings

        soup = BeautifulSoup(response.content, 'html.parser')

        results_container = soup.find('div', class_='search-results') # This class is hypothetical
        if not results_container:
             results_container = soup.find('div', attrs={'id': 'memSearch'}) # Another hypothetical selector

        if results_container:
            memorial_links_tags = results_container.find_all(
                'a', 
                href=lambda href: href and "/memorial/" in href and not href.endswith("/search")
            )

            logger.info(f"[{self.name}] Found {len(memorial_links_tags)} potential memorial links on search results page.")

            for link_tag in memorial_links_tags[:3]: # Process top N results to limit scope/requests
                memorial_url_path = link_tag.get('href')
                if not memorial_url_path:
                    continue

                memorial_url = "https://www.findagrave.com" + memorial_url_path
                logger.info(f"[{self.name}] Potential match found. URL: {memorial_url}")

                link_text = link_tag.get_text(strip=True, separator=' ')
                findings.append({
                   "data_field": "existence_on_findagrave",
                   "value": f"Potential FindAGrave record: '{link_text}'",
                   "source_url": memorial_url,
                   "citation": f"Find a Grave, database and images (https://www.findagrave.com : accessed {time.strftime('%d %B %Y')}), memorial page for a potential match of {person.first_name} {person.last_name}. URL: {memorial_url}",
                   "match_quality_notes": "This is a raw search result link. Full memorial page content was not scraped in this example. Further verification and detailed scraping needed."
                })
        else:
            logger.info(f"[{self.name}] No primary results container found on search page for {first_name} {last_name}.")

        if not findings:
            logger.info(f"[{self.name}] No direct memorial links extracted for {first_name} {last_name} from initial search page structure.")

        logger.info(f"[{self.name}] Concluding search for Person ID {person.id}. Returning {len(findings)} potential (placeholder) findings.")
        return findings
