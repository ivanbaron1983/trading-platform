import unittest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

class TestUsers(unittest.TestCase):
    """
    Pruebas unitarias para el módulo de usuarios.
    """
    def test_users_endpoint(self):
        """
        Verifica que la ruta de usuarios devuelva un código de estado 200.
        """
        response = client.get("/users")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
