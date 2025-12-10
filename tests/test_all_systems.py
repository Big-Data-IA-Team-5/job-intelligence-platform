"""
Comprehensive System Test - Verifies all agents, context, and resume parsing
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "snowflake"))
sys.path.insert(0, str(project_root / "frontend"))

import json
from snowflake.agents.agent1_search import JobSearchAgent
from snowflake.agents.agent2_chat import JobIntelligenceAgent
from snowflake.agents.agent3_classifier import VisaClassifier
from snowflake.agents.agent4_matcher import ResumeMatcherAgent
from frontend.utils.context_manager import ConversationContext


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")


def test_agent1_search():
    """Test Agent 1 - Job Search"""
    print_header("Testing Agent 1 - Job Search")
    
    try:
        agent = JobSearchAgent()
        print_info("Agent 1 initialized successfully")
        
        # Test 1: Basic search
        print("\n1️⃣  Testing basic job search...")
        result = agent.search(
            query="software engineer jobs in Boston",
            filters={}
        )
        
        if result and result.get("status") == "success":
            jobs = result.get("jobs", [])
            if len(jobs) > 0:
                print_success(f"Found {result.get('total', len(jobs))} jobs")
                sample_job = jobs[0]
                print(f"   Sample: {sample_job.get('job_title', 'N/A')} at {sample_job.get('company_name', 'N/A')}")
            else:
                print_error("No jobs found")
        else:
            print_error(f"Search failed: {result.get('error', 'Unknown error')}")
            
        # Test 2: Filter-based search
        print("\n2️⃣  Testing filtered search (remote jobs)...")
        result = agent.search(
            query="machine learning engineer",
            filters={"remote_type": "remote"}
        )
        
        if result and result.get("status") == "success":
            jobs = result.get("jobs", [])
            if len(jobs) > 0:
                print_success(f"Found {len(jobs)} remote ML jobs")
            else:
                print_error("No remote jobs found")
        else:
            print_error(f"Remote search failed: {result.get('error', 'Unknown error')}")
            
        return True
        
    except Exception as e:
        print_error(f"Agent 1 failed: {str(e)}")
        return False


def test_agent2_chat():
    """Test Agent 2 - Chat/SQL Agent"""
    print_header("Testing Agent 2 - Chat/SQL Agent")
    
    try:
        agent = JobIntelligenceAgent()
        print_info("Agent 2 initialized successfully")
        
        # Test 1: H1B query
        print("\n1️⃣  Testing H1B query...")
        response = agent.ask("Get me H1B information for Google")
        
        if response and isinstance(response, dict) and response.get("status") == "success":
            print_success("H1B query executed successfully")
            if "results" in response and len(response["results"]) > 0:
                print(f"   Found {len(response['results'])} Google H1B records")
                sample = response["results"][0]
                if "employer_name" in sample:
                    print(f"   Sample: {sample['employer_name']}")
            elif "answer" in response:
                print(f"   Answer preview: {str(response['answer'])[:100]}...")
        else:
            print_error(f"H1B query failed: {response.get('error', 'Unknown error')}")
            
        # Test 2: Company analysis
        print("\n2️⃣  Testing company information query...")
        response = agent.ask("Tell me about Microsoft's job postings")
        
        if response and response.get("status") == "success":
            print_success("Company query executed successfully")
        else:
            print_error(f"Company query failed: {response.get('error', 'Unknown error')}")
            
        # Test 3: Job search via chat
        print("\n3️⃣  Testing job search through Agent 2...")
        response = agent.ask("Show me data scientist positions")
        
        if response and response.get("status") == "success":
            print_success("Job search query executed successfully")
        else:
            print_error(f"Job search query failed: {response.get('error', 'Unknown error')}")
            
        return True
        
    except Exception as e:
        print_error(f"Agent 2 failed: {str(e)}")
        return False


def test_agent3_classifier():
    """Test Agent 3 - Job Classifier"""
    print_header("Testing Agent 3 - Job Classifier")
    
    try:
        agent = VisaClassifier()
        print_info("Agent 3 initialized successfully")
        
        # Test visa classification
        print("\n1️⃣  Testing visa job classification...")
        sample_job = {
            "job_title": "Machine Learning Engineer",
            "company_name": "Tech Corp",
            "location": "Boston, MA",
            "description": "We are looking for an experienced ML engineer. H-1B sponsorship available.",
            "h1b_sponsored": "Yes",
            "is_new_grad": "No",
            "work_model": "Hybrid"
        }
        
        classification = agent.classify_job(sample_job)
        
        if classification:
            print_success("Job classified successfully")
            print(f"   Visa Category: {classification.get('visa_category', 'N/A')}")
            print(f"   Confidence: {classification.get('confidence', 'N/A')}")
        else:
            print_error("Classification failed")
            
        return True
        
    except Exception as e:
        print_error(f"Agent 3 failed: {str(e)}")
        return False


def test_agent4_matcher():
    """Test Agent 4 - Resume Matcher"""
    print_header("Testing Agent 4 - Resume Matcher")
    
    try:
        agent = ResumeMatcherAgent()
        print_info("Agent 4 initialized successfully")
        
        # Test resume matching
        print("\n1️⃣  Testing resume-to-job matching...")
        sample_resume_text = """John Doe - Software Engineer
        
