"""
Custom Indeed Scraper
Built to handle Indeed's structure with proper error handling
"""
import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IndeedScraper:
    """Custom scraper for Indeed job postings"""
    
    BASE_URL = "https://www.indeed.com"
    
    def __init__(self, delay: int = 2, max_retries: int = 3):
        self.delay = delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def search_jobs(
        self,
        query: str,
        location: str = "United States",
        results_wanted: int = 50
    ) -> List[Dict]:
        """
        Search for jobs on Indeed
        
        Args:
            query: Job search query (e.g., "data engineer")
            location: Location to search
            results_wanted: Number of results to fetch
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        start = 0
        
        while len(jobs) < results_wanted:
            try:
                search_url = f"{self.BASE_URL}/jobs"
                params = {
                    'q': query,
                    'l': location,
                    'start': start,
                    'filter': 0  # No duplicate filtering
                }
                
                response = self.session.get(search_url, params=params, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.find_all('div', class_='job_seen_beacon')
                
                if not job_cards:
                    logger.info(f"No more jobs found at start={start}")
                    break
                
                for card in job_cards:
                    if len(jobs) >= results_wanted:
                        break
                    
                    job_data = self._extract_job_data(card)
                    if job_data:
                        jobs.append(job_data)
                
                start += 10
                time.sleep(self.delay + random.uniform(0, 1))
                
            except Exception as e:
                logger.error(f"Error scraping Indeed: {str(e)}")
                break
        
        logger.info(f"Scraped {len(jobs)} jobs from Indeed for '{query}' in {location}")
        return jobs
    
    def _extract_job_data(self, card) -> Optional[Dict]:
        """Extract job data from a job card"""
        try:
            # Job ID
            job_id = card.get('data-jk', '')
            if not job_id:
                return None
            
            # Title
            title_elem = card.find('h2', class_='jobTitle')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Company
            company_elem = card.find('span', {'data-testid': 'company-name'})
            company_name = company_elem.get_text(strip=True) if company_elem else ''
            
            # Location
            location_elem = card.find('div', {'data-testid': 'text-location'})
            location = location_elem.get_text(strip=True) if location_elem else ''
            
            # Salary
            salary_elem = card.find('div', class_='salary-snippet')
            salary_range = salary_elem.get_text(strip=True) if salary_elem else None
            
            # Description snippet
            description_elem = card.find('div', class_='job-snippet')
            description = description_elem.get_text(strip=True) if description_elem else ''
            
            # Job type
            job_type_elem = card.find('div', {'data-testid': 'attribute_snippet_testid'})
            job_type = job_type_elem.get_text(strip=True) if job_type_elem else None
            
            # Posted date
            date_elem = card.find('span', class_='date')
            posted_date = self._parse_posted_date(date_elem.get_text(strip=True) if date_elem else '')
            
            # URL
            url = f"{self.BASE_URL}/viewjob?jk={job_id}"
            
            return {
                'job_id': job_id,
                'title': title,
                'company_name': company_name,
                'location': location,
                'description': description,
                'posted_date': posted_date,
                'salary_range': salary_range,
                'job_type': job_type,
                'source': 'indeed',
                'url': url,
            }
            
        except Exception as e:
            logger.warning(f"Error extracting job data: {str(e)}")
            return None
    
    def _parse_posted_date(self, date_str: str) -> datetime:
        """Parse relative date strings like 'Posted 2 days ago'"""
        try:
            if 'today' in date_str.lower() or 'just posted' in date_str.lower():
                return datetime.now()
            elif 'day' in date_str:
                days = int(''.join(filter(str.isdigit, date_str)) or 1)
                return datetime.now() - timedelta(days=days)
            else:
                return datetime.now()
        except:
            return datetime.now()
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """Fetch full job details by job ID"""
        try:
            url = f"{self.BASE_URL}/viewjob?jk={job_id}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Full description
            desc_elem = soup.find('div', id='jobDescriptionText')
            full_description = desc_elem.get_text(strip=True) if desc_elem else ''
            
            return {
                'job_id': job_id,
                'full_description': full_description,
            }
            
        except Exception as e:
            logger.error(f"Error fetching job details for {job_id}: {str(e)}")
            return None


if __name__ == "__main__":
    # Test the scraper
    scraper = IndeedScraper()
    jobs = scraper.search_jobs("data engineer", "Remote", results_wanted=10)
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:3]:
        print(f"- {job['title']} at {job['company_name']}")
