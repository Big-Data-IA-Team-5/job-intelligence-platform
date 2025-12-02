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

class ComprehensiveAirtableScraper:
    def __init__(self, hours_lookback=720, max_retries=3, num_workers=5):
        """
        Comprehensive Airtable scraper that goes into each category individually
        Args:
            hours_lookback: Number of hours to look back for jobs (default: 720 = 30 days)
            max_retries: Maximum retries for failed categories (default: 3)
            num_workers: Number of parallel workers (default: 5)
        """
        self.num_workers = num_workers
        self.lock = threading.Lock()
        
        # ALL AIRTABLE CATEGORIES - organized by job type
        self.categories = {
            # Technical Roles
            'Software_Engineering': 'https://airtable.com/appjDG7vmPOm1pO7S/shr763VHjlzPBDCgN/tblLP4AtskrLA8Aw1?viewControls=on',
            'Data_Engineer': 'https://airtable.com/appqYfRGKpLQ8UsdH/shrFnvW20reJCEkYZ/tblDVfWJzDdU8KsoY?viewControls=on',
            'Machine_Learning_AI': 'https://airtable.com/appoxNzAIRReFCzZV/shrmDBF1vNPtzNjzl/tbldeT1mbQGFwtwpa?viewControls=on',
            'Cyber_Security': 'https://airtable.com/app5K4hbJeNczKe80/shrmicWx3O72527KW/tbl0nEY7kMwmxBzVS?viewControls=on',
            'Engineering_Development': 'https://airtable.com/appTmAS0zZwcwxhoo/shrZzO1d5s5qGPRgr/tblkOVG7BaimFY0C6?viewControls=on',
            
            # Data & Analytics
            'Data_Analyst': 'https://airtable.com/appZ5SmkwkcW7Xd8C/shr51y9s2uIRlkvI8/tblnD3h2G6iiA0Csr?viewControls=on',
            'Business_Analyst': 'https://airtable.com/appK8wuhdzqC2KtWr/shrlXw5IPUECgZH9Q/tbljDinzQ1c29E24C?viewControls=on',
            
            # Business Roles
            'Product_Management': 'https://airtable.com/appYvVTjJYHpq712D/shrpI5GFPocw2qcre/tblPKs03ZmPmgXeZU?viewControls=on',
            'Project_Manager': 'https://airtable.com/app5K4hbJeNczKe80/shrmicWx3O72527KW/tbl0nEY7kMwmxBzVS?viewControls=on',
            'Marketing': 'https://airtable.com/appcUz4GkJoWzTX3C/shrlp6fQzQ5mD68nC/tbldH61sRyLEQ6xSa?viewControls=on',
            'Sales': 'https://airtable.com/appoX5NsnYmJ3aeTd/shr1tIFqsoekDopXF/tblfENWXGILRBAAJF?viewControls=on',
            'Consulting': 'https://airtable.com/appk3hzdIFG7MVEqq/shr7BAtGeCN125QYK/tblRSPZ04WqHbNgVl?viewControls=on',
            'Management_Executive': 'https://airtable.com/appFa3PBhYWICqdV9/shrkuNa5I9zuPNlA1/tblWMm3zBbFv0TIq5?viewControls=on',
            
            # Finance & Accounting
            'Accounting_Finance': 'https://airtable.com/app3hKGPjx4m3n8uy/shrxflLkiF1ljjPgZ/tblsoYj6mVDT4Fvoz?viewControls=on',
            
            # Support & Operations
            'Human_Resources': 'https://airtable.com/appTYQlu4ffssFoAb/shrsYDrGPeDnGrxGV/tblsZIPj9cVSdTWtA?viewControls=on',
            'Customer_Service_Support': 'https://airtable.com/appUymIq1nGtqN2XK/shrwfk23CnWMKnVGD/tblq0hLymPp8Jss3Q?viewControls=on',
            'Legal_Compliance': 'https://airtable.com/appFU12UKGbt1gs95/shrVVTUffhqFK98J1/tblLXNqHxMVp7QIcl?viewControls=on',
            
            # Creative & Other
            'Creatives_Design': 'https://airtable.com/app7O2uKT9GTvMx9J/shrWEq2l15qeODGG3/tbllfcKFR3K5dDXmE?viewControls=on',
            'Arts_Entertainment': 'https://airtable.com/appxsdozleC9iaktr/shrtavKK7PhghGUt5/tblnkZfp7JMENSblI?viewControls=on',
            'Education_Training': 'https://airtable.com/appPYy0RX5fDsEhZm/shrYLlad4LNZEicQd/tblJgoMCG1GQVc3m3?viewControls=on',
            'Health_Care': 'https://airtable.com/appqXoZFUXnMz1QZH/shr8D4joJaLDSnum1/tblDzOjYZXCT5Pqtb?viewControls=on',
        }
        
        self.all_jobs = []
        self.hours_lookback = hours_lookback
        self.max_retries = max_retries
        self.cutoff_date = datetime.now() - timedelta(hours=hours_lookback)
        self.failed_categories = []
        self.empty_categories = []
        self.total_jobs_found = 0
        
    def parse_date(self, date_string):
        """Parse date string from Airtable to datetime object"""
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
        
        # Relative dates
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
            return False
        
        return parsed_date >= self.cutoff_date
    
    def is_likely_date(self, text):
        """Check if text looks like a date"""
        if not text or len(text) > 30 or len(text) < 8:
            return False
        
        if text.lower() in ['apply', 'remote', 'hybrid', 'on-site', 'onsite', 'on site']:
            return False
        
        if self.parse_date(text):
            return True
        
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{2}/\d{2}/\d{4}$',
            r'^\d{2}-\d{2}-\d{4}$',
            r'^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$',
            r'^\d{1,2}/\d{1,2}/\d{4}$',
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
        
        if re.search(r',\s*[A-Z]{2}$', text):
            return True
        
        location_keywords = [
            'remote', 'hybrid', 'on-site', 'onsite', 'in-person',
            'usa', 'us', 'united states', 'america',
            'ny', 'ca', 'tx', 'fl', 'il', 'pa', 'ma', 'wa', 'va', 'nc',
            'new york', 'california', 'texas', 'florida', 'seattle',
            'san francisco', 'boston', 'austin', 'chicago', 'atlanta',
            'denver', 'portland', 'phoenix', 'dallas', 'houston',
            'los angeles', 'washington dc', 'miami', 'philadelphia',
            ', usa', ', us', 'multi location'
        ]
        
        return any(keyword in text_lower for keyword in location_keywords)
    
    def is_likely_salary(self, text):
        """Check if text looks like a salary"""
        if not text or len(text) > 50:
            return False
        
        text_lower = text.lower()
        
        return ('$' in text or 
                'k' in text_lower or 
                '/yr' in text_lower or
                '/hr' in text_lower or
                any(word in text_lower for word in ['salary', 'compensation', 'pay', 'hourly', 'annual']))
    
    def is_likely_company(self, text):
        """Check if text looks like a company name"""
        if not text or len(text) > 100 or len(text) < 2:
            return False
        
        if re.search(r',\s*[A-Z]{2}$', text):
            return False
        
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
    
    def scrape_category_comprehensive(self, category_name, url, idx, total):
        """Comprehensively scrape a single category - each worker gets its own driver"""
        driver = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                with self.lock:
                    logger.info(f"\n{'=' * 80}")
                    logger.info(f"📂 CATEGORY {idx}/{total}: {category_name.replace('_', ' ')}")
                    if attempt > 1:
                        logger.info(f"🔄 Retry attempt {attempt}/{self.max_retries}")
                    logger.info(f"{'=' * 80}")
                
                # Create dedicated driver for this worker
                if driver is None:
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--window-size=1920,1080')
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                    chrome_options.page_load_strategy = 'normal'
                    driver = webdriver.Chrome(options=chrome_options)
                    with self.lock:
                        logger.info("✓ Chrome driver initialized")
                
                with self.lock:
                    logger.info(f"\n🌐 Loading {url}...")
                driver.get(url)
                
                with self.lock:
                    logger.info("⏳ Waiting for table to load (30 seconds)...")
                time.sleep(30)
                
                with self.lock:
                    logger.info("\n🔄 Scrolling horizontally to load all columns...")
                self.scroll_horizontally(driver)
                
                cutoff_str = self.cutoff_date.strftime('%Y-%m-%d %H:%M')
                with self.lock:
                    logger.info(f"\n📜 Extracting jobs posted after {cutoff_str}...")
                    logger.info(f"   (Last {self.hours_lookback} hours / {self.hours_lookback/24:.1f} days)")
                
                jobs = self.extract_all_jobs_from_category(driver, category_name)
                
                with self.lock:
                    logger.info(f"\n✅ Extracted {len(jobs)} jobs from {category_name}")
                
                # Add to global collection
                with self.lock:
                    self.all_jobs.extend(jobs)
                    
                    if len(jobs) == 0:
                        self.empty_categories.append(category_name)
                    else:
                        self.total_jobs_found += len(jobs)
                
                # Cleanup
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
                
            except Exception as e:
                with self.lock:
                    logger.error(f"\n❌ Error on attempt {attempt}: {str(e)[:100]}")
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
    
    def scroll_horizontally(self, driver):
        """Scroll table horizontally to load all columns"""
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
        except:
            pass
    
    def extract_all_jobs_from_category(self, driver, category):
        """Extract ALL jobs from a category with comprehensive scrolling"""
        all_jobs = []
        seen_titles = set()
        no_new_data_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 100  # Increased for comprehensive scraping
        
        with self.lock:
            logger.info(f"\n🔍 Starting comprehensive extraction for {category}...")
        
        while no_new_data_count < 5 and scroll_attempts < max_scroll_attempts:
            if scroll_attempts % 10 == 0:
                with self.lock:
                    logger.info(f"\n  → Scroll {scroll_attempts + 1} | Total jobs: {len(all_jobs)}")
            
            time.sleep(2)
            
            new_jobs = self.extract_visible_jobs(driver, seen_titles, category)
            all_jobs.extend(new_jobs)
            
            if new_jobs:
                no_new_data_count = 0
            else:
                no_new_data_count += 1
            
            self.perform_scroll(driver)
            scroll_attempts += 1
        
        with self.lock:
            logger.info(f"\n  ✓ Extraction complete after {scroll_attempts} scrolls")
            logger.info(f"  ✓ Total unique jobs found: {len(all_jobs)}")
        
        return all_jobs
    
    def perform_scroll(self, driver):
        """Perform scrolling to load more content"""
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
            
        except:
            pass
    
    def extract_visible_jobs(self, driver, seen_titles, category):
        """Extract currently visible jobs from the page"""
        new_jobs = []
        
        try:
            all_row_elements = driver.find_elements(By.CSS_SELECTOR, 'div.dataRow[data-rowid]')
            
            rows_by_id = {}
            for elem in all_row_elements:
                row_id = elem.get_attribute('data-rowid')
                if row_id not in rows_by_id:
                    rows_by_id[row_id] = []
                rows_by_id[row_id].append(elem)
            
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
                            cell_text = cell.text.strip()
                            if not cell_text:
                                cell_text = cell.get_attribute('innerText')
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
                    
                    # Extract date first
                    for text in cell_texts:
                        if 'date_posted' not in job:
                            parsed = self.parse_date(text)
                            if parsed:
                                job['date_posted'] = text
                                break
                    
                    # Extract other fields
                    for text in cell_texts:
                        if len(text) < 2 or len(text) > 500:
                            continue
                        
                        if text == job.get('date_posted'):
                            continue
                        
                        if 'title' not in job and self.is_likely_title(text):
                            job['title'] = text
                        
                        elif 'location' not in job and self.is_likely_location(text):
                            job['location'] = text
                        
                        elif 'work_model' not in job and text in ['Remote', 'Hybrid', 'On-site', 'Onsite', 'In-person']:
                            job['work_model'] = text
                        
                        elif 'salary' not in job and self.is_likely_salary(text):
                            job['salary'] = text
                        
                        elif 'company' not in job and self.is_likely_company(text):
                            job['company'] = text
                        
                        elif len(text) > 100 and 'qualifications' not in job:
                            job['qualifications'] = text
                        
                        text_lower = text.lower()
                        if 'new grad' in text_lower or 'entry level' in text_lower:
                            job['is_new_grad'] = 'Yes'
                        
                        if any(size in text for size in ['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+']):
                            if 'company_size' not in job:
                                job['company_size'] = text
                    
                    title = job.get('title', '')
                    if title and len(title) > 3 and title not in seen_titles:
                        date_posted = job.get('date_posted', '')
                        
                        # Apply time filter
                        if self.is_within_timeframe(date_posted):
                            seen_titles.add(title)
                            
                            # Convert to unified schema
                            unified_job = {
                                'job_id': job.get('row_id'),
                                'url': job.get('url'),
                                'title': job.get('title'),
                                'company': job.get('company'),
                                'location': job.get('location'),
                                'description': None,
                                'snippet': job.get('qualifications'),
                                'salary_min': None,
                                'salary_max': None,
                                'salary_text': job.get('salary'),
                                'job_type': None,
                                'work_model': job.get('work_model'),
                                'department': None,
                                'company_size': job.get('company_size'),
                                'qualifications': job.get('qualifications'),
                                'h1b_sponsored': None,
                                'is_new_grad': job.get('is_new_grad'),
                                'category': category,
                                'posted_date': date_posted,
                                'date_posted': date_posted,
                                'scraped_at': datetime.now().isoformat(),
                                'source': 'airtable',
                                'raw_json': {
                                    'original_row_data': job
                                }
                            }
                            
                            new_jobs.append(unified_job)
                    
                except:
                    continue
                    
        except Exception as e:
            pass
        
        return new_jobs
    
    def scrape_all_categories(self, specific_categories=None):
        """Scrape all categories in parallel
        
        Args:
            specific_categories: Optional list of category names to scrape. If None, scrapes all.
        """
        all_results = {}
        
        # Filter categories if specific ones requested
        if specific_categories:
            categories_to_scrape = {k: v for k, v in self.categories.items() if k in specific_categories}
        else:
            categories_to_scrape = self.categories
        
        try:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"🚀 COMPREHENSIVE AIRTABLE SCRAPER")
            logger.info(f"{'=' * 80}")
            logger.info(f"\n📊 Total categories: {len(categories_to_scrape)}")
            logger.info(f"🧵 Parallel workers: {self.num_workers}")
            logger.info(f"📅 Time window: Last {self.hours_lookback} hours ({self.hours_lookback/24:.1f} days)")
            logger.info(f"⏱️  Estimated time: {len(categories_to_scrape) // self.num_workers * 3} minutes")
            logger.info(f"\n{'=' * 80}\n")
            
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = {}
                for idx, (category_name, url) in enumerate(categories_to_scrape.items(), 1):
                    future = executor.submit(self.scrape_category_comprehensive, category_name, url, idx, len(categories_to_scrape))
                    futures[future] = category_name
                
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
                            'url': categories_to_scrape[category_name],
                            'job_count': 0,
                            'jobs': [],
                            'status': 'failed',
                            'error': str(e)[:200]
                        }
            
            self.save_outputs(all_results)
            self.print_summary(all_results)
            
        except KeyboardInterrupt:
            logger.warning("\n\n⚠️  Interrupted by user")
            self.save_outputs(all_results)
            self.print_summary(all_results)
        except Exception as e:
            logger.error(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        
        return all_results
    
    def save_outputs(self, all_results):
        """Save consolidated outputs"""
        folder = "data/scraped"
        os.makedirs(folder, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save clean JSON (jobs only - no metadata)
        json_file = os.path.join(folder, f"airtable_all_{self.hours_lookback}h_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_jobs, f, indent=2, ensure_ascii=False)
        logger.info(f"\n📦 JSON saved: {json_file}")
        
        # Save metadata separately
        metadata_file = os.path.join(folder, f"airtable_all_{self.hours_lookback}h_{timestamp}_metadata.json")
        category_breakdown = {}
        for cat_name, result in all_results.items():
            category_breakdown[cat_name] = {
                'job_count': result.get('job_count', 0),
                'status': result.get('status', 'unknown')
            }
        
        metadata = {
            'scraped_at': datetime.now().isoformat(),
            'cutoff_date': self.cutoff_date.isoformat(),
            'time_range_hours': self.hours_lookback,
            'total_jobs': len(self.all_jobs),
            'total_categories': len(all_results),
            'successful_categories': len([r for r in all_results.values() if r.get('status') == 'success']),
            'failed_categories': len([r for r in all_results.values() if r.get('status') == 'failed']),
            'category_breakdown': category_breakdown
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"📦 Metadata saved: {metadata_file}")
        
        # CSV
        csv_file = os.path.join(folder, f"airtable_all_{self.hours_lookback}h_{timestamp}.csv")
        
        if self.all_jobs:
            keys = ['category', 'title', 'company', 'location', 'work_model', 'salary_text', 
                    'date_posted', 'company_size', 'h1b_sponsored', 'is_new_grad', 
                    'qualifications', 'url']
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.all_jobs)
            
            logger.info(f"📦 CSV saved: {csv_file}")
        
        # Markdown
        md_file = os.path.join(folder, f"airtable_all_{self.hours_lookback}h_{timestamp}.md")
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Airtable Comprehensive Job Scrape\n\n")
            f.write(f"**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Time Range:** Last {self.hours_lookback} hours ({self.hours_lookback/24:.1f} days)\n\n")
            f.write(f"**Total Jobs:** {len(self.all_jobs)}\n\n")
            f.write("---\n\n")
            
            jobs_by_category = {}
            for job in self.all_jobs:
                cat = job.get('category', 'Unknown')
                if cat not in jobs_by_category:
                    jobs_by_category[cat] = []
                jobs_by_category[cat].append(job)
            
            f.write("## Jobs by Category\n\n")
            for cat in sorted(jobs_by_category.keys()):
                count = len(jobs_by_category[cat])
                f.write(f"- {cat}: **{count}** jobs\n")
        
        logger.info(f"📦 Markdown saved: {md_file}")
        logger.info(f"\n✅ All files saved in: {folder}/")
    
    def print_summary(self, all_results):
        """Print final summary"""
        logger.info(f"\n{'=' * 80}")
        logger.info("📊 FINAL SUMMARY")
        logger.info(f"{'=' * 80}")
        
        total_jobs = sum(r.get('job_count', 0) for r in all_results.values())
        successful = sum(1 for r in all_results.values() if r.get('status') == 'success')
        
        logger.info(f"\n✅ Successfully scraped: {successful}/{len(all_results)} categories")
        logger.info(f"📈 Total jobs found: {total_jobs}")
        logger.info(f"📅 Time window: Last {self.hours_lookback} hours ({self.hours_lookback/24:.1f} days)")
        
        categories_with_jobs = [(k, v['job_count']) for k, v in all_results.items() if v.get('job_count', 0) > 0]
        if categories_with_jobs:
            logger.info(f"\n🎯 Top categories:")
            for cat, count in sorted(categories_with_jobs, key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"   ✅ {cat.replace('_', ' ')}: {count} jobs")


if __name__ == "__main__":
    print("=" * 80)
    print(" " * 15 + "COMPREHENSIVE AIRTABLE SCRAPER")
    print(" " * 10 + "(Individually scrapes ALL Airtable categories)")
    print("=" * 80)
    
    print("\n⚙️  Time Range Options:")
    print("1. Last 48 hours")
    print("2. Last 7 days (168 hours)")
    print("3. Last 14 days (336 hours)")
    print("4. Last 30 days (720 hours) [RECOMMENDED]")
    print("5. Custom hours")
    
    choice = input("\nEnter your choice (1-5) [default: 4]: ").strip() or "4"
    
    hours_map = {
        "1": 48,
        "2": 168,
        "3": 336,
        "4": 720
    }
    
    if choice == "5":
        hours_lookback = int(input("Enter custom hours: "))
    else:
        hours_lookback = hours_map.get(choice, 720)
    
    num_workers = input("\n🔧 Parallel workers (1-8) [default: 5]: ").strip()
    num_workers = int(num_workers) if num_workers and num_workers.isdigit() else 5
    num_workers = max(1, min(8, num_workers))
    
    print(f"\n🎯 Configuration:")
    print(f"   Time window: Last {hours_lookback} hours ({hours_lookback/24:.1f} days)")
    print(f"   Categories: {len(ComprehensiveAirtableScraper().categories)}")
    print(f"   Workers: {num_workers}")
    print(f"   Output: data/scraped/")
    print(f"\n⏱️  Estimated time: {len(ComprehensiveAirtableScraper().categories) // num_workers * 3} minutes\n")
    
    input("Press Enter to start scraping...")
    
    scraper = ComprehensiveAirtableScraper(hours_lookback=hours_lookback, num_workers=num_workers)
    results = scraper.scrape_all_categories()
    
    print("\n" + "=" * 80)
    print("🎉 SCRAPING COMPLETED!")
    print("=" * 80)
    print(f"\n📁 Files saved in: data/scraped/")
    print(f"📊 Total jobs: {sum(r.get('job_count', 0) for r in results.values())}")
