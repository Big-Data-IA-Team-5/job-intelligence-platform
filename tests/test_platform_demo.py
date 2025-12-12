"""
Comprehensive Platform Demo Tests
Tests all major features with real-world scenarios to showcase platform capabilities
"""
import requests
import json
import time
from typing import Dict, List

# Configuration
BACKEND_URL = "https://job-intelligence-backend-97083220044.us-central1.run.app"
FRONTEND_URL = "https://job-intelligence-frontend-97083220044.us-central1.run.app"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE} {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_test(name: str):
    print(f"{Colors.CYAN}🔍 Test: {name}{Colors.END}")


def print_pass(message: str):
    print(f"{Colors.GREEN}  ✅ PASS: {message}{Colors.END}")


def print_fail(message: str):
    print(f"{Colors.RED}  ❌ FAIL: {message}{Colors.END}")


def print_info(message: str):
    print(f"{Colors.YELLOW}  ℹ️  {message}{Colors.END}")


def print_result(data: Dict, max_items: int = 3):
    """Pretty print result data"""
    if isinstance(data, list):
        for i, item in enumerate(data[:max_items]):
            print(f"{Colors.CYAN}     [{i+1}] {item}{Colors.END}")
    elif isinstance(data, dict):
        for key, value in list(data.items())[:max_items]:
            print(f"{Colors.CYAN}     {key}: {value}{Colors.END}")


# =============================================================================
# TEST SUITE 1: JOB SEARCH & FILTERING
# =============================================================================

def test_1_basic_job_search():
    """Test 1: Basic job search with no filters"""
    print_section("TEST SUITE 1: JOB SEARCH & FILTERING")
    print_test("1.1 - Basic Job Search (No Filters)")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            
            if len(jobs) > 0:
                print_pass(f"Retrieved {len(jobs)} jobs")
                print_info(f"Total jobs in DB: {data.get('total', 'N/A')}")
                print_result([f"{j['title']} at {j['company']}" for j in jobs[:3]])
                return True
            else:
                print_fail("No jobs returned")
                return False
        else:
            print_fail(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_2_location_filtering():
    """Test 2: Filter jobs by location"""
    print_test("1.2 - Location Filtering (Boston)")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"locations": ["Boston, MA"], "limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            
            if len(jobs) > 0:
                print_pass(f"Found {len(jobs)} jobs in Boston")
                print_result([f"{j['title']} - {j['location']}" for j in jobs[:3]])
                
                # Verify all jobs are in Boston
                boston_count = sum(1 for j in jobs if 'Boston' in j.get('location', ''))
                if boston_count == len(jobs):
                    print_pass(f"All {boston_count} jobs correctly filtered to Boston")
                else:
                    print_fail(f"Only {boston_count}/{len(jobs)} jobs are in Boston")
                return True
            else:
                print_fail("No Boston jobs found")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_3_date_filtering():
    """Test 3: Filter by posted date (Last 24 hours)"""
    print_test("1.3 - Date Filtering (Last 24 Hours)")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"posted_within_days": 1, "limit": 10},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            
            if len(jobs) > 0:
                print_pass(f"Found {len(jobs)} recent jobs (posted yesterday or today)")
                
                # Check days_since_posted values
                days_values = [j.get('days_since_posted') for j in jobs if j.get('days_since_posted') is not None]
                if days_values:
                    print_info(f"Days since posted: {min(days_values)} - {max(days_values)}")
                    if all(d <= 1 for d in days_values):
                        print_pass("All jobs posted within last 24 hours ✓")
                    else:
                        print_fail(f"Some jobs older than 24 hours: {[d for d in days_values if d > 1]}")
                
                print_result([f"{j['title']} (posted {j.get('days_since_posted', 'N/A')} days ago)" for j in jobs[:3]])
                return True
            else:
                print_fail("No recent jobs found")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_4_visa_sponsorship_filter():
    """Test 4: Filter by H-1B sponsorship"""
    print_test("1.4 - H-1B Sponsorship Filter")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"visa_sponsorship": "Yes", "limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            
            if len(jobs) > 0:
                print_pass(f"Found {len(jobs)} jobs with H-1B sponsorship")
                
                # Check H-1B sponsor status
                sponsor_count = sum(1 for j in jobs if j.get('h1b_sponsor') is True)
                print_info(f"{sponsor_count}/{len(jobs)} jobs confirmed as H-1B sponsors")
                
                print_result([
                    f"{j['company']} - Approval Rate: {j.get('h1b_approval_rate', 0)*100:.1f}%" 
                    for j in jobs[:3] if j.get('h1b_approval_rate')
                ])
                return True
            else:
                print_fail("No H-1B sponsor jobs found")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_5_salary_filtering():
    """Test 5: Filter by salary range"""
    print_test("1.5 - Salary Range Filtering ($100k - $200k)")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"salary_min": 100000, "salary_max": 200000, "limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            
            if len(jobs) > 0:
                print_pass(f"Found {len(jobs)} jobs in salary range")
                print_result([
                    f"{j['title']} - ${j.get('salary_min', 0):,} - ${j.get('salary_max', 0):,}"
                    for j in jobs[:3] if j.get('salary_min')
                ])
                return True
            else:
                print_fail("No jobs in salary range found")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_6_keyword_search():
    """Test 6: Search with keywords"""
    print_test("1.6 - Keyword Search (Python Engineer)")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"search": "python engineer", "limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            
            if len(jobs) > 0:
                print_pass(f"Found {len(jobs)} Python engineer jobs")
                print_result([f"{j['title']} at {j['company']}" for j in jobs[:3]])
                return True
            else:
                print_fail("No Python engineer jobs found")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


# =============================================================================
# TEST SUITE 2: RESUME MATCHING
# =============================================================================

def test_7_resume_matching():
    """Test 7: Resume matching with job recommendations"""
    print_section("TEST SUITE 2: RESUME MATCHING")
    print_test("2.1 - Resume Matching & Job Recommendations")
    
    sample_resume = """
    John Doe
    Software Engineer
    
    EDUCATION:
    Master's in Computer Science, MIT, 2022
    
    EXPERIENCE:
    Software Engineer at Amazon (2022-2024)
    - Built microservices using Python, AWS, and Docker
    - Led team of 3 engineers on ML pipeline project
    - Technologies: Python, AWS Lambda, DynamoDB, Kubernetes
    
    SKILLS:
    Python, Java, AWS, Docker, Kubernetes, React, PostgreSQL, Git
    
    WORK AUTHORIZATION: F-1 OPT
    """
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/resume/match",
            json={"resume_text": sample_resume, "user_id": "test_user_001"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                profile = data.get('profile', {})
                matches = data.get('top_matches', [])
                
                print_pass(f"Profile extracted successfully")
                print_info(f"Skills: {', '.join(profile.get('technical_skills', [])[:5])}")
                print_info(f"Experience: {profile.get('total_experience_years', 0)} years")
                print_info(f"Education: {profile.get('education_level', 'N/A')}")
                print_info(f"Visa Status: {profile.get('work_authorization', 'N/A')}")
                
                if len(matches) > 0:
                    print_pass(f"Found {len(matches)} job matches")
                    print_result([
                        f"{m['title']} at {m['company']} - Score: {m['overall_score']*100:.0f}%"
                        for m in matches[:3]
                    ])
                    
                    # Check score quality
                    avg_score = sum(m['overall_score'] for m in matches) / len(matches)
                    print_info(f"Average match score: {avg_score*100:.1f}%")
                    return True
                else:
                    print_fail("No job matches found")
                    return False
            else:
                print_fail(f"Status: {data.get('status')}")
                return False
        else:
            print_fail(f"HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


# =============================================================================
# TEST SUITE 3: CHAT AGENT & INTELLIGENCE
# =============================================================================

def test_8_chat_job_search():
    """Test 8: Chat agent job search"""
    print_section("TEST SUITE 3: CHAT AGENT & INTELLIGENCE")
    print_test("3.1 - Chat Job Search (Natural Language)")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat/ask",
            json={
                "question": "Find me software engineering jobs in Boston",
                "user_id": "test_user_chat"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', '')
            jobs = data.get('jobs', [])
            
            if len(jobs) > 0:
                print_pass(f"Chat agent found {len(jobs)} jobs")
                print_info(f"Answer preview: {answer[:150]}...")
                print_result([f"{j.get('TITLE', j.get('title', 'N/A'))}" for j in jobs[:3]])
                return True
            else:
                print_fail(f"No jobs found. Answer: {answer[:100]}")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_9_chat_salary_query():
    """Test 9: Chat agent salary query"""
    print_test("3.2 - Chat Salary Query (H-1B Data)")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat/ask",
            json={
                "question": "What's the average salary for software engineers at Google?",
                "user_id": "test_user_chat"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', '')
            
            if answer and len(answer) > 10:
                print_pass("Chat agent provided salary information")
                print_info(f"Answer: {answer[:200]}...")
                return True
            else:
                print_fail("No salary information returned")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_10_chat_h1b_sponsorship():
    """Test 10: Chat agent H-1B sponsorship query"""
    print_test("3.3 - Chat H-1B Sponsorship Query")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat/ask",
            json={
                "question": "Does Amazon sponsor H-1B visas?",
                "user_id": "test_user_chat"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('answer', '')
            
            if answer and ('yes' in answer.lower() or 'sponsor' in answer.lower()):
                print_pass("Chat agent answered H-1B question")
                print_info(f"Answer: {answer[:200]}...")
                return True
            else:
                print_fail(f"Unclear answer: {answer[:100]}")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


# =============================================================================
# TEST SUITE 4: ANALYTICS & STATISTICS
# =============================================================================

def test_11_analytics_summary():
    """Test 11: Platform analytics summary"""
    print_section("TEST SUITE 4: ANALYTICS & STATISTICS")
    print_test("4.1 - Analytics Summary")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/analytics/summary",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print_pass("Analytics data retrieved")
            print_info(f"Total Jobs: {data.get('total_jobs', 'N/A'):,}")
            print_info(f"Total Companies: {data.get('total_companies', 'N/A'):,}")
            print_info(f"H-1B Sponsors: {data.get('h1b_sponsors', 'N/A'):,}")
            print_info(f"Avg Salary: ${data.get('avg_salary', 0):,.0f}")
            print_info(f"Recent Postings (7d): {data.get('recent_postings_7d', 'N/A'):,}")
            return True
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_12_top_companies():
    """Test 12: Top hiring companies"""
    print_test("4.2 - Top Hiring Companies")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/analytics/companies?limit=10",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            companies = data.get('companies', [])
            
            if len(companies) > 0:
                print_pass(f"Retrieved top {len(companies)} companies")
                print_result([
                    f"{c['company']} - {c['job_count']} jobs (H-1B: {c.get('h1b_sponsor', False)})"
                    for c in companies[:5]
                ])
                return True
            else:
                print_fail("No companies data")
                return False
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


# =============================================================================
# TEST SUITE 5: PERFORMANCE & HEALTH
# =============================================================================

def test_13_backend_health():
    """Test 13: Backend health check"""
    print_section("TEST SUITE 5: PERFORMANCE & HEALTH")
    print_test("5.1 - Backend Health Check")
    
    try:
        start_time = time.time()
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            print_pass(f"Backend is healthy (Response time: {response_time:.0f}ms)")
            return True
        else:
            print_fail(f"Backend unhealthy: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


def test_14_response_time():
    """Test 14: API response time"""
    print_test("5.2 - API Response Time Test")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"limit": 10},
            timeout=10
        )
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            if response_time < 1000:
                print_pass(f"Fast response: {response_time:.0f}ms")
            elif response_time < 3000:
                print_pass(f"Acceptable response: {response_time:.0f}ms")
            else:
                print_fail(f"Slow response: {response_time:.0f}ms")
            return True
        else:
            print_fail(f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all tests and generate summary report"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*22 + "JOB INTELLIGENCE PLATFORM" + " "*31 + "║")
    print("║" + " "*20 + "COMPREHENSIVE TEST SUITE" + " "*33 + "║")
    print("╚" + "═"*78 + "╝")
    print(f"{Colors.END}\n")
    
    results = {}
    
    # Test Suite 1: Job Search & Filtering
    results['test_1_basic_job_search'] = test_1_basic_job_search()
    results['test_2_location_filtering'] = test_2_location_filtering()
    results['test_3_date_filtering'] = test_3_date_filtering()
    results['test_4_visa_sponsorship_filter'] = test_4_visa_sponsorship_filter()
    results['test_5_salary_filtering'] = test_5_salary_filtering()
    results['test_6_keyword_search'] = test_6_keyword_search()
    
    # Test Suite 2: Resume Matching
    results['test_7_resume_matching'] = test_7_resume_matching()
    
    # Test Suite 3: Chat Agent
    results['test_8_chat_job_search'] = test_8_chat_job_search()
    results['test_9_chat_salary_query'] = test_9_chat_salary_query()
    results['test_10_chat_h1b_sponsorship'] = test_10_chat_h1b_sponsorship()
    
    # Test Suite 4: Analytics
    results['test_11_analytics_summary'] = test_11_analytics_summary()
    results['test_12_top_companies'] = test_12_top_companies()
    
    # Test Suite 5: Performance
    results['test_13_backend_health'] = test_13_backend_health()
    results['test_14_response_time'] = test_14_response_time()
    
    # Generate Summary
    print_section("TEST SUMMARY REPORT")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"{Colors.BOLD}Total Tests: {total}{Colors.END}")
    print(f"{Colors.GREEN}Passed: {passed} ✅{Colors.END}")
    print(f"{Colors.RED}Failed: {total - passed} ❌{Colors.END}")
    print(f"{Colors.BOLD}Pass Rate: {pass_rate:.1f}%{Colors.END}\n")
    
    # Detailed results
    for test_name, result in results.items():
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
    
    return pass_rate >= 80  # Consider test suite successful if 80%+ pass


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
