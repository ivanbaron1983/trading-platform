# ~/project/backend/app/main.py

from fastapi import FastAPI
from .routes import users  # Importar las rutas de usuarios

# Crear instancia de la aplicación
app = FastAPI()

# Incluir rutas
app.include_router(users.router)

@app.get("/")
def read_root():
    """
    Ruta principal para verificar que la aplicación está funcionando.
    """
    return {"message": "Welcome to Trading Platform"}