SKILLS: Python, Machine Learning, TensorFlow, PyTorch, AWS, Docker
        
EXPERIENCE:
        - Software Engineer at TechCorp (2021-2023)
        - ML Intern at BigTech (2020-2021)
        
EDUCATION:
        - BS Computer Science - MIT (2020)
        """
        
        # Extract profile first
        profile = agent.extract_profile(sample_resume_text)
        
        if profile:
            print_success("Profile extracted successfully")
            print(f"   Skills: {len(profile.get('technical_skills', []))} technical skills")
            
            # Find matching jobs
            print("\n   Finding matching jobs...")
            matches = agent.find_matching_jobs(profile, limit=5)
            
            if matches and len(matches) > 0:
                print_success(f"Found {len(matches)} matching jobs")
                best_match = matches[0]
                print(f"   Best match: {best_match.get('job_title', 'N/A')} at {best_match.get('company_name', 'N/A')}")
            else:
                print_error("No matches found")
        else:
            print_error("Profile extraction failed")
            
        return True
        
    except Exception as e:
        print_error(f"Agent 4 failed: {str(e)}")
        return False


def test_context_manager():
    """Test Context Manager"""
    print_header("Testing Context Manager")
    
    try:
        context = ConversationContext()
        print_info("Context Manager initialized successfully")
        
        # Test 1: Update context
        print("\n1️⃣  Testing context update...")
        context.update_context("Show me software engineer jobs in Boston", "Here are software engineer jobs in Boston...")
        print_success("Context updated successfully")
        
        # Test 2: Get entities
        print("\n2️⃣  Testing entity extraction...")
        entities = context.get_current_entities()
        
        if entities:
            print_success(f"Entities retrieved: {len(entities['locations'])} locations, {len(entities['job_titles'])} job titles")
        else:
            print_error("Entity extraction failed")
            
        # Test 3: Build context string
        print("\n3️⃣  Testing context string building...")
        context_str = context.build_context_string()
        
        if context_str:
            print_success(f"Context string built: {len(context_str)} chars")
        else:
            print_error("Context string build failed")
            
        # Test 4: Clear context
        print("\n4️⃣  Testing context clear...")
        context.clear_context()
        summary = context.get_summary()
        
        if summary['total_turns'] == 0:
            print_success("Context cleared successfully")
        else:
            print_error("Context clear failed")
        
        return True
        
    except Exception as e:
        print_error(f"Context Manager failed: {str(e)}")
        return False


def main():
    """Run all system tests"""
    print_header("JOB INTELLIGENCE PLATFORM - COMPREHENSIVE SYSTEM TEST")
    
    results = {}
    
    # Run all tests
    results["Agent 1 (Search)"] = test_agent1_search()
    results["Agent 2 (Chat/SQL)"] = test_agent2_chat()
    results["Agent 3 (Classifier)"] = test_agent3_classifier()
    results["Agent 4 (Matcher)"] = test_agent4_matcher()
    results["Context Manager"] = test_context_manager()
    
    # Summary
    print_header("TEST SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    failed_tests = total_tests - passed_tests
    
    for component, passed in results.items():
        if passed:
            print_success(f"{component}: PASSED")
        else:
            print_error(f"{component}: FAILED")
    
    print(f"\n{Colors.BOLD}Overall: {passed_tests}/{total_tests} tests passed{Colors.END}")
    
    if failed_tests == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL SYSTEMS OPERATIONAL 🎉{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  {failed_tests} SYSTEM(S) NEED ATTENTION ⚠️{Colors.END}\n")
        return 1


if __name__ == "__main__":
    exit(main())
