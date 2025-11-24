"""
Unit tests for Agent 4 - Resume Matcher
"""
import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from snowflake.agents.agent4_matcher import ResumeMatcherAgent


class TestAgent4Matcher(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Initialize matcher once for all tests."""
        cls.matcher = ResumeMatcherAgent()
        
        # Sample resume for testing
        cls.test_resume = """
        John Doe
        Software Engineer
        
        EXPERIENCE:
        - Software Developer at TechCorp (2 years)
        - Intern at StartupXYZ (6 months)
        Total: 2.5 years
        
        SKILLS:
        - Programming: Python, JavaScript, React, SQL
        - Tools: Git, Docker, AWS
        
        EDUCATION:
        Master of Science in Computer Science
        Northeastern University, 2024
        
        WORK AUTHORIZATION:
        F-1 OPT (expires June 2026)
        
        OBJECTIVE:
        Seeking Software Engineer or Data Engineer positions
        in Boston area or remote. Expected salary: $85,000+
        """
    
    @classmethod
    def tearDownClass(cls):
        """Close connection after all tests."""
        cls.matcher.close()
    
    def test_profile_extraction(self):
        """Test resume profile extraction."""
        profile = self.matcher.extract_profile(self.test_resume)
        
        self.assertIsInstance(profile, dict)
        self.assertIn('technical_skills', profile)
        self.assertIn('total_experience_years', profile)
        self.assertIn('education_level', profile)
        self.assertIn('work_authorization', profile)
        
        # Check that some skills were extracted
        self.assertGreater(len(profile['technical_skills']), 0)
    
    def test_profile_has_valid_experience(self):
        """Test that extracted experience is a valid number."""
        profile = self.matcher.extract_profile(self.test_resume)
        
        self.assertIsInstance(profile['total_experience_years'], (int, float))
        self.assertGreaterEqual(profile['total_experience_years'], 0)
    
    def test_find_matching_jobs(self):
        """Test finding matching jobs based on profile."""
        profile = {
            'technical_skills': ['Python', 'SQL'],
            'work_authorization': 'F-1 OPT',
            'total_experience_years': 2.5,
            'education_level': "Master's",
            'desired_roles': ['Software Engineer'],
            'preferred_locations': ['Boston'],
            'salary_min': 85000
        }
        
        jobs = self.matcher.find_matching_jobs(profile, limit=10)
        
        self.assertIsInstance(jobs, list)
        # Jobs may be empty if database has no matching jobs
        for job in jobs:
            self.assertIn('JOB_ID', job)
            self.assertIn('TITLE', job)
            self.assertIn('VISA_CATEGORY', job)
    
    def test_rerank_jobs(self):
        """Test job re-ranking with scores."""
        profile = {
            'technical_skills': ['Python', 'SQL'],
            'work_authorization': 'F-1 OPT',
            'total_experience_years': 2.5,
            'preferred_locations': ['Boston'],
            'desired_roles': ['Software Engineer']
        }
        
        # Mock jobs for testing
        mock_jobs = [
            {
                'JOB_ID': 'test1',
                'TITLE': 'Software Engineer',
                'COMPANY': 'Test Corp',
                'DESCRIPTION': 'Python and SQL required',
                'LOCATION': 'Boston, MA',
                'VISA_CATEGORY': 'OPT',
                'H1B_SPONSOR': True
            }
        ]
        
        ranked = self.matcher.rerank_jobs(profile, mock_jobs)
        
        self.assertIsInstance(ranked, list)
        if len(ranked) > 0:
            match = ranked[0]
            self.assertIn('overall_score', match)
            self.assertIn('skills_score', match)
            self.assertIn('reasoning', match)
            self.assertGreaterEqual(match['overall_score'], 0)
            self.assertLessEqual(match['overall_score'], 100)
    
    def test_complete_matching_pipeline(self):
        """Test complete matching pipeline."""
        result = self.matcher.match_resume(
            resume_id='test_resume_unittest',
            resume_text=self.test_resume
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('resume_id', result)
        self.assertIn('profile', result)
        self.assertIn('top_matches', result)
        self.assertIn('total_candidates', result)
        
        self.assertEqual(result['resume_id'], 'test_resume_unittest')
        self.assertIsInstance(result['profile'], dict)
        self.assertIsInstance(result['top_matches'], list)
        self.assertIsInstance(result['total_candidates'], int)


if __name__ == '__main__':
    unittest.main()
