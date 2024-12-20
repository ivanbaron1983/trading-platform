import os
import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text  # Asegurarse de importar text para consultas SQL
from sqlalchemy.orm import sessionmaker
from backend.app.db import SessionLocal, engine
from backend.app.models import SP500IntradayData
from dotenv import load_dotenv

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("sp500_debug_tools.log"),
        logging.StreamHandler()
    ]
)

# Cargar variables de entorno
load_dotenv()

def check_database_connection():
    """
    Verifica la conexión a la base de datos.
    """
    logging.info("Paso 1: Verificar conexión a la base de datos.")
    try:
        db_session = SessionLocal()
        db_session.execute(text("SELECT 1"))  # Usar text() para consultas SQL
        logging.info("Conexión a la base de datos exitosa.")
        db_session.close()
    except SQLAlchemyError as e:
        logging.error(f"Error de conexión a la base de datos: {e}")
        raise

def check_intraday_table():
    """
    Verifica si la tabla sp500_intraday_data tiene datos.
    """
    logging.info("Paso 2: Verificar si la tabla 'sp500_intraday_data' tiene datos.")
    try:
        db_session = SessionLocal()
        count = db_session.query(SP500IntradayData).count()
        if count > 0:
            logging.info(f"La tabla 'sp500_intraday_data' contiene {count} registros.")
        else:
            logging.warning("La tabla 'sp500_intraday_data' está vacía.")
        db_session.close()
    except SQLAlchemyError as e:
        logging.error(f"Error al consultar la tabla 'sp500_intraday_data': {e}")
        raise

def list_symbols_in_intraday_table():
    """
    Lista los símbolos únicos presentes en la tabla sp500_intraday_data.
    """
    logging.info("Paso 3: Listar símbolos únicos en la tabla 'sp500_intraday_data'.")
    try:
        db_session = SessionLocal()
        symbols = db_session.query(SP500IntradayData.symbol).distinct().all()
        if symbols:
            symbol_list = [s[0] for s in symbols]
            logging.info(f"Símbolos encontrados: {symbol_list}")
        else:
            logging.warning("No se encontraron símbolos en la tabla 'sp500_intraday_data'.")
        db_session.close()
    except SQLAlchemyError as e:
        logging.error(f"Error al listar los símbolos de 'sp500_intraday_data': {e}")
        raise

def clear_intraday_table():
    """
    Limpia la tabla sp500_intraday_data eliminando todos los registros.
    """
    logging.info("Paso 4: Limpiar la tabla 'sp500_intraday_data'.")
    try:
        db_session = SessionLocal()
        db_session.execute(text("TRUNCATE TABLE sp500_intraday_data"))
        db_session.commit()
        logging.info("La tabla 'sp500_intraday_data' ha sido limpiada exitosamente.")
        db_session.close()
    except SQLAlchemyError as e:
        logging.error(f"Error al limpiar la tabla 'sp500_intraday_data': {e}")
        raise

def debug_sp500_tools():
    """
    Ejecuta las herramientas de depuración para S&P 500.
    """
    logging.info("Iniciando herramientas de depuración para S&P 500...")
    check_database_connection()
    check_intraday_table()
    list_symbols_in_intraday_table()
    # Descomentar si deseas limpiar la tabla durante la depuración
    # clear_intraday_table()

if __name__ == "__main__":
    debug_sp500_tools()


