from backend.app.db import Base, engine  # Importar la base y el motor de la base de datos
from backend.app.models import User, SP500Data, SP500IntradayData  # Importar todos los modelos definidos

def create_missing_tables():
    """
    Crea todas las tablas definidas en los modelos si no existen en la base de datos.
    """
    print("Verificando y creando tablas faltantes...")
    Base.metadata.create_all(bind=engine)
    print("Tablas faltantes creadas con éxito.")

if __name__ == "__main__":
    create_missing_tables()
