"""
JobSpy Fallback Scraper
Uses the python-jobspy library as a backup scraping method
"""
from jobspy import scrape_jobs
import logging
from typing import List, Dict
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobSpyScraper:
    """Wrapper for JobSpy library to scrape multiple job sites"""
    
    def __init__(self):
        self.supported_sites = ['indeed', 'linkedin', 'glassdoor', 'google']
    
    def search_jobs(
        self,
        query: str,
        location: str = "United States",
        results_wanted: int = 50,
        site_name: List[str] = None
    ) -> List[Dict]:
        """
        Search for jobs using JobSpy library
        
        Args:
            query: Job search query
            location: Location to search
            results_wanted: Number of results per site
            site_name: List of sites to scrape (default: ['indeed', 'linkedin'])
            
        Returns:
            List of job dictionaries
        """
        if site_name is None:
            site_name = ['indeed', 'linkedin']
        
        try:
            logger.info(f"Scraping jobs for '{query}' in {location} from {site_name}")
            
            jobs_df = scrape_jobs(
                site_name=site_name,
                search_term=query,
                location=location,
                results_wanted=results_wanted,
                hours_old=72,  # Jobs posted in last 3 days
                country_indeed='USA',
                linkedin_fetch_description=True,
            )
            
            if jobs_df is None or jobs_df.empty:
                logger.warning("No jobs found")
                return []
            
            # Convert DataFrame to list of dicts
            jobs = self._standardize_jobs(jobs_df)
            
            logger.info(f"Found {len(jobs)} jobs using JobSpy")
            return jobs
            
        except Exception as e:
            logger.error(f"Error with JobSpy scraper: {str(e)}")
            return []
    
    def _standardize_jobs(self, df: pd.DataFrame) -> List[Dict]:
        """Standardize JobSpy output to match our schema"""
        jobs = []
        
        for _, row in df.iterrows():
            try:
                job = {
                    'job_id': self._generate_job_id(row),
                    'title': row.get('title', ''),
                    'company_name': row.get('company', ''),
                    'location': row.get('location', ''),
                    'description': row.get('description', ''),
                    'posted_date': row.get('date_posted'),
                    'salary_range': self._format_salary(row),
                    'job_type': row.get('job_type'),
                    'source': row.get('site', 'unknown'),
                    'url': row.get('job_url', ''),
                }
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Error standardizing job row: {str(e)}")
                continue
        
        return jobs
    
    def _generate_job_id(self, row) -> str:
        """Generate a unique job ID from row data"""
        # Use the URL or create a hash
        url = row.get('job_url', '')
        if url:
            # Extract ID from URL if possible
            parts = url.split('/')
            for part in parts:
                if part and len(part) > 10:
                    return part[:50]
        
        # Fallback: hash of title + company
        import hashlib
        unique_str = f"{row.get('title', '')}{row.get('company', '')}{row.get('location', '')}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def _format_salary(self, row) -> str:
        """Format salary information"""
        salary_parts = []
        
        if pd.notna(row.get('min_amount')):
            salary_parts.append(f"${row['min_amount']:,.0f}")
        
        if pd.notna(row.get('max_amount')):
            salary_parts.append(f"${row['max_amount']:,.0f}")
        
        if salary_parts:
            return " - ".join(salary_parts)
        
        return None


if __name__ == "__main__":
    # Test the scraper
    scraper = JobSpyScraper()
    jobs = scraper.search_jobs("machine learning engineer", "San Francisco", results_wanted=10)
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:3]:
        print(f"- {job['title']} at {job['company_name']} ({job['source']})")
