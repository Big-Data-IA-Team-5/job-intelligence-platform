"""
Unit tests for Agent 3 - Visa Classifier
"""
import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from snowflake.agents.agent3_classifier import VisaClassifier


class TestAgent3Classifier(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Initialize classifier once for all tests."""
        cls.classifier = VisaClassifier()
    
    @classmethod
    def tearDownClass(cls):
        """Close connection after all tests."""
        cls.classifier.close()
    
    def test_cpt_classification(self):
        """Test CPT internship classification."""
        job = {
            'title': 'Software Engineer Intern',
            'company': 'Microsoft',
            'location': 'Boston, MA',
            'description': 'Summer internship for students. CPT eligible. Work on Azure cloud.'
        }
        
        result = self.classifier.classify_job(job, use_cache=False)
        
        self.assertEqual(result['visa_category'], 'CPT')
        self.assertGreaterEqual(result['confidence'], 0.7)
        self.assertIn('intern', [s.lower() for s in result['signals']])
    
    def test_h1b_classification(self):
        """Test H-1B sponsorship classification."""
        job = {
            'title': 'Data Analyst',
            'company': 'Google',
            'location': 'New York, NY',
            'description': 'We sponsor H-1B visas for qualified candidates. Full-time position.'
        }
        
        result = self.classifier.classify_job(job, use_cache=False)
        
        self.assertEqual(result['visa_category'], 'H-1B')
        self.assertGreaterEqual(result['confidence'], 0.7)
    
    def test_us_only_classification(self):
        """Test US citizenship required classification."""
        job = {
            'title': 'Defense Software Engineer',
            'company': 'Raytheon',
            'location': 'Washington, DC',
            'description': 'US citizenship required. Security clearance mandatory.'
        }
        
        result = self.classifier.classify_job(job, use_cache=False)
        
        self.assertEqual(result['visa_category'], 'US-Only')
        self.assertGreaterEqual(result['confidence'], 0.7)
    
    def test_opt_classification(self):
        """Test OPT new grad classification."""
        job = {
            'title': 'Junior Data Engineer',
            'company': 'Amazon',
            'location': 'Remote',
            'description': 'Entry level for recent graduates. OPT candidates welcome.'
        }
        
        result = self.classifier.classify_job(job, use_cache=False)
        
        self.assertEqual(result['visa_category'], 'OPT')
        self.assertGreaterEqual(result['confidence'], 0.6)
    
    def test_confidence_scores(self):
        """Test that confidence scores are in valid range."""
        job = {
            'title': 'Test Job',
            'company': 'Test Company',
            'location': 'Test Location',
            'description': 'Test description'
        }
        
        result = self.classifier.classify_job(job, use_cache=False)
        
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertLessEqual(result['confidence'], 1.0)
    
    def test_classification_stats(self):
        """Test getting classification statistics."""
        stats = self.classifier.get_classification_stats()
        
        self.assertIsInstance(stats, dict)
        for category, data in stats.items():
            self.assertIn('count', data)
            self.assertIsInstance(data['count'], int)


if __name__ == '__main__':
    unittest.main()
