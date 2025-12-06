#!/usr/bin/env python3
"""Debug script to check Airtable page structure"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Configuration
SELENIUM_URL = os.getenv('SELENIUM_REMOTE_URL', 'http://selenium-chrome:4444/wd/hub')
TEST_URL = "https://airtable.com/appqYfRGKpLQ8UsdH/shrFnvW20reJCEkYZ/tblDVfWJzDdU8KsoY?viewControls=on"

def main():
    print("🔍 Debugging Airtable Page Structure")
    print("=" * 80)
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Connect to Selenium Grid
    print(f"\n📡 Connecting to Selenium Grid: {SELENIUM_URL}")
    driver = webdriver.Remote(command_executor=SELENIUM_URL, options=chrome_options)
    
    try:
        # Load page
        print(f"\n🌐 Loading page: {TEST_URL}")
        driver.get(TEST_URL)
        
        # Wait for page to load
        print("\n⏳ Waiting 30 seconds for page to load...")
        time.sleep(30)
        
        # Get page source length
        page_source = driver.page_source
        print(f"\n📄 Page source length: {len(page_source)} characters")
        
        # Check for various selectors
        print("\n🔍 Testing CSS Selectors:")
        print("-" * 80)
        
        selectors = [
            ('div.dataRow[data-rowid]', 'Data rows (current selector)'),
            ('div.dataRow', 'Data rows without attribute'),
            ('div[data-rowid]', 'Any div with data-rowid'),
            ('div[role="row"]', 'Divs with role=row'),
            ('tr[data-rowid]', 'Table rows with data-rowid'),
            ('tr', 'Any table rows'),
            ('.cell', 'Elements with cell class'),
            ('div[data-columnid]', 'Cells with data-columnid'),
            ('div.row', 'Divs with row class'),
            ('[class*="row"]', 'Any element with "row" in class'),
            ('[class*="cell"]', 'Any element with "cell" in class'),
        ]
        
        for selector, description in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"  ✓ {selector:40s} → {len(elements):4d} elements | {description}")
                
                if elements and len(elements) > 0:
                    # Show first element details
                    first = elements[0]
                    print(f"    First element tag: {first.tag_name}")
                    print(f"    First element classes: {first.get_attribute('class')}")
                    print(f"    First element text (first 100 chars): {first.text[:100] if first.text else '(no text)'}")
            except Exception as e:
                print(f"  ✗ {selector:40s} → Error: {str(e)[:50]}")
        
        # Check page title
        print(f"\n📌 Page title: {driver.title}")
        
        # Check if Airtable loaded
        body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
        print(f"\n📝 Body text (first 500 chars):\n{body_text}")
        
        # Save page source for inspection
        output_file = "/opt/airflow/scraped_jobs/debug_page_source.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f"\n💾 Page source saved to: {output_file}")
        
        # Take screenshot
        screenshot_file = "/opt/airflow/scraped_jobs/debug_screenshot.png"
        driver.save_screenshot(screenshot_file)
        print(f"📸 Screenshot saved to: {screenshot_file}")
        
    finally:
        print("\n🔚 Closing browser...")
        driver.quit()
        print("✅ Done!")

if __name__ == "__main__":
    main()
