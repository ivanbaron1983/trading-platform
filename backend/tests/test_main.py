# ~/project/backend/tests/test_main.py
import unittest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

class TestMain(unittest.TestCase):
    """
    Pruebas unitarias para la aplicación principal.
    """
    def test_app_running(self):
        """
        Verifica que la ruta principal esté activa y devuelva un código de estado 200.
        """
        response = client.get("/")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
