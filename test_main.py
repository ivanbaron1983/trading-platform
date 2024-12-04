# ~/project/backend/tests/test_main.py
import unittest
from app.main import app

class TestMain(unittest.TestCase):
    def test_app_running(self):
        response = app.test_client().get('/')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
