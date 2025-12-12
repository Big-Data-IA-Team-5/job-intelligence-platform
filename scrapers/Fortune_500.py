"""
================================================================================
  ULTRA-SMART JOB CRAWLER V2 - HYBRID SELENIUM + HTTP
  Student: Pranav Patel | DAMG 7245
  TARGET: 70-80% SUCCESS RATE
================================================================================
  ENHANCED STRATEGY:
  1. Smart detection of JavaScript-heavy sites → use Selenium
  2. HTTP for simple sites (fast)
  3. Selenium for complex sites (Amazon, Google, Meta, Tesla, etc.)
  4. Better rate limiting with exponential backoff
  5. Enhanced error tracking and failure reasons
  6. Rotating user agents
  7. API endpoint detection
  8. JobSpy fallback for stubborn cases
================================================================================
"""

import json
import time
import os
import csv
from datetime import datetime
import re
import random
from io import StringIO
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import pandas as pd

# Selenium import for JavaScript-heavy sites
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
    print("✅ Selenium available - JavaScript rendering enabled")
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not installed")

# JobSpy import for fallback
try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    print("⚠️ JobSpy not installed - fallback scraping disabled. Install with: pip install python-jobspy")

# ============================================================================
# CONFIGURATION
# ============================================================================

def load_secrets():
    """Load secrets from secrets.json"""
    secrets_path = os.path.join(os.path.dirname(__file__), '../secrets.json')
    if not os.path.exists(secrets_path):
        raise FileNotFoundError(f"secrets.json not found at {secrets_path}")
    with open(secrets_path, 'r') as f:
        return json.load(f)

# Load API keys from secrets
try:
    _secrets = load_secrets()
    OPENAI_API_KEY = _secrets['api']['openai_api_key']
    SCRAPERAPI_KEY = None
except Exception as e:
    print(f"⚠️ Warning: Could not load secrets.json: {e}")
    OPENAI_API_KEY = None
    SCRAPERAPI_KEY = None

MAX_COMPANIES = None  # Run all companies
NUM_WORKERS = 16  # Increased from 8 to 16 - FASTER for 500 companies!
NUM_SELENIUM_WORKERS = 2  # Increased from 1 to 2 for more JS sites
REQUEST_DELAY = (1, 3)  # Reduced from (3,6) to (1,3) - faster HTTP requests
SELENIUM_DELAY = (5, 8)  # Reduced from (10,15) to (5,8) - faster page loads
CHECKPOINT_EVERY = 10  # Increased from 5 to 10 - less I/O
SELENIUM_TIMEOUT = 30  # Reduced from 40 to 30 - faster timeouts
MAX_RETRIES = 1  # Keep at 1 for speed
MAX_SELENIUM_RETRIES = 1  # Keep at 1 for speed

# Companies known to need Selenium (JavaScript-heavy)
JS_HEAVY_COMPANIES = {
    'amazon', 'alphabet', 'google', 'meta', 'facebook', 'tesla', 'oracle',
    'intel', 'ibm', 'salesforce', 'netflix', 'uber', 'airbnb',
    'goldman sachs', 'morgan stanley', 'wells fargo', 'citigroup',
    'bank of america', 'jpmorgan', 'capital one', 'american express',
    'boeing', 'general motors', 'ford', 'caterpillar', 'deere',
    'kroger', "lowe's", 'best buy', 'tjx', 'progressive', 'allstate',
    'marriott', 'delta', 'united', 'american airlines', 'fedex', 'ups',
    'at&t', 'verizon', 'charter', 'cigna', 'centene', 'hca', 'merck'
}

# Common job URL patterns to try as fallback
COMMON_JOB_URL_PATTERNS = [
    '/search-jobs',
    '/job-search',
    '/careers/search',
    '/careers/jobs',
    '/jobs/search',
    '/opportunities',
    '/search-results',
    '/openings',
    '/careers/job-search',
    '/en/jobs',
    '/en-us/jobs',
    '/wd/search',
    '/wd/jobs',
    '/ux/careers/jobs',
    '/ccx/careers/',
    '/gh/',
    '/gh/jobs',
    '/greenhouse',
    '/lever/',
    '/lever/jobs',
    '/jobs',
    '/careers/search'
]

print(f"\n{'='*80}")
print(f"🚀 ULTRA-SMART JOB CRAWLER V2 - HYBRID MODE")
print(f"{'='*80}")
print(f"✅ Workers: {NUM_WORKERS}")
print(f"✅ Selenium: {'ENABLED' if SELENIUM_AVAILABLE else 'DISABLED'}")
print(f"✅ JobSpy Fallback: {'ENABLED' if JOBSPY_AVAILABLE else 'DISABLED'}")
print(f"✅ Max Retries: {MAX_RETRIES}")
print(f"✅ JS-Heavy Companies Tracked: {len(JS_HEAVY_COMPANIES)}")
print(f"{'='*80}\n")

# ============================================================================
# SMART LINK FINDER
# ============================================================================

class SmartLinkFinder:
    """Intelligently finds job listing pages"""
    
    def __init__(self, openai_key: str):
        self.client = OpenAI(api_key=openai_key)
    
    def find_best_job_links(self, html: str, base_url: str, company: str) -> List[str]:
        """
        Extract ALL links and ask GPT which ones likely have jobs
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract all links with their text
        all_links = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            text = a.get_text(strip=True)
            
            # Skip empty or too long text
            if not text or len(text) > 100:
                continue
            
            # Make absolute URL
            full_url = urljoin(base_url, href)
            
            # Skip non-http links
            if not full_url.startswith('http'):
                continue
            
            # Keep same domain only
            if urlparse(full_url).netloc != urlparse(base_url).netloc:
                continue
            
            all_links.append({
                'text': text,
                'url': full_url
            })
        
        # Remove duplicates
        seen = set()
        unique_links = []
        for link in all_links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique_links.append(link)
        
        if len(unique_links) == 0:
            return []
        
        # Ask GPT to pick the best ones
        print(f"   Found {len(unique_links)} links total")
        
        # Take first 200 links for GPT analysis
        links_sample = unique_links[:200]
        links_text = "\n".join([f"{i+1}. {l['text']}: {l['url']}" 
                                for i, l in enumerate(links_sample)])
        
        prompt = f"""You are an expert at navigating company career websites to find where ACTUAL JOB POSTINGS are listed.

Company: {company}

Your mission: Find the URL(s) that will show a PAGE WITH A LIST/GRID OF REAL JOB OPENINGS (like search results or a job browser with multiple positions).

⚠️ CRITICAL SPECIAL CASES:

1. AMAZON/API-BASED SITES:
If the domain is amazon.jobs, jobs.amazondelivers.jobs, hiring.amazon.com, or other API-driven career sites:

❌ DO NOT RETURN these (they load jobs via API, not HTML):
- /en
- /en/locations
- /en/job_categories
- /en/business_categories
- /en/search?keywords=something
- Any page path without .json or /api/

✅ ONLY RETURN API endpoints if visible:
- /en/search.json?country=USA
- /search.json?base_query=&loc_query=USA
- /api/jobs?location=US
- Any URL ending in .json or containing /api/

If no API endpoint is found for these sites, return [].

2. CATEGORY/DEPARTMENT PAGES (CRITICAL - NEVER RETURN THESE):
❌ DO NOT RETURN URLs containing:
- /category/ (e.g., /category/data-science-jobs)
- /categories/
- /departments/
- /teams/
- /areas/
- /job-families/
- /disciplines/
- /business-units/

These are NOT job listing pages - they require clicking again to see actual jobs.
They are navigation/filter pages, not search results.

Example of what NOT to return:
- jobs.dell.com/category/engineering-jobs/...
- careers.company.com/departments/software
- jobs.company.com/job-families/technology

These pages do NOT show job cards directly - they only show categories to click.

🎯 PERFECT URLs (HIGHEST PRIORITY - these DIRECTLY SHOW job listings):
- Link text: "Search Jobs", "Job Search", "Find Jobs", "Browse Jobs"
- Link text: "View All Jobs", "All Openings", "See All Positions"
- Link text: "Explore Opportunities", "Open Positions", "Current Openings"
- URL patterns: /search, /jobs, /search-jobs, /job-search, /careers/search, /openings, /opportunities, /search-results
- URLs with query params: ?q=, ?search=, ?keyword=, ?location=
- Anything that explicitly says it will SEARCH or SHOW jobs
- Pages that load a grid/list of job cards directly

