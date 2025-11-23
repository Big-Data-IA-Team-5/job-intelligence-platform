"""
Scraper Orchestrator
Coordinates multiple scrapers and handles fallback logic
"""
import logging
from typing import List, Dict
from scrapers.custom_indeed_scraper import IndeedScraper
from scrapers.jobspy_fallback import JobSpyScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """Orchestrates multiple job scrapers with fallback logic"""
    
    def __init__(self):
        self.indeed_scraper = IndeedScraper()
        self.jobspy_scraper = JobSpyScraper()
    
    def scrape_jobs(
        self,
        query: str,
        location: str = "United States",
        results_wanted: int = 50,
        use_fallback: bool = True
    ) -> List[Dict]:
        """
        Scrape jobs with primary scraper and fallback if needed
        
        Args:
            query: Job search query
            location: Location to search
            results_wanted: Number of results wanted
            use_fallback: Whether to use fallback scraper if primary fails
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Try primary scraper (Indeed custom)
        try:
            logger.info(f"Attempting primary scraper for '{query}'")
            jobs = self.indeed_scraper.search_jobs(query, location, results_wanted)
        except Exception as e:
            logger.error(f"Primary scraper failed: {str(e)}")
        
        # Use fallback if primary didn't get enough results
        if use_fallback and len(jobs) < results_wanted * 0.5:
            logger.info("Using fallback scraper (JobSpy)")
            try:
                fallback_jobs = self.jobspy_scraper.search_jobs(
                    query, location, results_wanted - len(jobs)
                )
                jobs.extend(fallback_jobs)
            except Exception as e:
                logger.error(f"Fallback scraper failed: {str(e)}")
        
        # Deduplicate jobs
        jobs = self._deduplicate_jobs(jobs)
        
        logger.info(f"Total unique jobs collected: {len(jobs)}")
        return jobs
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on job_id"""
        seen_ids = set()
        unique_jobs = []
        
        for job in jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs


def run_scraping_pipeline(
    search_terms: List[str],
    locations: List[str],
    results_per_search: int = 50
) -> List[Dict]:
    """
    Run full scraping pipeline for multiple search terms and locations
    
    Args:
        search_terms: List of job titles/queries to search
        locations: List of locations to search
        results_per_search: Results wanted per search combination
        
    Returns:
        Combined list of all scraped jobs
    """
    orchestrator = ScraperOrchestrator()
    all_jobs = []
    
    for term in search_terms:
        for location in locations:
            logger.info(f"Scraping: {term} in {location}")
            jobs = orchestrator.scrape_jobs(term, location, results_per_search)
            all_jobs.extend(jobs)
    
    # Final deduplication
    all_jobs = orchestrator._deduplicate_jobs(all_jobs)
    
    logger.info(f"Pipeline complete. Total unique jobs: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    # Test the orchestrator
    search_terms = ["data engineer", "software engineer"]
    locations = ["Remote"]
    
    jobs = run_scraping_pipeline(search_terms, locations, results_per_search=10)
    
    print(f"\nCollected {len(jobs)} unique jobs")
    print("\nSample jobs:")
    for job in jobs[:5]:
        print(f"- {job['title']} at {job['company_name']} ({job['source']})")
