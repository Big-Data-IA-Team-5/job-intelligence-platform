"""
Comprehensive Query Test Suite for Agent 2 Fine-Tuning
Tests all query patterns to ensure robust understanding
"""

QUERY_TEST_SUITE = {
    
    # ========================================
    # 1. JOB SEARCH QUERIES
    # ========================================
    "job_search": {
        
        "basic": [
            "find jobs",
            "show me jobs",
            "looking for a job",
            "job openings",
            "what jobs are available",
            "list all positions",
            "search for jobs",
            "I need a job",
        ],
        
        "with_role": [
            "software engineer jobs",
            "data analyst positions",
            "machine learning engineer openings",
            "frontend developer jobs",
            "product manager roles",
            "devops engineer positions",
            "data scientist jobs",
            "backend engineer openings",
        ],
        
        "with_location": [
            "jobs in Boston",
            "positions in Seattle",
            "openings in New York",
            "jobs in Bay Area",
            "positions in Austin",
            "California jobs",
            "Massachusetts openings",
            "remote jobs",
        ],
        
        "role_plus_location": [
            "software engineer jobs in Boston",
            "data analyst in Seattle",
            "ML engineer positions in San Francisco",
            "remote software developer jobs",
            "NYC data scientist openings",
            "backend engineer in Austin",
        ],
        
        "with_visa": [
            "CPT internships",
            "OPT jobs",
            "H-1B sponsor companies",
            "jobs that sponsor visas",
            "internships for international students",
            "F-1 friendly jobs",
            "companies sponsoring H-1B",
            "visa sponsorship available",
        ],
        
        "role_location_visa": [
            "CPT software engineering internships in Boston",
            "OPT data analyst jobs in Seattle",
            "H-1B software engineer positions in NYC",
            "remote CPT internships",
            "entry level OPT jobs in California",
        ],
        
        "with_company": [
            "jobs at Amazon",
            "Google openings",
            "Microsoft positions",
            "work at Meta",
            "Apple careers",
            "Snowflake jobs",
        ],
        
        "company_role_location": [
            "software engineer at Amazon in Seattle",
            "data analyst at Google in San Francisco",
            "ML engineer at Microsoft remote",
            "product manager at Meta in NYC",
        ],
        
        "with_experience": [
            "entry level software engineer",
            "junior data analyst",
            "new grad positions",
            "intern jobs",
            "senior engineer jobs",
            "mid level developer",
        ],
        
        "with_work_model": [
            "remote software engineer jobs",
            "hybrid data analyst positions",
            "on-site engineer jobs",
            "work from home jobs",
            "fully remote positions",
        ],
        
        "with_salary": [
            "jobs paying over 100k",
            "positions with 80k+ salary",
            "high paying software jobs",
            "100k-150k data engineer jobs",
        ],
        
        "complex_multi_criteria": [
            "remote CPT software engineering internships paying 60k+",
            "H-1B data engineer jobs in Boston at companies with high approval rates",
            "entry level OPT jobs at FAANG companies in Seattle",
            "junior ML engineer remote positions with visa sponsorship",
            "internships in data science at top sponsors in Bay Area",
        ],
        
        "natural_language": [
            "I'm looking for data related jobs",
            "I want to work as a software engineer",
            "help me find an internship",
            "what jobs can I apply to",
            "I need CPT eligible positions",
            "show me opportunities in tech",
        ],
        
        "with_skills": [
            "Python developer jobs",
            "React frontend positions",
            "AWS cloud engineer jobs",
            "SQL data analyst",
            "Docker devops jobs",
        ],
        
        "edge_cases": [
            "show me 10 jobs",
            "find me anything",
            "jobs near me",
            "best jobs",
            "top companies",
            "latest openings",
        ],
    },
    
    # ========================================
    # 2. SALARY QUERIES
    # ========================================
    "salary": {
        
        "basic": [
            "what's the salary",
            "how much do they pay",
            "average compensation",
            "salary range",
            "pay scale",
        ],
        
        "with_role": [
            "software engineer salary",
            "data analyst pay",
            "how much do ML engineers make",
            "product manager compensation",
            "devops engineer salary range",
        ],
        
        "role_plus_location": [
            "software engineer salary in Boston",
            "data analyst pay in Seattle",
            "ML engineer compensation in San Francisco",
            "how much do engineers make in NYC",
            "California tech salaries",
        ],
        
        "role_location_company": [
            "software engineer salary at Amazon",
            "how much does Google pay data analysts",
            "Microsoft software engineer compensation in Seattle",
            "Meta product manager salary in California",
        ],
        
        "comparative": [
            "compare salaries in Boston vs Seattle",
            "which city pays more for engineers",
            "best paying locations for data roles",
        ],
        
        "with_experience": [
            "entry level software engineer salary",
            "new grad data analyst pay",
            "senior ML engineer compensation",
            "intern pay rates",
        ],
        
        "negotiation_focused": [
            "how to negotiate salary",
            "is 80k good for software engineer",
            "should I accept 100k for data analyst",
            "salary negotiation tips",
        ],
    },
    
    # ========================================
    # 3. H-1B SPONSORSHIP QUERIES
    # ========================================
    "h1b_sponsorship": {
        
        "basic": [
            "do they sponsor H-1B",
            "H-1B sponsorship",
            "visa sponsorship",
            "companies that sponsor",
        ],
        
        "with_company": [
            "does Amazon sponsor H-1B",
            "Google H-1B sponsorship",
            "will Microsoft sponsor my visa",
            "Meta H-1B policy",
            "Apple visa sponsorship",
        ],
        
        "approval_rates": [
            "Amazon H-1B approval rate",
            "what's Google's H-1B success rate",
            "Microsoft visa approval percentage",
            "is Netflix good for H-1B",
        ],
        
        "with_role": [
            "which companies sponsor H-1B for software engineers",
            "data analyst H-1B sponsors",
            "ML engineer visa sponsorship companies",
        ],
        
        "risk_assessment": [
            "is Amazon safe for H-1B",
            "risky H-1B sponsors",
            "companies with low approval rates",
            "safe visa sponsorship companies",
        ],
        
        "statistics": [
            "top H-1B sponsors",
            "companies with most H-1B approvals",
            "highest H-1B approval rates",
            "best companies for visa sponsorship",
        ],
    },
    
    # ========================================
    # 4. CONTACT INFORMATION QUERIES
    # ========================================
    "contact": {
        
        "employer_contact": [
            "who to contact at Amazon for H-1B",
            "Amazon immigration email",
            "Google H-1B contact",
            "Microsoft visa team email",
            "HR contact for sponsorship at Meta",
        ],
        
        "attorney_info": [
            "Amazon immigration attorney",
            "which law firm does Google use",
            "attorney for Microsoft H-1B",
            "immigration lawyers at Amazon",
            "Google's law firm for visa",
        ],
        
        "location_based": [
            "immigration attorneys in Boston",
            "H-1B lawyers in Seattle",
            "visa attorneys in San Francisco",
            "best immigration law firms in NYC",
            "California H-1B attorneys",
            "Massachusetts top attorney contact number",
            "immigration lawyers in New York",
            "top attorneys in Texas",
        ],
        
        "law_firm_specific": [
            "Fragomen law firm contact",
            "who uses Fragomen",
            "best immigration law firms",
            "top H-1B attorneys",
        ],
    },
    
    # ========================================
    # 5. COMPANY COMPARISON QUERIES
    # ========================================
    "comparison": {
        
        "two_companies": [
            "compare Amazon and Google",
            "Amazon vs Microsoft",
            "Google versus Meta",
            "Apple or Google for H-1B",
            "Netflix vs Uber sponsorship",
        ],
        
        "multiple_companies": [
            "compare Amazon, Google, and Microsoft",
            "best among FAANG for H-1B",
            "rank top tech companies for sponsorship",
        ],
        
        "specific_criteria": [
            "which has better approval rate: Amazon or Google",
            "compare salaries at Amazon vs Microsoft",
            "which pays more: Google or Meta",
        ],
    },
    
    # ========================================
    # 6. RESUME ANALYSIS QUERIES
    # ========================================
    "resume": {
        
        "analysis": [
            "analyze my resume",
            "review my CV",
            "feedback on my resume",
            "how's my resume",
            "resume critique",
        ],
        
        "matching": [
            "what jobs match my resume",
            "find jobs for my profile",
            "which positions am I qualified for",
            "match my skills to jobs",
        ],
        
        "improvement": [
            "how to improve my resume",
            "what skills should I add",
            "resume optimization tips",
            "make my resume better",
        ],
    },
    
    # ========================================
    # 7. CAREER ADVICE QUERIES
    # ========================================
    "career": [
        "career advice",
        "what should I do next",
        "career path for data engineer",
        "how to transition to ML engineer",
        "career growth in software engineering",
        "should I apply to this job",
        "is this a good career move",
    ],
    
    # ========================================
    # 8. EDGE CASES & VARIATIONS
    # ========================================
    "edge_cases": {
        
        "typos": [
            "sofware engineer jobs",  # missing 't'
            "data analist",  # wrong spelling
            "machne learning",  # typo
            "salery information",  # wrong spelling
        ],
        
        "abbreviations": [
            "SDE jobs",  # Software Development Engineer
            "SWE positions",  # Software Engineer
            "DS roles",  # Data Scientist
            "PM jobs",  # Product Manager
            "MLE openings",  # ML Engineer
        ],
        
        "informal": [
            "gimme some jobs",
            "any openings?",
            "what u got",
            "hook me up with jobs",
            "jobs pls",
        ],
        
        "vague": [
            "I want a job",
            "find something for me",
            "what do you have",
            "show me everything",
            "anything available",
        ],
        
        "multi_question": [
            "what's the salary and does Amazon sponsor H-1B",
            "find jobs in Boston and tell me about salaries",
            "compare Google vs Amazon and show me their jobs",
        ],
        
        "follow_ups": [
            "what about Google?",  # needs context from previous
            "and the salary?",  # continuation
            "tell me more",  # vague follow-up
            "what else",  # asking for more results
        ],
    },
    
    # ========================================
    # 9. NON-JOB QUERIES (Should Reject)
    # ========================================
    "should_reject": [
        "what's the weather",
        "tell me a joke",
        "what's 2+2",
        "write me a poem",
        "latest news",
        "stock prices",
        "who won the game",
        "restaurant recommendations",
    ],
}


