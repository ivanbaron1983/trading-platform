# ~/project/backend/app/main.py

from fastapi import FastAPI

# Crear la instancia principal de la aplicación
app = FastAPI()

# Ruta principal
@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading Platform API"}

# Ruta para verificar el estado del servidor
@app.get("/status")
def get_status():
    return {"status": "Server is running perfectly"}

