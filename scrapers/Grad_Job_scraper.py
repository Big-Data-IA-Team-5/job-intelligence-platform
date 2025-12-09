
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    InvalidSessionIdException, 
    WebDriverException,
    TimeoutException,
    NoSuchElementException
)
import time
import json
import csv
import os
from datetime import datetime, timedelta
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class AirtableJobScraper:
    def __init__(self, hours_lookback=168, max_retries=3, num_workers=3):
        """
        Initialize scraper with configurable lookback window
        Args:
            hours_lookback: Number of hours to look back for jobs (default: 168 = 7 days)
            max_retries: Maximum retries for failed categories (default: 3)
            num_workers: Number of parallel workers (default: 3)
        """
        self.num_workers = num_workers
        self.lock = threading.Lock()
        self.categories = {
            'Software_Engineering': 'https://airtable.com/appjDG7vmPOm1pO7S/shr763VHjlzPBDCgN/tblLP4AtskrLA8Aw1?viewControls=on',
            'Data_Analyst': 'https://airtable.com/appZ5SmkwkcW7Xd8C/shr51y9s2uIRlkvI8/tblnD3h2G6iiA0Csr?viewControls=on',
            'Marketing': 'https://airtable.com/appcUz4GkJoWzTX3C/shrlp6fQzQ5mD68nC/tbldH61sRyLEQ6xSa?viewControls=on',
            'Machine_Learning_AI': 'https://airtable.com/appoxNzAIRReFCzZV/shrmDBF1vNPtzNjzl/tbldeT1mbQGFwtwpa?viewControls=on',
            'Business_Analyst': 'https://airtable.com/appK8wuhdzqC2KtWr/shrlXw5IPUECgZH9Q/tbljDinzQ1c29E24C?viewControls=on',
            'Product_Management': 'https://airtable.com/appYvVTjJYHpq712D/shrpI5GFPocw2qcre/tblPKs03ZmPmgXeZU?viewControls=on',
            'Creatives_Design': 'https://airtable.com/app7O2uKT9GTvMx9J/shrWEq2l15qeODGG3/tbllfcKFR3K5dDXmE?viewControls=on',
            'Accounting_Finance': 'https://airtable.com/app3hKGPjx4m3n8uy/shrxflLkiF1ljjPgZ/tblsoYj6mVDT4Fvoz?viewControls=on',
            'Consulting': 'https://airtable.com/appk3hzdIFG7MVEqq/shr7BAtGeCN125QYK/tblRSPZ04WqHbNgVl?viewControls=on',
            'Engineering_Development': 'https://airtable.com/appTmAS0zZwcwxhoo/shrZzO1d5s5qGPRgr/tblkOVG7BaimFY0C6?viewControls=on',
            'Human_Resources': 'https://airtable.com/appTYQlu4ffssFoAb/shrsYDrGPeDnGrxGV/tblsZIPj9cVSdTWtA?viewControls=on',
            'Arts_Entertainment': 'https://airtable.com/appxsdozleC9iaktr/shrtavKK7PhghGUt5/tblnkZfp7JMENSblI?viewControls=on',
            'Management_Executive': 'https://airtable.com/appFa3PBhYWICqdV9/shrkuNa5I9zuPNlA1/tblWMm3zBbFv0TIq5?viewControls=on',
            'Customer_Service_Support': 'https://airtable.com/appUymIq1nGtqN2XK/shrwfk23CnWMKnVGD/tblq0hLymPp8Jss3Q?viewControls=on',
            'Legal_Compliance': 'https://airtable.com/appFU12UKGbt1gs95/shrVVTUffhqFK98J1/tblLXNqHxMVp7QIcl?viewControls=on',
            'Sales': 'https://airtable.com/appoX5NsnYmJ3aeTd/shr1tIFqsoekDopXF/tblfENWXGILRBAAJF?viewControls=on',
            'Education_Training': 'https://airtable.com/appPYy0RX5fDsEhZm/shrYLlad4LNZEicQd/tblJgoMCG1GQVc3m3?viewControls=on',
            'Cyber_Security': 'https://airtable.com/app5K4hbJeNczKe80/shrmicWx3O72527KW/tbl0nEY7kMwmxBzVS?viewControls=on',
            'Project_Manager': 'https://airtable.com/app5K4hbJeNczKe80/shrmicWx3O72527KW/tbl0nEY7kMwmxBzVS?viewControls=on',
            'Data_Engineer': 'https://airtable.com/appqYfRGKpLQ8UsdH/shrFnvW20reJCEkYZ/tblDVfWJzDdU8KsoY?viewControls=on',
            'Health_Care': 'https://airtable.com/appqXoZFUXnMz1QZH/shr8D4joJaLDSnum1/tblDzOjYZXCT5Pqtb?viewControls=on'
        }
        
        self.jobs = []
        self.all_jobs = []  # NEW: Store all jobs from all categories
        self.driver = None
        self.hours_lookback = hours_lookback
        self.max_retries = max_retries
        self.cutoff_date = datetime.now() - timedelta(hours=hours_lookback)
        self.current_category = None
        self.date_samples = []
        self.failed_categories = []
        self.empty_categories = []
        self.total_jobs_found = 0
        
    def setup_driver(self):
        """Setup Chrome driver with optimized settings"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2
        })
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.page_load_strategy = 'eager'
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("✓ Chrome driver initialized (headless) successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to initialize Chrome driver: {e}")
            return False
    
    def is_session_valid(self):
        """Check if the current session is still valid"""
        try:
            _ = self.driver.current_url
            return True
        except (InvalidSessionIdException, WebDriverException):
            return False
        except Exception:
            return False
    
    def restart_driver(self):
        """Restart the Chrome driver"""
        logger.warning("🔄 Restarting Chrome driver...")
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            time.sleep(3)
            return self.setup_driver()
        except Exception as e:
            logger.error(f"✗ Failed to restart driver: {e}")
            return False
    
    def parse_date(self, date_string):
        """Parse date string from Airtable to datetime object with extensive format support"""
        if not date_string or date_string in ['N/A', '', 'None', 'null', 'Apply']:
            return None
        
        date_string = date_string.strip()
        
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%b %d, %Y',
            '%B %d, %Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d %b %Y',
            '%d %B %Y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_string, fmt)
            except:
                continue
        
        try:
            date_part = date_string.split()[0]
            return datetime.strptime(date_part, '%Y-%m-%d')
        except:
            pass
        
        if 'ago' in date_string.lower():
            try:
                parts = date_string.lower().split()
                if 'day' in date_string.lower():
                    days = int(parts[0])
                    return datetime.now() - timedelta(days=days)
                elif 'hour' in date_string.lower():
                    hours = int(parts[0])
                    return datetime.now() - timedelta(hours=hours)
            except:
                pass
        
        if 'yesterday' in date_string.lower():
            return datetime.now() - timedelta(days=1)
        
        if 'today' in date_string.lower():
            return datetime.now()
        
        return None
    
    def is_within_timeframe(self, date_string):
        """Check if date is within the configured lookback window"""
        parsed_date = self.parse_date(date_string)
        
        if not parsed_date:
            if date_string not in ['N/A', '', 'None', 'Apply']:
                self.date_samples.append(('FAILED', date_string))
            return False
        
        self.date_samples.append(('SUCCESS', date_string, parsed_date))
        return parsed_date >= self.cutoff_date
    
    def is_likely_date(self, text):
        """Check if text looks like a date - IMPROVED WITH PATTERN MATCHING"""
        if not text or len(text) > 30 or len(text) < 8:
            return False
        
        # Exclude obvious non-dates
        if text.lower() in ['apply', 'remote', 'hybrid', 'on-site', 'onsite', 'on site']:
            return False
        
        # First, try to parse it - if it parses, it's definitely a date!
        if self.parse_date(text):
            return True
        
        # Check for common date patterns
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # 2025-11-25
            r'^\d{2}/\d{2}/\d{4}$',  # 11/25/2025
            r'^\d{2}-\d{2}-\d{4}$',  # 11-25-2025
            r'^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$',  # Nov 25, 2025
            r'^\d{1,2}/\d{1,2}/\d{4}$',  # 1/5/2025
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def is_likely_location(self, text):
        """Check if text looks like a location"""
        if not text or len(text) > 100:
            return False
        
        text_lower = text.lower()
        
        # Check for city, state patterns (e.g., "Houston, TX" or "New York, NY")
        import re
        if re.search(r',\s*[A-Z]{2}$', text):  # Ends with ", XX" (state abbreviation)
            return True
        
        # Location keywords
        location_keywords = [
            'remote', 'hybrid', 'on-site', 'onsite', 'in-person',
            'usa', 'us', 'united states', 'america',
            'ny', 'ca', 'tx', 'fl', 'il', 'pa', 'ma', 'wa', 'va', 'nc',
            'new york', 'california', 'texas', 'florida', 'seattle',
            'san francisco', 'boston', 'austin', 'chicago', 'atlanta',
            'denver', 'portland', 'phoenix', 'dallas', 'houston',
            'los angeles', 'washington dc', 'miami', 'philadelphia',
            ', usa', ', us', 'multi location', 'milwaukee', 'bronx',
            'orleans', 'windsor', 'renton', 'medicine', 'greeley',
            'toronto', 'montreal', 'ontario', 'quebec'
        ]
        
        return any(keyword in text_lower for keyword in location_keywords)
    
    def is_likely_salary(self, text):
        """Check if text looks like a salary"""
        if not text or len(text) > 50:
            return False
        
        text_lower = text.lower()
        
        # Salary indicators
        return ('$' in text or 
                'k' in text_lower or 
                '/yr' in text_lower or
                '/hr' in text_lower or
                any(word in text_lower for word in ['salary', 'compensation', 'pay', 'hourly', 'annual']))
    
    def is_likely_visa(self, text):
        """Check if text is about visa sponsorship"""
        if not text or len(text) > 50:
            return False
        
        text_lower = text.lower()
        
        visa_keywords = ['h1b', 'h-1b', 'visa', 'sponsorship', 'sponsor', 'work authorization']
        return any(keyword in text_lower for keyword in visa_keywords)
    
    def is_likely_company(self, text):
        """Check if text looks like a company name"""
        if not text or len(text) > 100 or len(text) < 2:
            return False
        
        # Exclude locations (city, state pattern)
        import re
        if re.search(r',\s*[A-Z]{2}$', text):  # Ends with ", XX" (state abbreviation)
            return False
        
        # Exclude common non-company words
        exclude = ['apply', 'remote', 'hybrid', 'on-site', 'onsite', 'on site']
        if text.lower() in exclude:
            return False
        
        if text[0].isupper():
            special_char_count = sum(1 for c in text if c in '!@#$%^&*()_+=[]{}|;:,.<>?/')
            if special_char_count < 3:
                return True
        
        return False
    
    def is_likely_title(self, text):
        """Check if text looks like a job title"""
        if not text or len(text) < 5 or len(text) > 150:
            return False
        
        text_lower = text.lower()
        
        title_keywords = [
            'engineer', 'developer', 'analyst', 'manager', 'specialist',
            'coordinator', 'associate', 'senior', 'junior', 'lead', 'principal',
            'director', 'intern', 'graduate', 'entry', 'software', 'data',
            'product', 'project', 'business', 'technical', 'support', 'scientist',
            'technician', 'administrator', 'consultant', 'designer', 'architect'
        ]
        
        return any(keyword in text_lower for keyword in title_keywords)
    
    def scrape_category_with_retry(self, category_name, url, idx, total):
        """Scrape a single category with retry logic - each worker gets its own driver"""
        driver = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                with self.lock:
                    logger.info(f"\n{'=' * 80}")
                    logger.info(f"📂 CATEGORY {idx}/{total}: {category_name.replace('_', ' ')}")
                    if attempt > 1:
                        logger.info(f"🔄 Retry attempt {attempt}/{self.max_retries}")
                    logger.info(f"{'=' * 80}")
                
                # Create driver for this worker if not exists
                if driver is None:
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--disable-software-rasterizer')
                    chrome_options.add_argument('--window-size=1920,1080')
                    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
                    chrome_options.add_argument('--disable-images')
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                    chrome_options.add_experimental_option("prefs", {
                        "profile.managed_default_content_settings.images": 2
                    })
                    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                    chrome_options.page_load_strategy = 'eager'
                    driver = webdriver.Chrome(options=chrome_options)
                    with self.lock:
                        logger.info("✓ Chrome driver initialized (headless) for worker")
                
                jobs = []
                date_samples = []
                
                with self.lock:
                    logger.info(f"\n🌐 Loading {url}...")
                driver.get(url)
                
                with self.lock:
                    logger.info("⏳ Waiting for table to load (30 seconds)...")
                time.sleep(30)
                
                with self.lock:
                    logger.info("\n🔄 Scrolling right to load all columns...")
                self.scroll_table_horizontally_with_driver(driver)
                
                cutoff_str = self.cutoff_date.strftime('%Y-%m-%d %H:%M')
                with self.lock:
                    logger.info(f"\n📜 Extracting jobs posted after {cutoff_str} (last {self.hours_lookback} hours)...")
                jobs, date_samples = self.extract_recent_jobs_with_driver(driver, category_name)
                
                with self.lock:
                    logger.info(f"\n✅ Found {len(jobs)} jobs from last {self.hours_lookback} hours in {category_name}")
                
                # Add jobs to all_jobs (already in unified format)
                with self.lock:
                    self.all_jobs.extend(jobs)
                    
                    if len(jobs) == 0:
                        self.empty_categories.append(category_name)
                    else:
                        self.total_jobs_found += len(jobs)
                
                if len(jobs) == 0 and date_samples:
                    with self.lock:
                        logger.info("\n🔍 Date Parsing Debug (checking why no jobs found):")
                        unique_dates = list(set([s[1] if s[0] == 'FAILED' else s[1] for s in date_samples[:10]]))
                        for date_str in unique_dates[:5]:
                            parsed = self.parse_date(date_str)
                            if parsed:
                                logger.info(f"  📅 '{date_str}' → {parsed.strftime('%Y-%m-%d')} (TOO OLD)" if parsed < self.cutoff_date else f"  ✓ '{date_str}' → {parsed.strftime('%Y-%m-%d')}")
                            else:
                                logger.info(f"  ❌ '{date_str}' → FAILED TO PARSE")
                elif date_samples:
                    with self.lock:
                        logger.info("\n🔍 Date Parsing Debug (first 3 samples):")
                        for sample in date_samples[:3]:
                            if sample[0] == 'SUCCESS':
                                logger.info(f"  ✓ '{sample[1]}' → {sample[2].strftime('%Y-%m-%d %H:%M')}")
                
                # Clean up driver
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                
                return {
                    'url': url,
                    'job_count': len(jobs),
                    'jobs': jobs.copy(),
                    'status': 'success'
                }
                
            except (InvalidSessionIdException, WebDriverException) as e:
                with self.lock:
                    logger.error(f"\n❌ Session error on attempt {attempt}: {str(e)[:100]}")
                if attempt < self.max_retries:
                    with self.lock:
                        logger.info(f"⏳ Waiting 10 seconds before retry...")
                    time.sleep(10)
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    driver = None
                else:
                    with self.lock:
                        logger.error(f"✗ Failed after {self.max_retries} attempts")
                        self.failed_categories.append(category_name)
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    return {
                        'url': url,
                        'job_count': 0,
                        'jobs': [],
                        'status': 'failed',
                        'error': str(e)[:200]
                    }
            
            except Exception as e:
                with self.lock:
                    logger.error(f"\n❌ Unexpected error on attempt {attempt}: {e}")
                if attempt < self.max_retries:
                    with self.lock:
                        logger.info(f"⏳ Waiting 10 seconds before retry...")
                    time.sleep(10)
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    driver = None
                else:
                    with self.lock:
                        logger.error(f"✗ Failed after {self.max_retries} attempts")
                        self.failed_categories.append(category_name)
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    return {
                        'url': url,
                        'job_count': 0,
                        'jobs': [],
                        'status': 'failed',
                        'error': str(e)[:200]
                    }
        
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        return {
            'url': url,
            'job_count': 0,
            'jobs': [],
            'status': 'failed',
            'error': 'Max retries exceeded'
        }
    
    def scrape_all_categories(self, specific_categories=None):
        """Scrape all job categories in parallel"""
        all_results = {}
        
        try:
            categories_to_scrape = specific_categories if specific_categories else list(self.categories.keys())
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"🚀 Starting parallel scraping with {self.num_workers} workers")
            logger.info(f"📊 Scanning {len(categories_to_scrape)} categories")
            logger.info(f"{'=' * 80}")
            
            # Parallel execution
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = {}
                for idx, category_name in enumerate(categories_to_scrape, 1):
                    if category_name not in self.categories:
                        logger.warning(f"⚠️  Category '{category_name}' not found. Skipping...")
                        continue
                    
                    url = self.categories[category_name]
                    future = executor.submit(self.scrape_category_with_retry, category_name, url, idx, len(categories_to_scrape))
                    futures[future] = category_name
                
                # Collect results as they complete
                for future in as_completed(futures):
                    category_name = futures[future]
                    try:
                        result = future.result()
                        all_results[category_name] = result
                        with self.lock:
                            logger.info(f"\n✓ Completed {len(all_results)}/{len(categories_to_scrape)} categories")
                    except Exception as e:
                        with self.lock:
                            logger.error(f"❌ Failed to get result for {category_name}: {e}")
                        all_results[category_name] = {
                            'url': self.categories[category_name],
                            'job_count': 0,
                            'jobs': [],
                            'status': 'failed',
                            'error': str(e)[:200]
                        }
            
            # Save consolidated files
            self.save_consolidated_files(all_results)
            
            # Save summary
            self.save_summary(all_results)
            
            # Print final analysis
            self.print_final_analysis(all_results)
            
        except KeyboardInterrupt:
            logger.warning("\n\n⚠️  Scraping interrupted by user")
            self.save_consolidated_files(all_results)
            self.save_summary(all_results)
            self.print_final_analysis(all_results)
        except Exception as e:
            logger.error(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.driver:
                logger.info("\n" + "=" * 80)
                logger.info("🏁 SCRAPING COMPLETED")
                logger.info("=" * 80)
                try:
                    self.driver.quit()
                    logger.info("✓ Browser closed")
                except:
                    pass
        
        return all_results
    
    def save_consolidated_files(self, all_results):
        """Save all jobs from all categories into single JSON and CSV files"""
        folder_name = "scraped_jobs"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save consolidated JSON
        json_file = os.path.join(folder_name, f"all_jobs_{self.hours_lookback}h_{timestamp}.json")
        
        # Build category breakdown
        category_breakdown = {}
        for cat_name, result in all_results.items():
            category_breakdown[cat_name] = {
                'job_count': result.get('job_count', 0),
                'status': result.get('status', 'unknown')
            }
        
        output = {
            'metadata': {
                'scraped_at': datetime.now().isoformat(),
                'cutoff_date': self.cutoff_date.isoformat(),
                'time_range': f'last {self.hours_lookback} hours',
                'total_jobs': len(self.all_jobs),
                'total_categories': len(all_results),
                'categories_with_jobs': sum(1 for r in all_results.values() if r.get('job_count', 0) > 0),
                'category_breakdown': category_breakdown
            },
            'jobs': self.all_jobs
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📦 CONSOLIDATED JSON saved: {json_file}")
        logger.info(f"   Total jobs: {len(self.all_jobs)}")
        
        # Save consolidated CSV
        csv_file = os.path.join(folder_name, f"all_jobs_{self.hours_lookback}h_{timestamp}.csv")
        
        if self.all_jobs:
            keys = ['category', 'title', 'company', 'location', 'work_model', 'salary', 'date_posted', 
                    'company_size', 'company_industry', 'h1b_sponsored', 'is_new_grad', 
                    'qualifications', 'url']
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.all_jobs)
            
            logger.info(f"📦 CONSOLIDATED CSV saved: {csv_file}")
        else:
            logger.warning("⚠️  No jobs to save in CSV")
        
        # Save consolidated markdown
        md_file = os.path.join(folder_name, f"all_jobs_{self.hours_lookback}h_{timestamp}.md")
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# All New Grad Jobs - Consolidated Report\n\n")
            f.write(f"**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Time Range:** Last {self.hours_lookback} hours ({self.hours_lookback/24:.1f} days)\n\n")
            f.write(f"**Cutoff Date:** {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Jobs:** {len(self.all_jobs)}\n\n")
            f.write("---\n\n")
            
            # Group jobs by category
            jobs_by_category = {}
            for job in self.all_jobs:
                cat = job.get('category', 'Unknown')
                if cat not in jobs_by_category:
                    jobs_by_category[cat] = []
                jobs_by_category[cat].append(job)
            
            f.write("## Table of Contents\n\n")
            for cat in sorted(jobs_by_category.keys()):
                count = len(jobs_by_category[cat])
                f.write(f"- [{cat}](#{cat.lower().replace(' ', '-')}) ({count} jobs)\n")
            f.write("\n---\n\n")
            
            # Write jobs grouped by category
            for cat in sorted(jobs_by_category.keys()):
                jobs = jobs_by_category[cat]
                f.write(f"## {cat}\n\n")
                f.write(f"**Total Jobs:** {len(jobs)}\n\n")
                
                for idx, job in enumerate(jobs, 1):
                    f.write(f"### {idx}. {job.get('title', 'N/A')}\n\n")
                    f.write(f"| Field | Value |\n")
                    f.write(f"|-------|-------|\n")
                    f.write(f"| **Company** | {job.get('company', 'N/A')} |\n")
                    f.write(f"| **Location** | {job.get('location', 'N/A')} |\n")
                    f.write(f"| **Work Model** | {job.get('work_model', 'N/A')} |\n")
                    f.write(f"| **Salary** | {job.get('salary', 'N/A')} |\n")
                    f.write(f"| **Date Posted** | {job.get('date_posted', 'N/A')} |\n")
                    f.write(f"| **Company Size** | {job.get('company_size', 'N/A')} |\n")
                    f.write(f"| **H1B Sponsored** | {job.get('h1b_sponsored', 'N/A')} |\n")
                    
                    if job.get('url'):
                        f.write(f"| **Apply** | [👉 Apply]({job.get('url')}) |\n")
                    
                    f.write(f"\n---\n\n")
                
                f.write("\n\n")
        
        logger.info(f"📦 CONSOLIDATED MARKDOWN saved: {md_file}")
        logger.info(f"\n✅ All consolidated files saved in: {folder_name}/")
    
    def print_final_analysis(self, all_results):
        """Print comprehensive analysis of scraping results"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 FINAL ANALYSIS")
        logger.info("=" * 80)
        
        successful = sum(1 for r in all_results.values() if r.get('status') == 'success')
        total_jobs = sum(r.get('job_count', 0) for r in all_results.values())
        
        logger.info(f"\n✅ Successfully scraped: {successful}/{len(all_results)} categories")
        logger.info(f"📈 Total jobs found: {total_jobs}")
        logger.info(f"📅 Time window: Last {self.hours_lookback} hours ({self.hours_lookback/24:.1f} days)")
        
        categories_with_jobs = [(k, v['job_count']) for k, v in all_results.items() if v.get('job_count', 0) > 0]
        if categories_with_jobs:
            logger.info(f"\n🎯 Categories with jobs ({len(categories_with_jobs)}):")
            for cat, count in sorted(categories_with_jobs, key=lambda x: x[1], reverse=True):
                logger.info(f"   ✅ {cat.replace('_', ' ')}: {count} jobs")
        
        if self.empty_categories:
            logger.info(f"\n⚠️  Categories with 0 jobs ({len(self.empty_categories)}):")
            for cat in self.empty_categories[:5]:
                logger.info(f"   📭 {cat.replace('_', ' ')}")
            if len(self.empty_categories) > 5:
                logger.info(f"   ... and {len(self.empty_categories) - 5} more")
            
            if self.hours_lookback < 336:
                logger.info(f"\n💡 Try running again with 14-30 day window for better coverage")
        
        if self.failed_categories:
            logger.info(f"\n❌ Failed categories ({len(self.failed_categories)}):")
            for cat in self.failed_categories:
                logger.info(f"   ✗ {cat.replace('_', ' ')}")
        
        if total_jobs > 0:
            avg_jobs_per_category = total_jobs / max(len(categories_with_jobs), 1)
            logger.info(f"\n📊 Data Quality Metrics:")
            logger.info(f"   Average jobs per active category: {avg_jobs_per_category:.1f}")
            logger.info(f"   Category coverage: {len(categories_with_jobs)}/{len(all_results)} ({100*len(categories_with_jobs)/len(all_results):.1f}%)")
    
    def scroll_table_horizontally_with_driver(self, driver):
        """Scroll the table horizontally to load all columns"""
        try:
            selectors = [
                'div[class*="tableContainer"]',
                'div[class*="gridViewContainer"]',
                'div[class*="viewport"]',
                'div[role="table"]'
            ]
            
            table_container = None
            for selector in selectors:
                try:
                    table_container = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if table_container:
                for i in range(10):
                    driver.execute_script("arguments[0].scrollLeft += 300;", table_container)
                    time.sleep(0.3)
                
                driver.execute_script("arguments[0].scrollLeft = 0;", table_container)
                time.sleep(1)
                with self.lock:
                    logger.info("  ✓ Columns loaded (container method)")
                return
        except:
            pass
        
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(15):
                body.send_keys(Keys.ARROW_RIGHT)
                time.sleep(0.2)
            for _ in range(15):
                body.send_keys(Keys.ARROW_LEFT)
                time.sleep(0.2)
            with self.lock:
                logger.info("  ✓ Columns loaded (arrow keys method)")
        except:
            with self.lock:
                logger.warning("  ⚠️ Horizontal scroll failed, continuing anyway...")
    
    def scroll_table_horizontally(self):
        """Legacy method - kept for compatibility"""
        if self.driver:
            self.scroll_table_horizontally_with_driver(self.driver)
    
    def extract_recent_jobs_with_driver(self, driver, category=None):
        """Extract jobs from the configured timeframe using specific driver"""
        jobs = []
        date_samples = []
        seen_titles = set()
        no_new_data_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 50
        old_jobs_in_a_row = 0
        max_old_jobs = 20
        
        while no_new_data_count < 5 and scroll_attempts < max_scroll_attempts and old_jobs_in_a_row < max_old_jobs:
            with self.lock:
                logger.info(f"\n  → Scroll attempt {scroll_attempts + 1} | Recent jobs: {len(jobs)}")
            
            time.sleep(2)
            
            new_jobs, old_job_count, new_date_samples = self.extract_visible_jobs_with_driver(driver, seen_titles, category)
            jobs.extend(new_jobs)
            date_samples.extend(new_date_samples)
            
            if new_jobs:
                with self.lock:
                    logger.info(f"  ✓ Found {len(new_jobs)} jobs from timeframe")
                no_new_data_count = 0
                old_jobs_in_a_row = 0
            else:
                no_new_data_count += 1
                with self.lock:
                    logger.info(f"  ⚠️  No new recent jobs (attempt {no_new_data_count}/5)")
            
            if old_job_count > 0 and len(new_jobs) == 0:
                old_jobs_in_a_row += old_job_count
                with self.lock:
                    logger.info(f"  ⏱️  Seeing older jobs... ({old_jobs_in_a_row}/{max_old_jobs} old jobs)")
            
            if old_jobs_in_a_row >= max_old_jobs:
                with self.lock:
                    logger.info(f"\n  🏁 Reached jobs older than {self.hours_lookback} hours - stopping")
                break
            
            self.perform_scroll_with_driver(driver)
            scroll_attempts += 1
        
        return jobs, date_samples
    
    def extract_recent_jobs(self):
        """Legacy method - kept for compatibility"""
        if self.driver:
            jobs, date_samples = self.extract_recent_jobs_with_driver(self.driver)
            self.jobs = jobs
            self.date_samples = date_samples
    
    def perform_scroll_with_driver(self, driver):
        """Perform various scrolling methods with specific driver"""
        try:
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(0.5)
            
            scrollable_divs = driver.find_elements(By.CSS_SELECTOR, 'div[style*="overflow"]')
            for div in scrollable_divs[:3]:
                try:
                    driver.execute_script("arguments[0].scrollTop += 600;", div)
                    time.sleep(0.3)
                except:
                    pass
            
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.5)
            
        except Exception as e:
            pass
    
    def perform_scroll(self):
        """Legacy method - kept for compatibility"""
        if self.driver:
            self.perform_scroll_with_driver(self.driver)
    
    def extract_visible_jobs_with_driver(self, driver, seen_titles, category=None):
        """Extract jobs using IMPROVED SMART FIELD DETECTION with specific driver"""
        new_jobs = []
        old_job_count = 0
        date_samples = []
        
        try:
            all_row_elements = driver.find_elements(By.CSS_SELECTOR, 'div.dataRow[data-rowid]')
            
            rows_by_id = {}
            for elem in all_row_elements:
                row_id = elem.get_attribute('data-rowid')
                if row_id not in rows_by_id:
                    rows_by_id[row_id] = []
                rows_by_id[row_id].append(elem)
            
            with self.lock:
                logger.info(f"  Found {len(rows_by_id)} unique rows")
            
            for row_id, row_elements in rows_by_id.items():
                try:
                    job = {'row_id': row_id}
                    
                    all_cells = []
                    for row_elem in row_elements:
                        cells = row_elem.find_elements(By.CSS_SELECTOR, 'div[data-columnid]')
                        all_cells.extend(cells)
                    
                    cell_texts = []
                    for cell in all_cells:
                        try:
                            column_id = cell.get_attribute('data-columnid')
                            
                            cell_text = cell.text.strip()
                            if not cell_text:
                                cell_text = cell.get_attribute('innerText')
                                if cell_text:
                                    cell_text = cell_text.strip()
                            if not cell_text:
                                cell_text = cell.get_attribute('textContent')
                                if cell_text:
                                    cell_text = cell_text.strip()
                            
                            if cell_text:
                                cell_texts.append(cell_text)
                            
                            try:
                                link = cell.find_element(By.TAG_NAME, 'a')
                                job['url'] = link.get_attribute('href')
                            except:
                                pass
                                
                        except:
                            continue
                    
                    # PHASE 1: FIND THE DATE FIRST
                    for text in cell_texts:
                        if 'date_posted' not in job:
                            parsed = self.parse_date(text)
                            if parsed:
                                job['date_posted'] = text
                                date_samples.append(('SUCCESS', text, parsed))
                                break
                            elif text and len(text) > 0 and self.is_likely_date(text):
                                date_samples.append(('FAILED', text))
                    
                    # PHASE 2: DETECT OTHER FIELDS
                    for text in cell_texts:
                        if len(text) < 2 or len(text) > 500:
                            continue
                        
                        if text == job.get('date_posted'):
                            continue
                        
                        if 'title' not in job and self.is_likely_title(text):
                            job['title'] = text
                        
                        elif 'location' not in job and self.is_likely_location(text):
                            job['location'] = text
                        
                        elif 'work_model' not in job and text in ['Remote', 'Hybrid', 'On-site', 'Onsite', 'In-person', 'In-Person', 'On Site']:
                            job['work_model'] = text
                        
                        elif 'salary' not in job and self.is_likely_salary(text):
                            job['salary'] = text
                        
                        elif 'h1b_sponsored' not in job and self.is_likely_visa(text):
                            job['h1b_sponsored'] = text
                        
                        elif 'company' not in job and self.is_likely_company(text) and len(text) < 60:
                            job['company'] = text
                        
                        elif len(text) > 100 and 'qualifications' not in job:
                            job['qualifications'] = text
                        
                        text_lower = text.lower()
                        if 'new grad' in text_lower or 'new-grad' in text_lower or 'entry level' in text_lower:
                            job['is_new_grad'] = 'Yes'
                        
                        if any(size in text for size in ['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+', '10000+', '1001-5000', '5001-10000', '101-250']):
                            if 'company_size' not in job:
                                job['company_size'] = text
                    
                    title = job.get('title', '')
                    if title and len(title) > 3 and title not in seen_titles:
                        date_posted = job.get('date_posted', '')
                        
                        if self.is_within_timeframe(date_posted):
                            seen_titles.add(title)
                            
                            # Standardize to unified schema
                            unified_job = {
                                'job_id': job.get('row_id') or None,
                                'url': job.get('url') or None,
                                'title': job.get('title') or None,
                                'company': job.get('company') or None,
                                'location': job.get('location') or None,
                                'description': None,
                                'snippet': job.get('qualifications') or None,
                                'salary_min': None,
                                'salary_max': None,
                                'salary_text': job.get('salary') or None,
                                'job_type': None,
                                'work_model': job.get('work_model') or None,
                                'department': None,
                                'company_size': job.get('company_size') or None,
                                'qualifications': job.get('qualifications') or None,
                                'h1b_sponsored': job.get('h1b_sponsored') or None,
                                'is_new_grad': job.get('is_new_grad') or None,
                                'category': category,
                                'posted_date': date_posted or None,
                                'scraped_at': datetime.now().isoformat(),
                                'source': 'airtable',
                                'raw_json': {
                                    'original_row_data': job
                                }
                            }
                            
                            new_jobs.append(unified_job)
                            with self.lock:
                                logger.info(f"    ✓ [{len(new_jobs)}] {title[:60]}... ({date_posted})")
                        else:
                            old_job_count += 1
                    
                except:
                    continue
                    
        except Exception as e:
            with self.lock:
                logger.warning(f"  ⚠️  Error extracting: {str(e)[:100]}")
        
        return new_jobs, old_job_count, date_samples
    
    def extract_visible_jobs(self, seen_titles):
        """Legacy method - kept for compatibility"""
        if self.driver:
            new_jobs, old_job_count, date_samples = self.extract_visible_jobs_with_driver(self.driver, seen_titles)
            self.date_samples.extend(date_samples)
            return new_jobs, old_job_count
        return [], 0
    
    def save_summary(self, all_results):
        """Save summary file"""
        summary_file = "scraped_jobs/SUMMARY.md"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# New Grad Jobs Scraping Summary\n\n")
            f.write(f"**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Time Range:** Last {self.hours_lookback} hours ({self.hours_lookback/24:.1f} days)\n\n")
            f.write(f"**Cutoff Date:** {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            total_jobs = sum(result.get('job_count', 0) for result in all_results.values())
            successful = sum(1 for r in all_results.values() if r.get('status') == 'success')
            failed = sum(1 for r in all_results.values() if r.get('status') == 'failed')
            empty = len([r for r in all_results.values() if r.get('job_count', 0) == 0 and r.get('status') == 'success'])
            
            f.write(f"**Total Jobs Across All Categories:** {total_jobs}\n\n")
            f.write(f"**Successful Categories:** {successful}/{len(all_results)}\n\n")
            f.write(f"**Categories with Jobs:** {successful - empty}/{len(all_results)}\n\n")
            f.write(f"**Empty Categories:** {empty}\n\n")
            if failed > 0:
                f.write(f"**Failed Categories:** {failed}\n\n")
            f.write("---\n\n")
            
            f.write("## Jobs by Category\n\n")
            f.write("| Category | Job Count | Status |\n")
            f.write("|----------|-----------|--------|\n")
            
            sorted_results = sorted(all_results.items(), key=lambda x: x[1].get('job_count', 0), reverse=True)
            
            for category_name, result in sorted_results:
                display_name = category_name.replace('_', ' ')
                job_count = result.get('job_count', 0)
                
                if result.get('status') == 'failed':
                    status_emoji = "❌ Failed"
                elif job_count == 0:
                    status_emoji = "📭 Empty"
                else:
                    status_emoji = "✅ Success"
                
                f.write(f"| {display_name} | **{job_count}** | {status_emoji} |\n")
            
            if empty > 0:
                f.write("\n---\n\n")
                f.write("## 💡 Note on Empty Categories\n\n")
                f.write(f"{empty} categories returned 0 jobs in the {self.hours_lookback} hour window.\n\n")
                
                if self.hours_lookback < 336:
                    f.write("**Suggestion:** Re-run with 14-30 day window for better coverage.\n\n")
            
            if failed > 0:
                f.write("\n---\n\n")
                f.write("## Failed Categories\n\n")
                for category_name, result in all_results.items():
                    if result.get('status') == 'failed':
                        error = result.get('error', 'Unknown error')
                        f.write(f"- **{category_name}**: {error}\n")
        
        logger.info(f"📄 Summary saved to: {summary_file}")


if __name__ == "__main__":
    print("=" * 80)
    print(" " * 10 + "NEW GRAD JOB SCRAPER - CONSOLIDATED OUTPUT")
    print(" " * 12 + "(All jobs saved in one JSON + CSV file)")
    print("=" * 80)
    
    print("\n⚙️  Configuration Options:")
    print("1. Scrape last 48 hours")
    print("2. Scrape last 7 days (168 hours) [RECOMMENDED]")
    print("3. Scrape last 14 days (336 hours)")
    print("4. Scrape all jobs (720 hours / 30 days)")
    print("5. Custom hours")
    
    choice = input("\nEnter your choice (1-5) [default: 2]: ").strip() or "2"
    
    hours_map = {
        "1": 48,
        "2": 168,
        "3": 336,
        "4": 720
    }
    
    if choice == "5":
        hours_lookback = int(input("Enter custom hours to look back: "))
    else:
        hours_lookback = hours_map.get(choice, 168)
    
    num_workers = input("\n🔧 Number of parallel workers (1-8) [default: 7]: ").strip()
    num_workers = int(num_workers) if num_workers and num_workers.isdigit() else 7
    num_workers = max(1, min(8, num_workers))  # Limit to 1-8 workers
    
    print(f"\n🎯 Scraping jobs from last {hours_lookback} hours ({hours_lookback/24:.1f} days)")
    print(f"📊 Scanning {len(AirtableJobScraper().categories)} job categories")
    print(f"🚀 Using {num_workers} parallel workers")
    print(f"⏱️  Estimated time: {len(AirtableJobScraper().categories) // num_workers * 2} minutes total")
    print(f"🔄 Max retries per category: 3")
    print(f"🧠 Using improved date detection")
    print(f"📦 Output: Single consolidated JSON + CSV file\n")
    
    scrape_all = input("Scrape all categories? (y/n) [default: y]: ").strip().lower() or "y"
    
    scraper = AirtableJobScraper(hours_lookback=hours_lookback, num_workers=num_workers)
    
    if scrape_all == "n":
        print("\nAvailable categories:")
        for i, cat in enumerate(scraper.categories.keys(), 1):
            print(f"  {i}. {cat.replace('_', ' ')}")
        
        cat_input = input("\nEnter category numbers (comma-separated, e.g., 1,2,5): ").strip()
        category_indices = [int(x.strip()) for x in cat_input.split(",")]
        category_names = [list(scraper.categories.keys())[i-1] for i in category_indices]
        
        results = scraper.scrape_all_categories(specific_categories=category_names)
    else:
        results = scraper.scrape_all_categories()
    
    print("\n" + "=" * 80)
    print("🎉 SCRAPING COMPLETED!")
    print("=" * 80)
    
    total_jobs = sum(result.get('job_count', 0) for result in results.values())
    successful = sum(1 for r in results.values() if r.get('status') == 'success')
    failed = sum(1 for r in results.values() if r.get('status') == 'failed')
    empty = len([r for r in results.values() if r.get('job_count', 0) == 0 and r.get('status') == 'success'])
    
    print(f"\n📊 Total jobs found: {total_jobs}")
    print(f"📅 Time range: Last {hours_lookback} hours ({hours_lookback/24:.1f} days)")
    print(f"✅ Successful: {successful}/{len(results)} categories")
    print(f"📭 Empty: {empty}/{len(results)} categories")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(results)} categories")
    
    print("\n📁 All files saved in: scraped_jobs/")
    print(f"   📦 all_jobs_{hours_lookback}h_[timestamp].json (consolidated)")
    print(f"   📦 all_jobs_{hours_lookback}h_[timestamp].csv (consolidated)")
    print(f"   📦 all_jobs_{hours_lookback}h_[timestamp].md (formatted report)")
    print(f"   📄 SUMMARY.md (overview)")
    
    print("\n" + "=" * 80)