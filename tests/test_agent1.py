"""
Unit tests for Agent 1
"""
import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from snowflake.agents.agent1_search import JobSearchAgent


class TestAgent1(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.agent = JobSearchAgent()
    
    @classmethod
    def tearDownClass(cls):
        cls.agent.close()
    
    def test_search_all_jobs(self):
        result = self.agent.search("Show me all jobs")
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['total'], 0)
    
    def test_cpt_search(self):
        result = self.agent.search("CPT internships")
        self.assertEqual(result['status'], 'success')
        if result['total'] > 0:
            self.assertEqual(result['jobs'][0]['VISA_CATEGORY'], 'CPT')
    
    def test_h1b_search(self):
        result = self.agent.search("H-1B sponsors")
        self.assertEqual(result['status'], 'success')
        if result['total'] > 0:
            self.assertTrue(result['jobs'][0]['H1B_SPONSOR'])
    
    def test_empty_query(self):
        result = self.agent.search("")
        self.assertEqual(result['status'], 'error')
    
    def test_with_filters(self):
        result = self.agent.search("Jobs", {'limit': 5})
        self.assertEqual(result['status'], 'success')
        self.assertLessEqual(result['total'], 5)


if __name__ == '__main__':
    unittest.main()