# ========================================
# TEST RUNNER
# ========================================

def run_comprehensive_test_suite(agent):
    """
    Run all query combinations to test Agent 2 robustness.
    
    Usage:
        from snowflake.agents.agent2_chat import JobIntelligenceAgent
        agent = JobIntelligenceAgent()
        run_comprehensive_test_suite(agent)
        agent.close()
    """
    
    print("="*80)
    print("🧪 COMPREHENSIVE AGENT 2 TEST SUITE")
    print("="*80)
    print(f"\nTotal test queries: {sum(len(v) if isinstance(v, list) else sum(len(subv) for subv in v.values()) for v in QUERY_TEST_SUITE.values())}")
    print("\n" + "="*80)
    
    results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    # Test each category
    for category, queries in QUERY_TEST_SUITE.items():
        print(f"\n📁 CATEGORY: {category.upper()}")
        print("-"*80)
        
        if isinstance(queries, dict):
            for subcategory, subqueries in queries.items():
                print(f"\n  📂 {subcategory}:")
                
                for query in subqueries[:3]:  # Test first 3 of each subcategory
                    try:
                        print(f"    ❓ {query}")
                        result = agent.ask(query)
                        
                        if result.get('confidence', 0) > 0.5:
                            print(f"       ✅ Confidence: {result['confidence']:.0%}")
                            results["passed"] += 1
                        else:
                            print(f"       ⚠️  Low confidence: {result['confidence']:.0%}")
                            results["failed"] += 1
                            results["errors"].append({
                                "query": query,
                                "confidence": result['confidence'],
                                "answer": result['answer'][:100]
                            })
                    
                    except Exception as e:
                        print(f"       ❌ Error: {e}")
                        results["failed"] += 1
                        results["errors"].append({
                            "query": query,
                            "error": str(e)
                        })
        
        else:  # List directly
            for query in queries[:3]:
                try:
                    print(f"    ❓ {query}")
                    result = agent.ask(query)
                    
                    if result.get('confidence', 0) > 0.5:
                        print(f"       ✅ Confidence: {result['confidence']:.0%}")
                        results["passed"] += 1
                    else:
                        print(f"       ⚠️  Low confidence: {result['confidence']:.0%}")
                        results["failed"] += 1
                
                except Exception as e:
                    print(f"       ❌ Error: {e}")
                    results["failed"] += 1
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"\n✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"Success Rate: {results['passed'] / (results['passed'] + results['failed']) * 100:.1f}%")
    
    if results['errors']:
        print(f"\n🔍 First 5 Failures:")
        for error in results['errors'][:5]:
            print(f"\n  Query: {error['query']}")
            if 'confidence' in error:
                print(f"  Confidence: {error['confidence']:.0%}")
            if 'error' in error:
                print(f"  Error: {error['error']}")
    
    return results


