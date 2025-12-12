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
from webdriver_manager.chrome import ChromeDriverManager
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

class InternshipAirtableScraper:
    def __init__(self, hours_lookback=720, max_retries=3, num_workers=5):
        """
        Internship Airtable scraper for intern-list.com categories
        Args:
            hours_lookback: Number of hours to look back for jobs (default: 720 = 30 days)
            max_retries: Maximum retries for failed categories (default: 3)
            num_workers: Number of parallel workers (default: 5)
        """
        self.num_workers = num_workers
        self.lock = threading.Lock()
        
        # ALL INTERNSHIP AIRTABLE CATEGORIES from intern-list.com
        self.categories = {
            'Software_Engineering': 'https://airtable.com/app17F0kkWQZhC6HB/shrOTtndhc6HSgnYb/tblp8wxvfYam5sD04?viewControls=on',
            'Data_Analysis': 'https://airtable.com/appbsiP1flCoaXCSm/shreRS1cFLbduwBaU/tblrEk9sQX3yAx8Ag?viewControls=on',
            'Machine_Learning_AI': 'https://airtable.com/appjSXAWiVF4d1HoZ/shrf04yGbrK3IebAl/tbl7UBhvwqng6GRGZ?viewControls=on',
            'Product_Management': 'https://airtable.com/apprzZO4NFGouLji9/shrApQMVthWyRpdyu/tbliz003oxUdlGZHt?viewControls=on',
            'Accounting_Finance': 'https://airtable.com/appLzkCIXi5t8aYf4/shrIEKOHYPMwmpheG/tbl2DLQU5z2difWpo?viewControls=on',
            'Engineering_Development': 'https://airtable.com/appmXHK6JoqQcSKf6/shruwVkAKPjHFdVJu/tbl0U5gfpdphUO2KF?viewControls=on',
            'Business_Analyst': 'https://airtable.com/appFuMULJB6cXtL6L/shrabXspvMx1kfuQw/tblWaxQOcYrDJYZzn?viewControls=on',
            'Marketing': 'https://airtable.com/app6VTnxj2BsmftlM/shrbDWZK8D73K9RAQ/tbls7oRDgGYLz0IAX?viewControls=on',
            'Cybersecurity': 'https://airtable.com/appVWWidEOaCW7Biy/shrC0SNKnwMV3Fem9/tblsnzx5JszyejGd3?viewControls=on',
            'Consulting': 'https://airtable.com/appvVpV9JOUFrdDyu/shrPvpTT69P8fVy6H/tbl3gqgBQs9Xi2Ydn?viewControls=on',
            'Creatives_Design': 'https://airtable.com/appTrsSSLTPwEjG9Q/shrMZcqheJOCdXyQj/tblGekeEX8WABgLA3?viewControls=on',
            'Management_Executive': 'https://airtable.com/appujVcsLuXB2JFop/shrhyPUWuX0p9pWYs/tbldErF19CL1rLaDK?viewControls=on',
            'Public_Sector_Government': 'https://airtable.com/appcUSsKv3NZC0Tw3/shrimGkP5RvvFnSAU/tblENYq2qeJFbT17u?viewControls=on',
            'Legal_Compliance': 'https://airtable.com/appKXf9Bymafe61XI/shr6vQAB8tHZNsiEU/tblysbiJ3VUNpGme0?viewControls=on',
            'Human_Resources': 'https://airtable.com/appyGF0pekIR0p4qJ/shrxhUrCtEmdmGnVY/tblWywQzTMq6E3nuJ?viewControls=on',
            'Arts_Entertainment': 'https://airtable.com/appwi3tCBl9ZLUND8/shrxC4JFy2nGtoLmP/tblc6nD1S6fXOgzqK?viewControls=on',
            'Sales': 'https://airtable.com/appyCGJ9D68yZv0jE/shrT1cwFFOHJ1bAHO/tblo4H9W2sTKWnK4t?viewControls=on',
            'Customer_Service_Support': 'https://airtable.com/apppgR3v0Son1CSSy/shrnsOz4FDwhfDyM0/tblmGgpHlshxQkqR6?viewControls=on',
            'Education_Training': 'https://airtable.com/appvZ0ygFft9DK7Bc/shrAym7bN1r0rvyUi/tbl8cdtliF3qebQSi?viewControls=on',
            'Healthcare': 'https://airtable.com/appjLKAydm1GYAZJO/shr6jzdb5NNtjOejW/tblW0G4vxuMaYcl1d?viewControls=on'
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
        
        # Check if it's a location first - locations are NOT companies
        if self.is_likely_location(text):
            return False
        
        exclude = ['apply', 'remote', 'hybrid', 'on-site', 'onsite', 'on site', 'international']
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
    
    def scroll_horizontally(self, driver):
        """Scroll the Airtable table horizontally to load all columns"""
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
    
    def perform_scroll(self, driver):
        """Perform vertical scrolling"""
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
    
    def extract_visible_jobs(self, driver, seen_titles, category=None):
        """Extract jobs from visible Airtable rows"""
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
                        
                        elif 'company' not in job and self.is_likely_company(text) and len(text) < 60:
                            job['company'] = text
                        
                        elif len(text) > 100 and 'qualifications' not in job:
                            job['qualifications'] = text
                    
                    title = job.get('title', '')
                    if title and len(title) > 3 and title not in seen_titles:
                        date_posted = job.get('date_posted', '')
                        
                        # Accept jobs with NO date OR within timeframe
                        if not date_posted or self.is_within_timeframe(date_posted):
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
                                'job_type': 'Internship',
                                'work_model': job.get('work_model') or None,
                                'department': None,
                                'company_size': None,
                                'qualifications': job.get('qualifications') or None,
                                'h1b_sponsored': None,
                                'is_new_grad': None,
                                'category': category,
                                'posted_date': date_posted or None,
                                'scraped_at': datetime.now().isoformat(),
                                'source': 'intern-list.com (Airtable)',
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
    
    def extract_all_jobs_from_category(self, driver, category):
        """Extract jobs from category with deep scrolling (100 attempts)"""
        jobs = []
        date_samples = []
        seen_titles = set()
        no_new_data_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 100
        old_jobs_in_a_row = 0
        max_old_jobs = 20
        
        while no_new_data_count < 5 and scroll_attempts < max_scroll_attempts and old_jobs_in_a_row < max_old_jobs:
            with self.lock:
                logger.info(f"\n  → Scroll attempt {scroll_attempts + 1} | Recent internships: {len(jobs)}")
            
            time.sleep(2)
            
            new_jobs, old_job_count, new_date_samples = self.extract_visible_jobs(driver, seen_titles, category)
            jobs.extend(new_jobs)
            date_samples.extend(new_date_samples)
            
            if new_jobs:
                with self.lock:
                    logger.info(f"  ✓ Found {len(new_jobs)} internships from timeframe")
                no_new_data_count = 0
                old_jobs_in_a_row = 0
            else:
                no_new_data_count += 1
                with self.lock:
                    logger.info(f"  ⚠️  No new recent internships (attempt {no_new_data_count}/5)")
            
            if old_job_count > 0 and len(new_jobs) == 0:
                old_jobs_in_a_row += old_job_count
                with self.lock:
                    logger.info(f"  ⏱️  Seeing older internships... ({old_jobs_in_a_row}/{max_old_jobs} old jobs)")
            
            if old_jobs_in_a_row >= max_old_jobs:
                with self.lock:
                    logger.info(f"\n  🏁 Reached internships older than {self.hours_lookback} hours - stopping")
                break
            
            self.perform_scroll(driver)
            scroll_attempts += 1
        
        return jobs
    
    def scrape_category_comprehensive(self, category_name, url, idx, total):
        """Comprehensively scrape a single internship category - each worker gets its own driver"""
        driver = None
        
        try:  # CRITICAL: Outer try for finally cleanup
            for attempt in range(1, self.max_retries + 1):
                try:
                    with self.lock:
                        logger.info(f"\n{'=' * 80}")
                        logger.info(f"📂 INTERNSHIP CATEGORY {idx}/{total}: {category_name.replace('_', ' ')}")
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
                        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
                        chrome_options.add_argument('--disable-images')
                        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                        chrome_options.add_experimental_option('useAutomationExtension', False)
                        chrome_options.add_experimental_option("prefs", {
                            "profile.managed_default_content_settings.images": 2
                        })
                        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                        chrome_options.page_load_strategy = 'eager'
                        
                        # Check if running in Composer/Airflow (no Selenium Grid available)
                        selenium_url = os.getenv('SELENIUM_REMOTE_URL', '')
                        use_remote = selenium_url and 'selenium' in selenium_url.lower()
                        
                        if use_remote:
                            # Docker environment with Selenium Grid
                            with self.lock:
                                logger.info(f"🌐 Using Selenium Grid at {selenium_url}")
                            max_connection_retries = 3
                            for retry in range(max_connection_retries):
                                try:
                                    driver = webdriver.Remote(command_executor=selenium_url, options=chrome_options)
                                    with self.lock:
                                        logger.info("✓ Chrome driver initialized (Grid)")
                                    break
                                except Exception as e:
                                    if retry < max_connection_retries - 1:
                                        wait_time = (retry + 1) * 5
                                        with self.lock:
                                            logger.warning(f"⚠️  Failed to connect to Selenium Grid (attempt {retry + 1}/{max_connection_retries}): {str(e)}")
                                            logger.info(f"⏳ Retrying in {wait_time} seconds...")
                                        time.sleep(wait_time)
                                    else:
                                        with self.lock:
                                            logger.error(f"❌ Failed to connect to Selenium Grid after {max_connection_retries} attempts")
                                        raise
                        else:
                            # Composer/Airflow - use chromedriver-binary package
                            with self.lock:
                                logger.info("💻 Using chromedriver-binary package (Composer/Airflow mode)")
                            # chromedriver-binary package includes the driver - just import to add to PATH
                            import chromedriver_binary
                            driver = webdriver.Chrome(options=chrome_options)
                            with self.lock:
                                logger.info("✓ Chrome driver initialized from chromedriver-binary package")
                    
                    # Set page load timeout to prevent infinite hangs
                    driver.set_page_load_timeout(120)  # 2 minutes max for page load
                    
                    with self.lock:
                        logger.info(f"\n🌐 Loading {url}...")
                    driver.get(url)
                    
                    with self.lock:
                        logger.info("⏳ Waiting for Airtable to load...")
                    
                    # Wait for Airtable to fully render the data rows (reduced timeout)
                    try:
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.dataRow[data-rowid]'))
                        )
                        with self.lock:
                            logger.info("✓ Table rows detected")
                        time.sleep(5)  # Brief wait for stabilization
                    except TimeoutException:
                        with self.lock:
                            logger.warning("⚠️  Timeout waiting for dataRow elements - using fallback wait...")
                        time.sleep(15)  # Shorter fallback
                    
                    with self.lock:
                        logger.info("\n🔄 Scrolling horizontally to load all columns...")
                    self.scroll_horizontally(driver)
                    
                    cutoff_str = self.cutoff_date.strftime('%Y-%m-%d %H:%M')
                    with self.lock:
                        logger.info(f"\n📜 Extracting internships posted after {cutoff_str}...")
                        logger.info(f"   (Last {self.hours_lookback} hours / {self.hours_lookback/24:.1f} days)")
                    
                    jobs = self.extract_all_jobs_from_category(driver, category_name)
                    
                    with self.lock:
                        logger.info(f"\n✅ Extracted {len(jobs)} internships from {category_name}")
                    
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
                        except Exception:
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
                            except Exception:
                                pass
                        driver = None
                    else:
                        with self.lock:
                            logger.error(f"✗ Failed after {self.max_retries} attempts")
                            self.failed_categories.append(category_name)
                        if driver:
                            try:
                                driver.quit()
                            except Exception:
                                pass
                        return {
                            'url': url,
                            'job_count': 0,
                            'jobs': [],
                            'status': 'failed',
                            'error': str(e)[:200]
                        }
            
            # If we exhaust retries
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            
            return {
                'url': url,
                'job_count': 0,
                'jobs': [],
                'status': 'failed',
                'error': 'Max retries exceeded'
            }
        finally:  # CRITICAL: Always cleanup driver
            if driver:
                try:
                    driver.quit()
                    with self.lock:
                        logger.info(f"  🔌 Cleaned up driver for {category_name}")
                except Exception as e:
                    with self.lock:
                        logger.warning(f"  ⚠️  Driver cleanup warning: {str(e)[:50]}")
    
    def scrape_all_categories(self, specific_categories=None):
        """Scrape all internship categories in parallel"""
        all_results = {}
        
        try:
            categories_to_scrape = specific_categories if specific_categories else list(self.categories.keys())
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"🚀 Starting parallel internship scraping with {self.num_workers} workers")
            logger.info(f"📊 Scanning {len(categories_to_scrape)} internship categories")
            logger.info(f"{'=' * 80}")
            
            # Parallel execution
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = {}
                for idx, category_name in enumerate(categories_to_scrape, 1):
                    if category_name not in self.categories:
                        logger.warning(f"⚠️  Category '{category_name}' not found. Skipping...")
                        continue
                    
                    url = self.categories[category_name]
                    future = executor.submit(self.scrape_category_comprehensive, category_name, url, idx, len(categories_to_scrape))
                    futures[future] = category_name
                
                for future in as_completed(futures):
                    category_name = futures[future]
                    try:
                        result = future.result()
                        all_results[category_name] = result
                    except Exception as e:
                        logger.error(f"❌ Category {category_name} raised exception: {e}")
                        all_results[category_name] = {
                            'url': self.categories.get(category_name, ''),
                            'job_count': 0,
                            'jobs': [],
                            'status': 'failed',
                            'error': str(e)[:200]
                        }
            
            # Save results
            self.save_results(all_results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Fatal error in scrape_all_categories: {e}")
            return all_results
    
    def save_results(self, all_results):
        """Save scraped internships to files"""
        os.makedirs('/tmp/scraped_jobs', exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        hours = self.hours_lookback
        base_filename = f"internships_all_{hours}h_{timestamp}"
        
        json_file = f"/tmp/scraped_jobs/{base_filename}.json"
        metadata_file = f"/tmp/scraped_jobs/{base_filename}_metadata.json"
        csv_file = f"/tmp/scraped_jobs/{base_filename}.csv"
        md_file = f"/tmp/scraped_jobs/{base_filename}.md"
        
        # Save clean JSON (jobs only - no metadata)
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_jobs, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✅ Saved {len(self.all_jobs)} internships to {json_file}")
        
        # Save metadata separately
        metadata = {
            'scraped_at': datetime.now().isoformat(),
            'cutoff_date': self.cutoff_date.isoformat(),
            'time_range_hours': self.hours_lookback,
            'total_jobs': len(self.all_jobs),
            'total_categories': len(self.categories),
            'successful_categories': len([r for r in all_results.values() if r.get('status') == 'success']),
            'failed_categories': len([r for r in all_results.values() if r.get('status') == 'failed']),
            'category_breakdown': {cat: result.get('job_count', 0) for cat, result in all_results.items()}
        }
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved metadata to {metadata_file}")
        
        # Save CSV
        if self.all_jobs:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.all_jobs[0].keys())
                writer.writeheader()
                writer.writerows(self.all_jobs)
            logger.info(f"✅ Saved CSV to {csv_file}")
        
        # Save Markdown summary
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# Internship Scraping Summary\n\n")
            f.write(f"**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Time Range:** Last {self.hours_lookback} hours ({self.hours_lookback/24:.1f} days)\n\n")
            f.write(f"**Total Internships:** {len(self.all_jobs)}\n\n")
            f.write(f"**Categories Scraped:** {len(self.categories)}\n\n")
            
            f.write("## Breakdown by Category\n\n")
            for category_name, result in sorted(all_results.items()):
                count = result.get('job_count', 0)
                status = result.get('status', 'unknown')
                icon = "✅" if status == 'success' else "❌"
                f.write(f"- {icon} **{category_name.replace('_', ' ')}**: {count} internships\n")
        
        logger.info(f"✅ Saved summary to {md_file}")


if __name__ == "__main__":
    # For testing
    scraper = InternshipAirtableScraper(hours_lookback=720, num_workers=5)
    results = scraper.scrape_all_categories()
    
    total = sum(r.get('job_count', 0) for r in results.values())
    print(f"\n{'=' * 80}")
    print(f"COMPLETED: {total} internships scraped from {len(results)} categories")
    print(f"{'=' * 80}")
