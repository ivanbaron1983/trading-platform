import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.config import settings
from dotenv import load_dotenv


# URL de conexión a PostgreSQL
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Crear el motor de la base de datos
engine = create_engine(DATABASE_URL)

# Configurar la sesión para la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear una clase base para los modelos
Base = declarative_base()

# Dependencia para obtener la sesión de base de datos en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