# ========================================
# GOLDEN TEST SET (For Accuracy Measurement)
# ========================================

GOLDEN_TEST_SET = [
    # Format: (query, expected_intent, expected_entities)
    
    # Job Search
    ("find software engineer jobs in Boston", "job_search", {"job_title": "software engineer", "location": "boston"}),
    ("CPT internships at Amazon", "job_search", {"visa": "CPT", "company": "amazon"}),
    ("remote data analyst positions", "job_search", {"job_title": "data analyst", "work_model": "remote"}),
    
    # Salary
    ("what's the salary for data engineer in Seattle", "salary_info", {"job_title": "data engineer", "location": "seattle"}),
    ("how much do software engineers make at Google", "salary_info", {"job_title": "software engineer", "company": "google"}),
    
    # H-1B Sponsorship
    ("does Amazon sponsor H-1B", "h1b_sponsorship", {"company": "amazon"}),
    ("which companies sponsor visas for ML engineers", "h1b_sponsorship", {"job_title": "ml engineer"}),
    
    # Contact
    ("who to contact at Microsoft for H-1B", "contact_info", {"company": "microsoft"}),
    ("immigration attorneys in Boston", "contact_info", {"location": "boston"}),
    ("Massachusetts top attorney contact number", "contact_info", {"location": "massachusetts"}),
    
    # Comparison
    ("compare Amazon and Google", "company_comparison", {"companies": ["amazon", "google"]}),
    
    # Resume
    ("analyze my resume", "resume_analysis", {}),
    
    # Should Reject
    ("what's the weather", "general", {}),
]


