from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings  # Importa el objeto de configuración desde config.py

# Configuración de la base de datos
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependencia para obtener la sesión de base de datos en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