⚠️ URL patterns that are ACCEPTABLE (NOT category pages):
- /search-jobs (shows results)
- /jobs (if it shows list of jobs)
- /job-search?query=
- /search-results
- /openings
- /opportunities (if it's a job list)

✅ GOOD URLs (may show job lists):
- "Software Jobs", "Engineering Positions" → if they list multiple jobs
- "Career Opportunities" → if it's a searchable job page
- "Join Our Team" → only if URL suggests job listings (/jobs, /search)

❌ BAD URLs (DO NOT INCLUDE - these are info pages, not job listings):
- "About Us", "Why Work Here", "Our Story", "Company Culture"
- "Benefits", "Perks", "What We Offer", "Employee Benefits"
- "Diversity", "Inclusion", "Values", "Mission"
- "Locations", "Offices", "Our Teams", "Departments" (unless URL has /jobs)
- "News", "Blog", "Events", "FAQs", "Contact"
- "Students", "University", "Internships" (unless it's a job search for these)
- Individual team pages like "Engineering Team" or "Life at [Company]"
- Career landing/home pages that just have marketing content

Available links from the page:
{links_text}

Critical thinking: Ask yourself "If I click this link, will I see a list of individual job titles with locations?"

Return a JSON array of the top 5-10 URLs most likely to show ACTUAL JOB LISTINGS:
["url1", "url2", "url3"]

Prioritize URLs with explicit job search functionality. Return multiple URLs to maximize chances.
If no clear job listing URLs exist, try returning the most promising career-related URLs as fallback."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Pick URLs that lead to job listings. Return only JSON array of URLs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            result = response.choices[0].message.content.strip()
            result = re.sub(r'^```json\s*|\s*```$', '', result).strip()
            
            urls = json.loads(result)
            
            if isinstance(urls, list):
                print(f"   ✓ GPT selected {len(urls)} promising links")
                return urls
            
        except Exception as e:
            print(f"   ⚠️ GPT analysis failed: {str(e)[:50]}")
        
        return []

# ============================================================================
# SMART JOB DETECTOR & EXTRACTOR
# ============================================================================

class SmartJobExtractor:
    """Detects and extracts jobs from any page with multiple extraction strategies"""
    
    def __init__(self, openai_key: str):
        self.client = OpenAI(api_key=openai_key)
    
    def extract_structured_data(self, html: str, company: str, url: str) -> List[Dict]:
        """
        Strategy 1: Extract jobs from JSON-LD structured data or meta tags
        Fast and accurate when available
        """
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Look for JSON-LD structured data (schema.org JobPosting)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                
                # Handle single JobPosting
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    job = self._parse_job_posting(data, company, url)
                    if job:
                        jobs.append(job)
                
                # Handle array of JobPostings
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            job = self._parse_job_posting(item, company, url)
                            if job:
                                jobs.append(job)
                
                # Handle nested in graph
                elif isinstance(data, dict) and '@graph' in data:
                    for item in data['@graph']:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            job = self._parse_job_posting(item, company, url)
                            if job:
                                jobs.append(job)
                
            except (json.JSONDecodeError, AttributeError):
                continue
        
        if jobs:
            print(f"       ✓ Structured data found: {len(jobs)} jobs from JSON-LD")
        
        return jobs
    
    def _parse_job_posting(self, data: dict, company: str, url: str) -> Optional[Dict]:
        """Parse a JobPosting schema.org object"""
        title = data.get('title') or data.get('name', '')
        if not title:
            return None
        
        # Extract location
        location = 'USA'
        job_location = data.get('jobLocation', {})
        if isinstance(job_location, dict):
            address = job_location.get('address', {})
            if isinstance(address, dict):
                city = address.get('addressLocality', '')
                state = address.get('addressRegion', '')
                location = f"{city}, {state}" if city and state else state or city or 'USA'
        elif isinstance(job_location, list) and len(job_location) > 0:
            address = job_location[0].get('address', {})
            if isinstance(address, dict):
                city = address.get('addressLocality', '')
                state = address.get('addressRegion', '')
                location = f"{city}, {state}" if city and state else state or city or 'USA'
        
        # Validate USA location
        location_lower = location.lower()
        excluded = ['canada', 'uk', 'united kingdom', 'india', 'china', 'singapore', 
                   'australia', 'germany', 'france', 'mexico', 'brazil', 'japan', 'europe']
        if any(ex in location_lower for ex in excluded):
            return None
        
        # Extract other fields
        job_url = data.get('url') or data.get('identifier', {}).get('value', url)
        job_type = data.get('employmentType', '')
        if isinstance(job_type, list):
            job_type = ', '.join(job_type)
        
        description = data.get('description', '')
        if len(description) > 500:
            description = description[:500]
        
        salary = ''
        if 'baseSalary' in data:
            salary_data = data['baseSalary']
            if isinstance(salary_data, dict):
                value = salary_data.get('value', {})
                if isinstance(value, dict):
                    min_val = value.get('minValue', '')
                    max_val = value.get('maxValue', '')
                    if min_val and max_val:
                        salary = f"${min_val}-${max_val}"
        
        posted_date = data.get('datePosted', '')
        
        return {
            'job_id': data.get('identifier', {}).get('value', '') if isinstance(data.get('identifier'), dict) else '',
            'title': title,
            'company': company,
            'location': location,
            'job_type': job_type,
            'department': data.get('hiringOrganization', {}).get('department', '') if isinstance(data.get('hiringOrganization'), dict) else '',
            'salary_range': salary,
            'description': description,
            'apply_url': job_url,
            'posted_date': posted_date,
            'source': 'fortune500_structured_data',
            'scraped_at': datetime.now().isoformat()
        }
    
    def extract_with_patterns(self, html: str, company: str, url: str) -> List[Dict]:
        """
        Strategy 2: Direct HTML parsing using common patterns
        Faster than GPT, works for common ATS systems
        """
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Common job card patterns across different ATS systems
        job_selectors = [
            # Workday
            {'class_': lambda x: x and 'job' in x.lower() and 'card' in x.lower()},
            {'class_': lambda x: x and 'position' in x.lower()},
            # Greenhouse
            {'data-qa': 'job-post'},
            {'class_': 'opening'},
            # Lever
            {'class_': 'posting'},
            # Generic
            {'class_': lambda x: x and 'job-listing' in x.lower()},
            {'class_': lambda x: x and 'job-item' in x.lower()},
            {'itemtype': 'http://schema.org/JobPosting'},
        ]
        
        job_elements = []
        for selector in job_selectors:
            elements = soup.find_all(['div', 'li', 'article', 'tr'], **selector, limit=100)
            job_elements.extend(elements)
        
        # Remove duplicates
        seen_texts = set()
        unique_elements = []
        for elem in job_elements:
            text = elem.get_text(strip=True)[:100]
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_elements.append(elem)
        
        print(f"       → Pattern matching found {len(unique_elements)} potential job elements")
        
        for elem in unique_elements[:50]:  # Limit to 50
            job = self._extract_job_from_element(elem, company, url)
            if job:
                jobs.append(job)
        
        if jobs:
            print(f"       ✓ Pattern extraction: {len(jobs)} jobs")
        
        return jobs
    
    def _extract_job_from_element(self, elem, company: str, base_url: str) -> Optional[Dict]:
        """Extract job data from a single HTML element"""
        # Find title
        title = ''
        title_tags = elem.find_all(['h2', 'h3', 'h4', 'a'], limit=5)
        for tag in title_tags:
            text = tag.get_text(strip=True)
            if text and len(text) > 10 and len(text) < 150:
                # Skip navigation text
                if not any(nav in text.lower() for nav in ['view all', 'back', 'next', 'filter', 'sort']):
                    title = text
                    break
        
        if not title:
            return None
        
        # Find location
        location = 'USA'
        location_indicators = ['location', 'office', 'city', 'region']
        for indicator in location_indicators:
            loc_elem = elem.find(class_=lambda x: x and indicator in x.lower())
            if loc_elem:
                location = loc_elem.get_text(strip=True)
                break
        
        # Validate USA location
        location_lower = location.lower()
        excluded = ['canada', 'uk', 'united kingdom', 'india', 'china', 'singapore',
                   'australia', 'germany', 'france', 'mexico', 'brazil', 'japan', 'europe']
        if any(ex in location_lower for ex in excluded):
            return None
        
        # Find URL
        job_url = base_url
        link = elem.find('a', href=True)
        if link:
            job_url = urljoin(base_url, link['href'])
        
        # Find job type
        job_type = ''
        type_elem = elem.find(class_=lambda x: x and any(t in x.lower() for t in ['type', 'employment']))
        if type_elem:
            job_type = type_elem.get_text(strip=True)
        
        # Find job ID using regex
        job_id = ''
        text = elem.get_text()
        id_patterns = [
            r'[Jj]ob\s*[IiDd#]+[\s:]*([A-Z0-9\-]+)',
            r'[Rr]eq(?:uisition)?[\s#:]*([A-Z0-9\-]+)',
            r'[IiDd]+[\s:]*([0-9]{5,})',
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text)
            if match:
                job_id = match.group(1)
                break
        
        return {
            'job_id': job_id,
            'title': title,
            'company': company,
            'location': location,
            'job_type': job_type,
            'department': '',
            'salary_range': '',
            'description': '',
            'apply_url': job_url,
            'posted_date': '',
            'source': 'fortune500_pattern_match',
            'scraped_at': datetime.now().isoformat()
        }
    
    def detect_api_endpoint(self, html: str, base_url: str) -> Optional[str]:
        """
        Strategy 3: Detect if page loads jobs via API
        Returns API endpoint URL if found
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for API calls in JavaScript
        scripts = soup.find_all('script')
        api_patterns = [
            r'["\']([^"\']*(?:api|search)[^"\']*\.json[^"\']*)["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.get\(["\']([^"\']+)["\']',
            r'["\']([^"\']*\/api\/jobs[^"\']*)["\']',
        ]
        
        for script in scripts:
            if script.string:
                for pattern in api_patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    for match in matches:
                        if 'job' in match.lower() or 'search' in match.lower():
                            api_url = urljoin(base_url, match)
                            print(f"       ✓ Detected API endpoint: {api_url[:80]}...")
                            return api_url
        
        # Check for common API URL patterns in page
        domain = urlparse(base_url).netloc
        common_api_patterns = [
            f"https://{domain}/api/jobs",
            f"https://{domain}/search.json",
            f"https://{domain}/en/search.json",
        ]
        
        for api_url in common_api_patterns:
            if api_url.lower() in html.lower():
                print(f"       ✓ Found API URL in HTML: {api_url}")
                return api_url
        
        return None
    
    def has_job_listings(self, html: str) -> bool:
        """Quick check if page has actual job listings with multiple postings"""
        text = html.lower()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for common ATS platforms
        if soup.select('[data-automation-id="jobTile"]'):  # Workday
            return True
        if soup.select('section.opening'):  # Greenhouse
            return True
        if soup.select('div.posting'):  # Lever
            return True
        
        # Strong indicators of job results page
        strong_signals = [
            ('showing' in text or 'displaying' in text or 'found' in text) and 'job' in text,
            text.count('apply') > 8 or text.count('apply now') > 5,
            text.count('job id') > 5 or text.count('req id') > 5 or text.count('requisition') > 5,
            'results' in text and 'job' in text,
        ]
        
        # Medium indicators
        medium_signals = [
            text.count('job title') > 3,
            text.count('location') > 10 and 'job' in text,
            'job openings' in text or 'current openings' in text or 'open positions' in text,
            'search results' in text or 'search jobs' in text,
        ]
        
        # Count job-like containers (less strict)
        job_containers = soup.find_all(['div', 'li', 'article', 'tr'], 
                                      class_=lambda x: x and any(keyword in str(x).lower() 
                                      for keyword in ['job', 'position', 'opening', 'result', 'listing', 'card', 'opportunity']))
        
        # Count apply buttons/links (more lenient)
        apply_buttons = len(soup.find_all(['a', 'button'], 
                                         text=lambda x: x and ('apply' in str(x).lower() or 'view' in str(x).lower())))
        
        # More lenient evidence - accept if any strong evidence OR combination of medium evidence
        has_very_strong = sum(strong_signals) >= 2
        has_strong_signal = sum(strong_signals) >= 1 and sum(medium_signals) >= 1
        has_many_jobs = len(job_containers) > 8  # Reduced from 10
        has_moderate_jobs = len(job_containers) > 3 and apply_buttons > 3  # More lenient
        has_medium_evidence = sum(medium_signals) >= 2 and len(job_containers) > 2
        
        return has_very_strong or has_strong_signal or has_many_jobs or has_moderate_jobs or has_medium_evidence
    
    def extract_job_urls(self, html: str, base_url: str) -> List[str]:
        """
        Extract individual job posting URLs from a job listing page
        """
        soup = BeautifulSoup(html, 'html.parser')
        job_urls = []
        base_domain = urlparse(base_url).netloc
        
        # Look for links that might be individual job postings
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            text = a.get_text(strip=True)
            
            if not href:
                continue
            
            # Make absolute URL
            full_url = urljoin(base_url, href)
            url_lower = full_url.lower()
            
            # Skip if different domain
            if urlparse(full_url).netloc != base_domain:
                continue
            
            # Skip if it's the same as base_url (listing page itself)
            if full_url.split('#')[0].split('?')[0] == base_url.split('#')[0].split('?')[0]:
                continue
            
            # Look for job-specific URL patterns - comprehensive list including Salesforce
            is_job_url = any(pattern in url_lower for pattern in [
                '/job/', '/jobs/', '/position/', '/opening/', '/career/', 
                '/requisition/', '/req/', 'jid=', 'jobid=', 'job_id=', 'id=',
                '/detail/', '/apply/', '/vacancy/', '/role/', '/posting/',
                '/opportunities/', '/jobdetails/', '/jobdetail/', '/careers/job',
                'jobid=', '/job-detail', '/job-details'  # Added for Salesforce
            ])
            
            # Additional check: if link text looks like a job title (longer text, not navigation)
            text_looks_like_job = len(text) > 20 and not any(nav in text.lower() for nav in [
                'search', 'filter', 'sort', 'view all', 'back', 'next', 'previous',
                'home', 'about', 'benefits', 'sign in', 'login', 'register', 'load more',
                'show more', 'page', 'clear', 'reset', 'apply now'
            ])
            
            # Exclude category/department pages (but allow if they contain job indicators)
            is_category_page = (
                any(cat in url_lower for cat in ['/teams/', '/departments/']) and
                not any(x in url_lower for x in ['opening', 'job', 'position'])
            )
            
            if (is_job_url or text_looks_like_job) and not is_category_page:
                job_urls.append(full_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in job_urls:
            # Clean URL (remove fragments)
            clean_url = url.split('#')[0]
            if clean_url not in seen:
                seen.add(clean_url)
                unique_urls.append(clean_url)
        
        return unique_urls[:50]  # Increased limit to 50 job URLs
    
    def extract_all_jobs(self, html: str, company: str, url: str) -> List[Dict]:
        """
        Extract ALL jobs from a page using multiple strategies:
        1. Structured data (JSON-LD) - fastest
        2. HTML patterns - fast
        3. GPT extraction - most flexible (fallback)
        """
        print(f"       → Trying multiple extraction strategies...")
        
        # Strategy 1: Structured data (JSON-LD)
        jobs = self.extract_structured_data(html, company, url)
        if jobs and len(jobs) >= 5:  # Good amount from structured data
            print(f"       ✅ Success with structured data: {len(jobs)} jobs")
            return jobs
        
        # Strategy 2: Pattern matching
        pattern_jobs = self.extract_with_patterns(html, company, url)
        if pattern_jobs and len(pattern_jobs) >= 5:  # Good amount from patterns
            print(f"       ✅ Success with pattern matching: {len(pattern_jobs)} jobs")
            return pattern_jobs
        
        # Combine small results from both strategies
        if jobs or pattern_jobs:
            combined = jobs + pattern_jobs
            # Deduplicate by title
            seen_titles = set()
            unique_jobs = []
            for job in combined:
                title_key = (job['title'].lower(), job['location'].lower())
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_jobs.append(job)
            
            if len(unique_jobs) >= 3:  # At least some jobs found
                print(f"       ✅ Combined strategies: {len(unique_jobs)} jobs")
                return unique_jobs
        
        # Strategy 3: GPT extraction (fallback - most flexible but slower)
        print(f"       → Falling back to GPT extraction...")
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove noise
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # ALSO extract all links for GPT to reference
        all_links = []
        for a in soup.find_all('a', href=True):
            href = urljoin(url, a.get('href', ''))
            link_text = a.get_text(strip=True)
            if link_text and len(link_text) > 10:
                all_links.append(f"{link_text} -> {href}")
        
        links_section = "\n".join(all_links[:100])  # First 100 links
        
        # Chunk if needed
        if len(text) > 60000:
            text = text[:60000]
        
        prompt = f"""Extract ALL job postings from this page. Be AGGRESSIVE - extract everything that looks like a job.

Company: {company}
Listing Page URL: {url}

CRITICAL: For each job, find its INDIVIDUAL job posting URL from the links below.

Available links on the page:
{links_section}

EXTRACT:
✓ ALL job types (intern, full-time, contract, part-time, etc.)
✓ ONLY USA locations (exclude Canada, UK, India, China, Europe, etc.)
✓ Software, engineering, data, tech roles AND business/operations roles
✓ Entry level, experienced, senior - ALL levels

For each job return:
{{
  "title": "exact job title",
  "location": "city, state OR Remote OR USA",
  "job_type": "Intern/Full-Time/Contract/etc if visible",
  "department": "if visible",
  "job_id": "if visible",
  "job_url": "INDIVIDUAL job posting URL - find the specific link for THIS job from the links above, NOT the listing page"
}}

Page content:
{text}

IMPORTANT: The job_url MUST be the individual job's detail page URL, NOT "{url}".
Look for patterns like /job/[id], /position/[id], or job-specific URLs in the links section.

Return JSON array with ALL USA jobs. If no individual URLs found, use the listing page URL.
If this is NOT a job listings page, return [].
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract ALL USA jobs with their INDIVIDUAL job URLs. Return JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=4000
            )
            
            result = response.choices[0].message.content.strip()
            result = re.sub(r'^```json\s*|\s*```$', '', result).strip()
            
            jobs_raw = json.loads(result)
            
            if not isinstance(jobs_raw, list):
                return []
            
            print(f"       GPT extracted {len(jobs_raw)} potential jobs")
            
            # Format jobs
            jobs = []
            for job in jobs_raw:
                if not isinstance(job, dict):
                    continue
                
                title = job.get('title', '')
                location = job.get('location', '')
                
                if not title:
                    continue
                
                # USA-only filtering - check location
                if location:
                    location_lower = location.lower()
                    
                    # Check for non-USA markers first
                    non_usa_markers = [
                        'canada', 'toronto', 'vancouver', 'ca ',
                        'united kingdom', 'uk', 'london',
                        'india', 'bangalore',
                        'germany', 'berlin',
                        'australia', 'sydney',
                        'singapore'
                    ]
                    if any(x in location_lower for x in non_usa_markers):
                        continue
                    
                    # Require USA markers for validation
                    usa_markers = [
                        'united states', 'usa', ', us', ' us',
                        'alabama','alaska','arizona','arkansas','california','colorado',
                        'connecticut','delaware','florida','georgia','hawaii','idaho',
                        'illinois','indiana','iowa','kansas','kentucky','louisiana',
                        'maine','maryland','massachusetts','michigan','minnesota',
                        'mississippi','missouri','montana','nebraska','nevada',
                        'new hampshire','new jersey','new mexico','new york',
                        'north carolina','north dakota','ohio','oklahoma','oregon',
                        'pennsylvania','rhode island','south carolina','south dakota',
                        'tennessee','texas','utah','vermont','virginia','washington',
                        'west virginia','wisconsin','wyoming','district of columbia',
                        'dc','d.c','remote'
                    ]
                    if not any(state in location_lower for state in usa_markers):
                        continue
                
                # Use individual job URL if found, otherwise fallback to listing page
                job_url = job.get('job_url', url)
                if not job_url or job_url == url or 'page=' in job_url or '#results' in job_url or '#content' in job_url:
                    job_url = url  # Fallback to listing page if no individual URL found
                    if job_url == url:
                        print(f"         ⚠️ No individual URL for: {title[:40]}...")
                
                jobs.append({
                    'job_id': job.get('job_id') or None,
                    'url': job_url,
                    'title': title,
                    'company': company,
                    'location': location or 'USA',
                    'description': job.get('description') or None,
                    'snippet': None,
                    'salary_min': None,
                    'salary_max': None,
                    'salary_text': job.get('salary_range') or None,
                    'job_type': job.get('job_type') or None,
                    'work_model': None,
                    'department': job.get('department') or None,
                    'company_size': None,
                    'qualifications': None,
                    'h1b_sponsored': None,
                    'is_new_grad': None,
                    'category': None,
                    'posted_date': None,
                    'scraped_at': datetime.now().isoformat(),
                    'source': 'fortune500',
                    'raw_json': {
                        'original_job_data': job
                    }
                })
            
            return jobs
            
        except Exception as e:
            print(f"       ⚠️ Extraction error: {str(e)[:80]}")
            return []

# ============================================================================
# ENHANCED FALLBACK CHAIN
# ============================================================================

class EnhancedFallbackChain:
    """5-layer fallback system to maximize job extraction success"""
    
    def __init__(self, scraper):
        self.scraper = scraper
        self.http = scraper.http
        self.job_extractor = scraper.job_extractor
    
    def try_all_fallbacks(self, company_name: str, career_url: str) -> List[Dict]:
        """Try all fallback strategies in order before giving up"""
        print(f"\n[ENHANCED FALLBACKS] Trying alternative strategies for {company_name}...")
        
        # FALLBACK 1: Common URL Patterns (0 cost, fast)
        print(f"\n[FALLBACK 1] Trying common URL patterns...")
        jobs = self.try_common_url_patterns(company_name, career_url)
        if jobs:
            print(f"   ✅ Common URL patterns found {len(jobs)} jobs!")
            return jobs
        
        # FALLBACK 2: Sitemap.xml (0 cost, fast)
        print(f"\n[FALLBACK 2] Checking sitemap.xml...")
        jobs = self.try_sitemap(company_name, career_url)
        if jobs:
            print(f"   ✅ Sitemap found {len(jobs)} jobs!")
            return jobs
        
        # FALLBACK 3: Deep Crawl (2-3 levels deep)
        print(f"\n[FALLBACK 3] Deep crawling 2-3 levels...")
        jobs = self.try_deep_crawl(company_name, career_url)
        if jobs:
            print(f"   ✅ Deep crawl found {len(jobs)} jobs!")
            return jobs
        
        # FALLBACK 4: Alternative Domains (jobs.company.com, hiring.company.com)
        print(f"\n[FALLBACK 4] Trying alternative job domains...")
        jobs = self.try_alternative_domains(company_name, career_url)
        if jobs:
            print(f"   ✅ Alternative domain found {len(jobs)} jobs!")
            return jobs
        
        # FALLBACK 5: Extended Selenium with Interactions (slower, but powerful)
        if SELENIUM_AVAILABLE and self.scraper.use_selenium:
            print(f"\n[FALLBACK 5] Extended Selenium with interactions...")
            jobs = self.try_extended_selenium(company_name, career_url)
            if jobs:
                print(f"   ✅ Extended Selenium found {len(jobs)} jobs!")
                return jobs
        
        print(f"   ⚠️  All fallbacks exhausted - no jobs found")
        return []
    
    def try_common_url_patterns(self, company_name: str, career_url: str) -> List[Dict]:
        """FALLBACK 1: Try predictable URL patterns"""
        base_url = career_url.rstrip('/')
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Common patterns to try
        patterns = [
            f"{base_url}/search",
            f"{base_url}/jobs",
            f"{base_url}/search-jobs",
            f"{base_url}/job-search",
            f"{base_url}/opportunities",
            f"{base_url}/openings",
            f"{base_url}/us",
            f"{base_url}/en",
            f"{base_url}/en-us",
            f"{domain}/careers/search",
            f"{domain}/careers/jobs",
            f"{domain}/careers/search-jobs",
            f"{domain}/jobs/search",
            f"{domain}/search-jobs",
        ]
        
        # Add patterns from COMMON_JOB_URL_PATTERNS
        for pattern in COMMON_JOB_URL_PATTERNS:
            patterns.append(f"{base_url}{pattern}")
            patterns.append(f"{domain}/careers{pattern}")
        
        # Remove duplicates
        patterns = list(dict.fromkeys(patterns))
        
        print(f"   → Trying {len(patterns)} common URL patterns...")
        
        for i, url in enumerate(patterns[:15], 1):  # Try first 15
            print(f"      [{i}] {url}")
            
            # Try fetching
            html = self.http.fetch(url)
            if not html:
                continue
            
            # Check if it has job listings
            if self.job_extractor.has_job_listings(html):
                print(f"      ✓ Found job listings!")
                jobs = self.job_extractor.extract_all_jobs(html, company_name, url)
                if jobs:
                    return jobs
        
        return []
    
    def try_deep_crawl(self, company_name: str, career_url: str) -> List[Dict]:
        """FALLBACK 3: Crawl 2-3 levels deep to find hidden job pages"""
        print(f"   → Starting deep crawl from landing page...")
        
        # Get landing page
        landing_html = self.http.fetch(career_url)
        if not landing_html:
            return []
        
        soup = BeautifulSoup(landing_html, 'html.parser')
        
        # Find ALL career-related links (Level 1)
        level1_links = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            text = a.get_text(strip=True).lower()
            
            # Look for career/job related keywords
            if any(keyword in text for keyword in [
                'career', 'job', 'work', 'opportunity', 'opening', 'position',
                'join', 'hiring', 'search', 'explore', 'find', 'browse'
            ]) or any(keyword in href.lower() for keyword in [
                'career', 'job', 'work', 'opportunity', 'opening', 'search'
            ]):
                full_url = urljoin(career_url, href)
                if urlparse(full_url).netloc == urlparse(career_url).netloc:
                    level1_links.append(full_url)
        
        # Remove duplicates
        level1_links = list(dict.fromkeys(level1_links))[:10]  # Limit to 10
        
        if not level1_links:
            return []
        
        print(f"   → Found {len(level1_links)} Level 1 links to explore")
        
        # Visit each Level 1 link
        all_jobs = []
        for i, level1_url in enumerate(level1_links, 1):
            if all_jobs:  # Stop if we found jobs
                break
            
            print(f"      [{i}/{len(level1_links)}] {level1_url[:60]}...")
            
            level1_html = self.http.fetch(level1_url)
            if not level1_html:
                continue
            
            # Try extracting jobs at Level 1
            if self.job_extractor.has_job_listings(level1_html):
                print(f"         ✓ Jobs found at Level 1!")
                jobs = self.job_extractor.extract_all_jobs(level1_html, company_name, level1_url)
                if jobs:
                    all_jobs.extend(jobs)
                    continue
            
            # Go deeper - Level 2
            soup = BeautifulSoup(level1_html, 'html.parser')
            level2_links = []
            
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                text = a.get_text(strip=True).lower()
                
                if any(keyword in text for keyword in [
                    'search', 'browse', 'find', 'view', 'see all', 'all jobs',
                    'explore', 'opportunity', 'opening', 'position'
                ]) or any(keyword in href.lower() for keyword in [
                    'search', 'browse', 'find', 'all', 'list', 'results'
                ]):
                    full_url = urljoin(level1_url, href)
                    if urlparse(full_url).netloc == urlparse(career_url).netloc:
                        level2_links.append(full_url)
            
            level2_links = list(dict.fromkeys(level2_links))[:5]  # Limit to 5
            
            if not level2_links:
                continue
            
            print(f"         → Going deeper: {len(level2_links)} Level 2 links")
            
            # Visit Level 2 links
            for j, level2_url in enumerate(level2_links, 1):
                if all_jobs:  # Stop if we found jobs
                    break
                
                level2_html = self.http.fetch(level2_url)
                if not level2_html:
                    continue
                
                if self.job_extractor.has_job_listings(level2_html):
                    print(f"         ✓ Jobs found at Level 2!")
                    jobs = self.job_extractor.extract_all_jobs(level2_html, company_name, level2_url)
                    if jobs:
                        all_jobs.extend(jobs)
                        break
        
        return all_jobs
    
    def try_alternative_domains(self, company_name: str, career_url: str) -> List[Dict]:
        """FALLBACK 4: Try alternative job-specific domains"""
        parsed = urlparse(career_url)
        base_domain = parsed.netloc
        
        # Extract root domain (e.g., company.com from careers.company.com)
        parts = base_domain.split('.')
        if len(parts) >= 2:
            root_domain = '.'.join(parts[-2:])
        else:
            root_domain = base_domain
        
        # Common alternative domains for job sites
        alternative_domains = [
            f"https://jobs.{root_domain}",
            f"https://hiring.{root_domain}",
            f"https://careers.{root_domain}",
            f"https://work.{root_domain}",
            f"https://join.{root_domain}",
            f"https://{root_domain}/jobs",
            f"https://{root_domain}/careers",
            f"https://{root_domain}/work-with-us",
        ]
        
        # Remove the original career_url
        alternative_domains = [d for d in alternative_domains if not d.startswith(f"https://{base_domain}")]
        
        print(f"   → Trying {len(alternative_domains)} alternative domains...")
        
        for i, alt_url in enumerate(alternative_domains, 1):
            print(f"      [{i}] {alt_url}")
            
            # Try fetching
            html = self.http.fetch(alt_url)
            if not html or len(html) < 5000:  # Skip error pages
                continue
            
            # Check if it looks like a career site
            text_lower = html.lower()
            if 'job' in text_lower or 'career' in text_lower or 'position' in text_lower:
                print(f"      ✓ Valid career site detected!")
                
                # Try extracting jobs directly
                if self.job_extractor.has_job_listings(html):
                    print(f"      ✓ Job listings found!")
                    jobs = self.job_extractor.extract_all_jobs(html, company_name, alt_url)
                    if jobs:
                        return jobs
                
                # Try finding job links with GPT
                from urllib.parse import urljoin
                job_links = self.scraper.link_finder.find_best_job_links(html, alt_url, company_name)
                if job_links:
                    print(f"      → Found {len(job_links)} job links, visiting...")
                    for job_url in job_links[:3]:  # Try first 3
                        job_html = self.http.fetch(job_url)
                        if job_html and self.job_extractor.has_job_listings(job_html):
                            jobs = self.job_extractor.extract_all_jobs(job_html, company_name, job_url)
                            if jobs:
                                return jobs
        
        return []
    
    def try_sitemap(self, company_name: str, career_url: str) -> List[Dict]:
        """FALLBACK 2: Parse sitemap.xml to find job URLs"""
        parsed = urlparse(career_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Common sitemap locations
        sitemap_urls = [
            f"{domain}/sitemap.xml",
            f"{domain}/careers/sitemap.xml",
            f"{domain}/sitemap_index.xml",
            f"{career_url}/sitemap.xml",
        ]
        
        print(f"   → Checking {len(sitemap_urls)} sitemap locations...")
        
        for sitemap_url in sitemap_urls:
            print(f"      • {sitemap_url}")
            
            try:
                # Fetch sitemap
                html = self.http.fetch(sitemap_url)
                if not html:
                    continue
                
                # Parse XML
                soup = BeautifulSoup(html, 'xml')
                if not soup.find():
                    # Try HTML parser if XML fails
                    soup = BeautifulSoup(html, 'html.parser')
                
                # Find all URLs
                urls = []
                for loc in soup.find_all('loc'):
                    url = loc.get_text(strip=True)
                    url_lower = url.lower()
                    
                    # Filter for job-related URLs
                    if any(keyword in url_lower for keyword in [
                        '/job/', '/jobs/', '/position/', '/opening/', 
                        '/career/', '/requisition/', '/vacancy/'
                    ]):
                        urls.append(url)
                
                if urls:
                    print(f"      ✓ Found {len(urls)} job URLs in sitemap!")
                    
                    # Fetch up to 30 job pages
                    jobs = []
                    for i, job_url in enumerate(urls[:30], 1):
                        if i % 10 == 0:
                            print(f"         Processing job {i}/{min(len(urls), 30)}...")
                        
                        job_html = self.http.fetch(job_url)
                        if job_html:
                            job_data = self.job_extractor.extract_all_jobs(job_html, company_name, job_url)
                            if job_data:
                                jobs.extend(job_data)
                        
                        # Stop if we have enough
                        if len(jobs) >= 50:
                            break
                    
                    if jobs:
                        print(f"      ✅ Extracted {len(jobs)} jobs from sitemap!")
                        return jobs
            
            except Exception as e:
                print(f"      ⚠️ Sitemap error: {str(e)[:50]}")
                continue
        
        return []
    
    def try_extended_selenium(self, company_name: str, career_url: str) -> List[Dict]:
        """FALLBACK 4: Extended Selenium with scrolling and button clicks"""
        print(f"   → Loading page with extended Selenium...")
        
        if not self.http.driver:
            if not self.http._init_selenium():
                return []
        
        try:
            driver = self.http.driver
            driver.set_page_load_timeout(120)  # 2 minutes max for page load
            driver.get(career_url)
            
            # Wait for initial load
            WebDriverWait(driver, SELENIUM_TIMEOUT).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            print(f"   → Waiting 10 seconds for JavaScript...")
            time.sleep(10)
            
            # Scroll down multiple times to trigger lazy loading
            print(f"   → Scrolling to load lazy content...")
            for i in range(6):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                if i < 5:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                    time.sleep(1)
            
            # Try clicking common "Load More" / "Show All" buttons
            print(f"   → Looking for 'Load More' / 'Show All' buttons...")
            button_texts = [
                'load more', 'show more', 'view all', 'see all', 
                'show all jobs', 'view all jobs', 'load all',
                'more jobs', 'show all results'
            ]
            
            for btn_text in button_texts:
                try:
                    buttons = driver.find_elements(By.XPATH, 
                        f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{btn_text}')] | "
                        f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{btn_text}')]"
                    )
                    
                    for button in buttons[:2]:  # Try first 2 matches
                        try:
                            if button.is_displayed() and button.is_enabled():
                                print(f"      → Clicking '{btn_text}' button...")
                                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(1)  # Reduced from 4s - faster scroll loading
                                print(f"      ✓ Clicked '{btn_text}'")
                                break
                        except:
                            continue
                except:
                    continue
            
            # Final scroll
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Reduced from 3s - faster final load
            
            # Get final page source
            html = driver.page_source
            print(f"   → Got {len(html):,} bytes after interactions")
            
            # Extract jobs
            if self.job_extractor.has_job_listings(html):
                print(f"   ✓ Page has job listings after interactions!")
                jobs = self.job_extractor.extract_all_jobs(html, company_name, career_url)
                return jobs
            else:
                print(f"   ⚠️ Still no job listings detected")
        
        except Exception as e:
            print(f"   ⚠️ Extended Selenium error: {str(e)[:80]}")
        
        return []

# ============================================================================
# HTTP CLIENT
# ============================================================================

class HTTPClient:
    """Enhanced HTTP client with Selenium support"""
    
    def __init__(self, scraper_api_key=None, use_selenium=False):
        self.session = requests.Session()
        self.scraper_api_key = scraper_api_key
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.driver = None
        
        # Rotating user agents
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        if not SELENIUM_AVAILABLE or self.driver:
            return self.driver is not None
        
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument(f'user-agent={random.choice(self.user_agents)}')
            options.add_argument('--window-size=1920,1080')
            
            # Check if running in Composer/Airflow (no Selenium Grid available)
            selenium_url = os.getenv('SELENIUM_REMOTE_URL', '')
            use_remote = selenium_url and 'selenium' in selenium_url.lower()
            
            if use_remote:
                # Docker environment with Selenium Grid
                print(f"   🌐 Using Selenium Grid at {selenium_url}")
                max_connection_retries = 3
                for retry in range(max_connection_retries):
                    try:
                        self.driver = webdriver.Remote(command_executor=selenium_url, options=options)
                        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        return True
                    except Exception as e:
                        if retry < max_connection_retries - 1:
                            wait_time = (retry + 1) * 5
                            print(f"   ⚠️ Failed to connect to Selenium Grid (attempt {retry + 1}/{max_connection_retries}): {str(e)[:80]}")
                            print(f"   ⏳ Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                        else:
                            print(f"   ❌ Failed to connect to Selenium Grid after {max_connection_retries} attempts: {str(e)[:80]}")
                            return False
            else:
                # Composer/Airflow - use chromedriver-binary package
                print("   💻 Using chromedriver-binary package (Composer/Airflow mode)")
                # chromedriver-binary package includes the driver - just import to add to PATH
                import chromedriver_binary
                self.driver = webdriver.Chrome(options=options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                return True
        except Exception as e:
            print(f"   ⚠️ Selenium init failed: {str(e)[:80]}")
            return False
    
    def fetch_with_selenium(self, url: str) -> Optional[str]:
        """Fetch URL with Selenium (for JavaScript-heavy sites)"""
        if not self.driver:
            if not self._init_selenium():
                return None
        
        try:
            self.driver.set_page_load_timeout(120)  # 2 minutes max for page load
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Wait for dynamic content
            time.sleep(4)
            
            # Scroll to load lazy content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            
            html = self.driver.page_source
            return html
            
        except Exception as e:
            print(f"   ⚠️ Selenium fetch error: {str(e)[:80]}")
            return None
        
    def fetch(self, url: str, retry: int = 0, force_selenium: bool = False) -> Optional[str]:
        """Fetch URL with smart strategy selection"""
        
        # For force_selenium, try Selenium first but with fallback to HTTP
        if force_selenium and self.use_selenium and retry == 0:
            selenium_html = self.fetch_with_selenium(url)
            if selenium_html and len(selenium_html) > 5000:  # Valid response
                return selenium_html
            # Selenium failed, try HTTP as fallback
            print(f"       → Selenium failed, trying HTTP...")
            force_selenium = False  # Disable for this attempt
        
        # Regular HTTP request with enhanced anti-detection headers
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
        
        try:
            # Smart delay with exponential backoff
            delay = random.uniform(*REQUEST_DELAY) * (retry + 1) if retry > 0 else random.uniform(*REQUEST_DELAY)
            time.sleep(delay)
            
            if self.scraper_api_key:
                api_url = f"http://api.scraperapi.com/?api_key={self.scraper_api_key}&url={url}"
                response = requests.get(api_url, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code in [403, 429]:
                if retry == 0 and self.use_selenium:
                    # First 403/429, immediately try Selenium (better for bot detection)
                    print(f"       ⚠️ Status {response.status_code}, trying Selenium...")
                    return self.fetch_with_selenium(url)
                elif retry < MAX_RETRIES:
                    # Subsequent retries (fast fail)
                    print(f"       ⚠️ Status {response.status_code}, retry {retry + 1}/{MAX_RETRIES}...")
                    time.sleep(2)  # Reduced from 5*(retry+1) to 2 seconds
                    return self.fetch(url, retry + 1, force_selenium=True)
            elif retry < MAX_RETRIES:
                return self.fetch(url, retry + 1, force_selenium)
            
        except requests.exceptions.Timeout:
            if retry < MAX_RETRIES:
                print(f"       ⚠️ Timeout, retry {retry + 1}/{MAX_RETRIES}...")
                return self.fetch(url, retry + 1, force_selenium)
        except Exception as e:
            if retry < MAX_RETRIES:
                print(f"       ⚠️ Error: {str(e)[:40]}, retry {retry + 1}/{MAX_RETRIES}...")
                time.sleep(1)  # Reduced from 3*(retry+1) to 1 second
                return self.fetch(url, retry + 1, force_selenium)
        
        return None
    
    def cleanup_driver(self):
        """Explicitly cleanup Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                print("  🔌 Selenium driver closed")
            except Exception as e:
                print(f"  ⚠️  Driver cleanup warning: {str(e)[:50]}")
            finally:
                self.driver = None
    
    def __del__(self):
        """Cleanup Selenium driver on object destruction"""
        self.cleanup_driver()

# ============================================================================
# MAIN SCRAPER
# ============================================================================

class UltraSmartScraper:
    """The ultra-smart hybrid scraper with Selenium support"""
    
    def __init__(self, openai_key: str, scraper_api_key=None, use_selenium=False):
        self.link_finder = SmartLinkFinder(openai_key)
        self.job_extractor = SmartJobExtractor(openai_key)
        self.http = HTTPClient(scraper_api_key, use_selenium=use_selenium)
        self.use_selenium = use_selenium
        self.failed_reasons = {}  # Track why companies fail
    
    def scrape_company(self, company_name: str, career_url: str) -> List[Dict]:
        """
        Scrape one company with smart strategy selection
        """
        print(f"\n{'='*80}")
        print(f"🏢 {company_name}")
        print(f"{'='*80}")
        print(f"Career Page: {career_url}")
        
        # Check if this is a JavaScript-heavy company
        needs_selenium = any(js_company in company_name.lower() for js_company in JS_HEAVY_COMPANIES)
        if needs_selenium and self.use_selenium:
            print(f"   🔧 Detected JS-heavy site - Selenium mode activated")
        
        # Step 1: Get landing page
        print(f"\n[STEP 1] Fetching landing page...")
        landing_html = self.http.fetch(career_url, force_selenium=needs_selenium)
        
        if not landing_html:
            print(f"   ✗ Failed to fetch landing page")
            
            # EARLY FALLBACK: Try common career page patterns from base domain
            print(f"\n[EARLY FALLBACK] Trying common career URLs from base domain...")
            from urllib.parse import urlparse
            parsed = urlparse(career_url)
            base_domain = f"{parsed.scheme}://{parsed.netloc}"
            
            # Common career page patterns to try
            common_patterns = [
                '/careers',
                '/jobs', 
                '/careers/jobs',
                '/careers/search',
                '/en/careers',
                '/en-us/careers',
                '/company/careers',
                '/about/careers',
                '/work-with-us',
                '/join-us'
            ]
            
            for pattern in common_patterns:
                test_url = base_domain + pattern
                print(f"   → Trying {test_url}...")
                test_html = self.http.fetch(test_url, force_selenium=False)
                # If HTTP fails with 403, try Selenium for bot detection
                if not test_html and self.use_selenium:
                    test_html = self.http.fetch(test_url, force_selenium=True)
                if test_html and len(test_html) > 5000:
                    print(f"   ✅ Found! Using {test_url} instead")
                    career_url = test_url
                    landing_html = test_html
                    break
            
            if not landing_html:
                print(f"   ✗ All fallback URLs failed")
                self.failed_reasons[company_name] = "Failed to fetch landing page (connection error)"
                return []
        
        print(f"   ✓ Fetched ({len(landing_html):,} bytes)")
        
        # Step 2: Find best links
        print(f"\n[STEP 2] Finding job listing links with GPT...")
        job_links = self.link_finder.find_best_job_links(landing_html, career_url, company_name)
        
        if not job_links:
            print(f"   ⚠️ No good links found - trying to extract from landing page directly...")
            # Try extracting jobs directly from landing page as fallback
            if self.job_extractor.has_job_listings(landing_html):
                print(f"   ✓ Landing page has job listings!")
                jobs = self.job_extractor.extract_all_jobs(landing_html, company_name, career_url)
                if jobs:
                    print(f"   ✅ Extracted {len(jobs)} jobs from landing page!")
                    return jobs
            print(f"   ✗ No jobs found on landing page either")
            self.failed_reasons[company_name] = "GPT could not identify job listing pages"
            return []
        
        # Step 3: Try each link (ENHANCED - more aggressive extraction)
        print(f"\n[STEP 3] Visiting {len(job_links)} promising pages...")
        
        all_jobs = []
        
        for i, job_url in enumerate(job_links, 1):
            print(f"\n   [{i}/{len(job_links)}] {job_url[:70]}...")
            
            # Fetch page (use Selenium if needed)
            page_html = self.http.fetch(job_url, force_selenium=needs_selenium)
            if not page_html:
                print(f"       ✗ Failed to fetch")
                # Try with Selenium as fallback if not already using it
                if not needs_selenium and self.use_selenium:
                    print(f"       → Retrying with Selenium...")
                    page_html = self.http.fetch(job_url, force_selenium=True)
                    if not page_html:
                        continue
                else:
                    continue
            
            print(f"       ✓ Fetched ({len(page_html):,} bytes)")
            
            # LESS STRICT - Try to extract even if detection is weak
            has_listings = self.job_extractor.has_job_listings(page_html)
            if not has_listings:
                print(f"       ⚠️  Weak job signal, but trying extraction anyway...")
            else:
                print(f"       ✓ Job listings detected!")
            
            # Extract individual job URLs
            print(f"       → Extracting individual job URLs...")
            job_urls = self.job_extractor.extract_job_urls(page_html, job_url)
            
            if job_urls:
                print(f"       ✓ Found {len(job_urls)} individual job URLs")
                # Show first few URLs for debugging
                if len(job_urls) <= 3:
                    for u in job_urls:
                        print(f"           • {u}")
                else:
                    for u in job_urls[:3]:
                        print(f"           • {u}")
                    print(f"           ... and {len(job_urls) - 3} more")
                
                print(f"       → Fetching details from each job page...")
                
                jobs = []
                for idx, individual_job_url in enumerate(job_urls[:50], 1):  # Limit to 50 jobs per listing page
                    if idx % 5 == 0:
                        print(f"         Processing job {idx}/{min(len(job_urls), 10)}...")
                    
                    # Try regular fetch first, fallback to Selenium
                    job_html = self.http.fetch(individual_job_url)
                    if not job_html and self.use_selenium:
                        job_html = self.http.fetch(individual_job_url, force_selenium=True)
                    
                    if job_html:
                        job_data = self.job_extractor.extract_all_jobs(job_html, company_name, individual_job_url)
                        if job_data:
                            jobs.extend(job_data)
            else:
                print(f"       → No individual job URLs found, extracting from listing page...")
                jobs = self.job_extractor.extract_all_jobs(page_html, company_name, job_url)
            
            if jobs:
                print(f"       ✅ Extracted {len(jobs)} USA jobs!")
                all_jobs.extend(jobs)
                
                # INCREASED threshold - keep going to get more jobs
                if len(all_jobs) >= 100:  # Changed from 50 to 100
                    print(f"\n   🎯 Found {len(all_jobs)} jobs, stopping")
                    break
            else:
                # Even if extraction failed, try Selenium as last attempt
                if not needs_selenium and self.use_selenium and has_listings:
                    print(f"       → Extraction failed with HTTP, trying Selenium...")
                    selenium_html = self.http.fetch(job_url, force_selenium=True)
                    if selenium_html:
                        retry_jobs = self.job_extractor.extract_all_jobs(selenium_html, company_name, job_url)
                        if retry_jobs:
                            print(f"       ✅ Selenium extraction: {len(retry_jobs)} jobs!")
                            all_jobs.extend(retry_jobs)
        
        # Result - Only try fallbacks if we got 0 jobs (to save time on Fortune 500 run)
        # Companies with some jobs are considered successful
        jobs_found = len(all_jobs) if all_jobs else 0
        
        if all_jobs:
            print(f"\n{'='*80}")
            print(f"✅ SUCCESS: {len(all_jobs)} total USA jobs from {company_name}")
            print(f"{'='*80}")
        else:
            print(f"\n{'='*80}")
            print(f"⊘ No USA jobs found for {company_name} on their website")
            print(f"{'='*80}")
            
            # Track failure reason
            if company_name not in self.failed_reasons:
                self.failed_reasons[company_name] = "Pages visited but no jobs extracted"
            
            # ENHANCED FALLBACKS: Try alternative strategies before JobSpy
            fallback_chain = EnhancedFallbackChain(self)
            all_jobs = fallback_chain.try_all_fallbacks(company_name, career_url)
            
            if all_jobs:
                print(f"✅ Fallback chain saved {company_name}: {len(all_jobs)} jobs!")
                self.failed_reasons.pop(company_name, None)  # Remove from failed
            else:
                # LAST RESORT: Try JobSpy (Indeed, LinkedIn, etc.) if everything else failed
                if JOBSPY_AVAILABLE:
                    print(f"\n[LAST RESORT] Trying JobSpy (Indeed/LinkedIn) for {company_name}...")
                    # Add delay to respect Indeed rate limits
                    time.sleep(random.uniform(0.5, 1.5))  # Reduced from 2-4s to 0.5-1.5s
                    all_jobs = self.scrape_with_jobspy(company_name)
                    if all_jobs:
                        print(f"✅ JobSpy found {len(all_jobs)} jobs!")
                        self.failed_reasons.pop(company_name, None)  # Remove from failed
                    else:
                        print(f"⊘ JobSpy also found 0 jobs")
                        self.failed_reasons[company_name] = "Failed: All strategies (direct + fallbacks + JobSpy) returned 0 jobs"
        
        return all_jobs
    
    def scrape_with_jobspy(self, company_name: str) -> List[Dict]:
        """
        Fallback scraper using JobSpy (Indeed, LinkedIn, ZipRecruiter, Glassdoor)
        Only called when company website scraping returns 0 jobs
        Includes retry logic for rate limiting
        """
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"   ⚠️  Retry attempt {attempt + 1}/{max_retries}...")
                    time.sleep(retry_delay * attempt)  # Exponential backoff
                
                print(f"   → Searching Indeed for '{company_name}' jobs in USA...")
                
                # Scrape jobs from Indeed - last 7 days, USA only
                jobs_df = scrape_jobs(
                    site_name=["indeed"],
                    search_term=company_name,
                    location="United States",
                    results_wanted=50,  # Get up to 50 jobs
                    hours_old=168,  # Last 7 days (168 hours)
                    country_indeed='USA'
                )
                
                if jobs_df is None or len(jobs_df) == 0:
                    return []
                
                print(f"   ✓ Found {len(jobs_df)} jobs from Indeed")
                
                # Convert to our format
                jobs = []
                for _, row in jobs_df.iterrows():
                    jobs.append({
                        'job_id': row.get('job_id'),
                        'title': row.get('title', ''),
                        'company': company_name,
                        'location': row.get('location', 'USA'),
                        'job_type': row.get('job_type', ''),
                        'department': '',
                        'salary_range': f"${row.get('min_amount', '')}-${row.get('max_amount', '')}" if row.get('min_amount') else '',
                        'description': row.get('description', '')[:500] if row.get('description') else '',
                        'apply_url': row.get('job_url', ''),
                        'posted_date': str(row.get('date_posted', '')) if row.get('date_posted') else '',
                        'source': 'jobspy_indeed',
                        'scraped_at': datetime.now().isoformat()
                    })
                
                return jobs
                
            except Exception as e:
                print(f"   ⚠️ JobSpy error (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                if attempt == max_retries - 1:
                    print(f"   ❌ Max retries reached for {company_name}")
                    return []
        
        return []

# ============================================================================
# PROGRESS MANAGER (Thread-Safe)
# ============================================================================

class ProgressManager:
    """Manages progress with thread-safe operations"""
    
    def __init__(self):
        self.checkpoint_file = 'scraped_jobs/fortune500_progress.json'
        self.completed = self.load_progress()
        self.lock = Lock()  # Thread-safe operations
    
    def load_progress(self) -> Set[str]:
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return set(json.load(f).get('completed', []))
        return set()
    
    def save_progress(self, company: str):
        with self.lock:
            self.completed.add(company)
            os.makedirs('POC_OUTPUT', exist_ok=True)
            with open(self.checkpoint_file, 'w') as f:
                json.dump({'completed': list(self.completed)}, f)
    
    def is_completed(self, company: str) -> bool:
        with self.lock:
            return company in self.completed

# ============================================================================
# MAIN
# ============================================================================

def scrape_single_company(company_info: Dict, scraper: UltraSmartScraper, 
                         progress: ProgressManager, worker_id: int) -> Dict:
    """Scrape a single company (thread-safe worker function)"""
    company_name = company_info['name']
    company_url = company_info['url']
    
    result = {
        'company': company_name,
        'jobs': [],
        'success': False,
        'error': None
    }
    
    try:
        jobs = scraper.scrape_company(company_name, company_url)
        
        if jobs:
            result['jobs'] = jobs
            result['success'] = True
            print(f"[Worker {worker_id}] ✅ {company_name}: {len(jobs)} jobs")
        else:
            print(f"[Worker {worker_id}] ⚠️  {company_name}: 0 jobs")
        
        progress.save_progress(company_name)
        
    except Exception as e:
        result['error'] = str(e)
        print(f"[Worker {worker_id}] ❌ {company_name}: {str(e)[:100]}")
    
    return result

def main():
    print("="*80)
    print("  ULTRA-SMART JOB CRAWLER (8 PARALLEL WORKERS)")
    print("  Student: Pranav Patel | DAMG 7245")
    print("  Intelligently explores websites to find ALL USA jobs")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize
    progress = ProgressManager()
    
    # Load companies
    print("📋 Loading Fortune 500 companies...")
    
    csv_path = 'data/raw/fortune500_career_pages.csv'
    if not os.path.exists(csv_path):
        csv_path = 'fortune500_career_pages.csv'
    
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: CSV not found")
        return
    
    companies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows with missing or invalid URLs
            career_url = row.get('final_career_url', '').strip()
            if not career_url:
                continue
            if 'No central' in career_url or career_url == '':
                continue
            
            # Only include verified URLs or URLs that look valid
            verified = row.get('verified', 'False')
            if verified == 'False' and not career_url.startswith('http'):
                continue
            
            companies.append({
                'name': row['company_name'],
                'url': career_url
            })
    
    print(f"✓ Loaded {len(companies)} companies")
    print(f"✓ Already completed: {len(progress.completed)}")
    print()
    
    # Filter out completed companies
    companies_to_scrape = [c for c in companies if not progress.is_completed(c['name'])]
    
    if MAX_COMPANIES:
        companies_to_scrape = companies_to_scrape[:MAX_COMPANIES]
    
    print(f"🎯 Scraping {len(companies_to_scrape)} companies with {NUM_WORKERS} workers")
    print()
    
    # Thread-safe results collection
    all_jobs = []
    successful = 0
    failed = 0
    failed_companies = []
    results_lock = Lock()
    
    print("="*80)
    print("STARTING PARALLEL SCRAPING")
    print("="*80)
    print()
    
    start_time = datetime.now()
    
    # Create worker pool
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Create scraper instances for each worker (with staggered start)
        # Smart worker distribution:
        # - Workers 1-3: Selenium enabled (for JS-heavy sites: Amazon, Google, Meta, etc.)
        # - Workers 4-8: HTTP only (fast for simple sites: Walmart, CVS, etc.)
        scrapers = []
        for i in range(NUM_WORKERS):
            use_selenium = SELENIUM_AVAILABLE and (i < NUM_SELENIUM_WORKERS)
            scraper = UltraSmartScraper(OPENAI_API_KEY, SCRAPERAPI_KEY, use_selenium=use_selenium)
            scrapers.append(scraper)
            if use_selenium:
                print(f"[Worker {i+1}] Selenium enabled ✅ (JS-heavy sites)")
            else:
                print(f"[Worker {i+1}] HTTP only (fast scraping)")
            time.sleep(0.2)  # Reduced from 0.5s - faster startup
        
        # Submit all tasks
        future_to_company = {}
        for i, company in enumerate(companies_to_scrape):
            worker_id = i % NUM_WORKERS
            scraper = scrapers[worker_id]
            future = executor.submit(scrape_single_company, company, scraper, progress, worker_id + 1)
            future_to_company[future] = company
        
        # Process results as they complete
        completed_count = 0
        for future in as_completed(future_to_company):
            completed_count += 1
            company = future_to_company[future]
            
            try:
                result = future.result()
                
                with results_lock:
                    if result['success']:
                        all_jobs.extend(result['jobs'])
                        successful += 1
                    else:
                        failed += 1
                        failed_companies.append(result['company'])
                    
                    # Progress update every 5 companies (no file save)
                    if completed_count % CHECKPOINT_EVERY == 0:
                        elapsed = (datetime.now() - start_time).total_seconds() / 60
                        print(f"\n📊 Progress [{completed_count}/{len(companies_to_scrape)}]: {len(all_jobs)} jobs collected | {elapsed:.1f} min elapsed")
            
            except Exception as e:
                print(f"❌ Future error for {company['name']}: {str(e)[:100]}")
                with results_lock:
                    failed += 1
                    failed_companies.append(company['name'])
    
    # Final results
    elapsed_time = (datetime.now() - start_time).total_seconds() / 60
    
    print("\n" + "="*80)
    print("SCRAPING COMPLETE")
    print("="*80)
    print()
    print(f"📊 Results:")
    print(f"   Companies: {successful + failed}")
    print(f"   Successful: {successful}")
    print(f"   Failed (0 jobs): {failed}")
    print(f"   Total jobs: {len(all_jobs)}")
    print(f"   Time elapsed: {elapsed_time:.1f} minutes ({elapsed_time/60:.1f} hours)")
    print()
    
    if failed_companies:
        print(f"❌ Companies with 0 jobs ({len(failed_companies)}):")
        
        # Collect all failure reasons
        failure_reasons = {}
        for scraper in scrapers:
            failure_reasons.update(scraper.failed_reasons)
        
        for company in failed_companies:
            reason = failure_reasons.get(company, 'Unknown reason')
            print(f"   • {company:35s} | {reason[:60]}")
        print()
        
        # Save detailed failure analysis
        os.makedirs('scraped_jobs', exist_ok=True)
        with open('scraped_jobs/fortune500_failed_analysis.json', 'w') as f:
            json.dump(failure_reasons, f, indent=2)
        print(f"   💾 Failure analysis saved: scraped_jobs/fortune500_failed_analysis.json")
        print()
    
    if all_jobs:
        save_results(all_jobs, 'fortune500_final.csv')
        
        print("📋 Sample jobs:")
        for i, job in enumerate(all_jobs[:20], 1):
            print(f"{i:2d}. {job['title'][:50]:50s} | {job['company'][:15]:15s} | {job['location'][:20]}")
        
        print(f"\n💾 Total unique jobs: {len(all_jobs)}")
    
    print()
    print("="*80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

def save_results(jobs: List[Dict], filename: str):
    """Save results (thread-safe)"""
    os.makedirs('scraped_jobs', exist_ok=True)
    
    if not jobs:
        return
    
    df = pd.DataFrame(jobs)
    df = df.drop_duplicates(subset=['title', 'company'], keep='first')
    jobs_unique = df.to_dict('records')
    
    df.to_csv(f'scraped_jobs/{filename}', index=False)
    
    # Save clean JSON (jobs only - no metadata)
    json_file = filename.replace('.csv', '.json')
    with open(f'scraped_jobs/{json_file}', 'w') as f:
        json.dump(jobs_unique, f, indent=2)
    
    # Save metadata separately
    metadata_file = filename.replace('.csv', '_metadata.json')
    with open(f'scraped_jobs/{metadata_file}', 'w') as f:
        json.dump({
            'scraped_at': datetime.now().isoformat(),
            'total_jobs': len(jobs_unique),
            'companies': len(set(j['company'] for j in jobs_unique)),
            'source': 'fortune500'
        }, f, indent=2)
    
    print(f"   💾 Saved: scraped_jobs/{filename}")
    print(f"   💾 Saved: scraped_jobs/{json_file}")
    print(f"   💾 Saved: scraped_jobs/{metadata_file}")

if __name__ == "__main__":
    main()