def test_golden_set(agent):
    """Test against golden set for accuracy measurement."""
    
    print("\n" + "="*80)
    print("🎯 GOLDEN SET ACCURACY TEST")
    print("="*80)
    
    correct_intent = 0
    correct_entities = 0
    total = len(GOLDEN_TEST_SET)
    
    for i, (query, expected_intent, expected_entities) in enumerate(GOLDEN_TEST_SET, 1):
        print(f"\n{i}. Testing: {query}")
        
        result = agent.ask(query)
        detected_intent = "unknown"  # Would need to add intent to response
        
        # For now, check if appropriate method was called by checking answer content
        if expected_intent == "job_search" and "Found" in result['answer']:
            detected_intent = "job_search"
        elif expected_intent == "salary_info" and ("Salary" in result['answer'] or "$" in result['answer']):
            detected_intent = "salary_info"
        elif expected_intent == "h1b_sponsorship" and ("Sponsor" in result['answer'] or "approval" in result['answer'].lower()):
            detected_intent = "h1b_sponsorship"
        elif expected_intent == "contact_info" and ("Contact" in result['answer'] or "Email" in result['answer'] or "Attorney" in result['answer']):
            detected_intent = "contact_info"
        elif expected_intent == "company_comparison" and "compare" in result['answer'].lower():
            detected_intent = "company_comparison"
        elif expected_intent == "general" and "specialized" in result['answer'].lower():
            detected_intent = "general"
        
        if detected_intent == expected_intent:
            print(f"   ✅ Intent: {detected_intent}")
            correct_intent += 1
        else:
            print(f"   ❌ Intent: Expected {expected_intent}, got {detected_intent}")
            print(f"      Answer preview: {result['answer'][:100]}...")
    
    accuracy = (correct_intent / total) * 100
    print(f"\n📊 ACCURACY: {accuracy:.1f}% ({correct_intent}/{total} correct)")
    
    return accuracy


# ========================================
# MAIN TEST EXECUTION
# ========================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/Users/pranavpatel/Desktop/job-intelligence-platform')
    from snowflake.agents.agent2_chat import JobIntelligenceAgent
    
    print("\n🚀 Starting Comprehensive Agent 2 Testing...")
    print("This will take 5-10 minutes to run all tests.\n")
    
    agent = JobIntelligenceAgent()
    
    # Run comprehensive suite
    results = run_comprehensive_test_suite(agent)
    
    # Run golden set
    accuracy = test_golden_set(agent)
    
    agent.close()
    
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE!")
    print("="*80)
    print(f"\nOverall Success Rate: {results['passed'] / (results['passed'] + results['failed']) * 100:.1f}%")
    print(f"Golden Set Accuracy: {accuracy:.1f}%")
    print("\n" + "="*80)
