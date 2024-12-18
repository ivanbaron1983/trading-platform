import os
import pandas as pd
import requests
from sqlalchemy.orm import Session
from backend.app.db import SessionLocal
from backend.app.models import SP500IntradayData  # Ajusta según tu modelo intradía
from dotenv import load_dotenv
import logging
import time

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("polygon_intraday_loader.log"),
        logging.StreamHandler()
    ]
)

# Cargar la clave API desde el archivo .env
load_dotenv()
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
if not POLYGON_API_KEY:
    raise ValueError("La clave API de Polygon.io no está configurada en el archivo .env")

# Ruta para guardar datos temporalmente
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../../data/sp500_intraday")
os.makedirs(DATA_DIR, exist_ok=True)

# Configuración de límites de solicitudes
REQUESTS_LIMIT = 5  # Límite de llamadas por minuto para la cuenta Basic
REQUEST_COUNT = 0
START_TIME = time.time()

# Función para manejar el límite de solicitudes
def wait_if_limit_reached():
    global REQUEST_COUNT, START_TIME
    if REQUEST_COUNT >= REQUESTS_LIMIT:
        elapsed_time = time.time() - START_TIME
        if elapsed_time < 60:
            wait_time = 60 - elapsed_time
            logging.info(f"Límite alcanzado. Esperando {wait_time:.2f} segundos...")
            time.sleep(wait_time)
        REQUEST_COUNT = 0
        START_TIME = time.time()

# Función para verificar disponibilidad del ticker
def check_ticker_availability(symbol):
    """Consulta la fecha desde la cual hay datos disponibles para un símbolo en Polygon.io."""
    url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
    params = {"apiKey": POLYGON_API_KEY}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if "results" in data and "list_date" in data["results"]:
                return data["results"]["list_date"]
        else:
            logging.warning(f"No se pudo verificar disponibilidad para {symbol}: {response.status_code}")
    except Exception as e:
        logging.error(f"Error al verificar disponibilidad para {symbol}: {e}")
    return "2018-01-01"  # Fecha por defecto

# Función para descargar datos intradía
def download_intraday_data(symbol, start_date, end_date="2023-12-31", retries=3):
    """Descarga datos intradía de un símbolo desde Polygon.io."""
    global REQUEST_COUNT
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{start_date}/{end_date}"
    params = {"adjusted": "true", "sort": "asc", "apiKey": POLYGON_API_KEY}
    
    for attempt in range(retries):
        try:
            wait_if_limit_reached()  # Controlar límite de solicitudes
            response = requests.get(url, params=params)
            REQUEST_COUNT += 1

            if response.status_code == 200:
                data = response.json().get("results", [])
                if not data:
                    logging.warning(f"No se encontraron datos para {symbol}.")
                    return pd.DataFrame()

                # Convertir datos a DataFrame
                df = pd.DataFrame(data)
                df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
                df.rename(columns={
                    "o": "Open",
                    "h": "High",
                    "l": "Low",
                    "c": "Close",
                    "v": "Volume",
                    "timestamp": "Datetime"
                }, inplace=True)

                return df[["Datetime", "Open", "High", "Low", "Close", "Volume"]]
            else:
                logging.error(f"Error al descargar datos para {symbol}: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Error en el intento {attempt + 1} para {symbol}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Retraso exponencial antes de reintentar
    return pd.DataFrame()

# Limpieza de datos
def clean_data(data: pd.DataFrame):
    """Limpia y valida los datos descargados."""
    try:
        data.dropna(inplace=True)
        return data
    except Exception as e:
        logging.error(f"Error al limpiar datos: {e}")
        return pd.DataFrame()

# Guardar datos en la base de datos
def save_to_db(session: Session, symbol: str, data: pd.DataFrame):
    """Guarda datos intradía en la base de datos."""
    for _, row in data.iterrows():
        try:
            session.add(SP500IntradayData(
                symbol=symbol,
                datetime=row["Datetime"],
                open=row["Open"],
                high=row["High"],
                low=row["Low"],
                close=row["Close"],
                volume=row["Volume"]
            ))
        except Exception as e:
            logging.error(f"Error al guardar datos para {symbol}: {e}")
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Error al guardar datos en la base de datos: {e}")

# Descarga y almacenamiento de datos intradía
def download_sp500_intraday_data():
    """Descarga datos intradía para empresas del S&P 500 y los guarda en la base de datos."""
    sp500_companies = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    db_session = SessionLocal()

    try:
        for _, row in sp500_companies.iterrows():
            symbol = row["Symbol"]
            start_date = check_ticker_availability(symbol)
            logging.info(f"Descargando datos para {symbol} desde {start_date}...")
            intraday_data = download_intraday_data(symbol, start_date=start_date)

            if not intraday_data.empty:
                clean_data_frame = clean_data(intraday_data)
                if not clean_data_frame.empty:
                    save_to_db(db_session, symbol, clean_data_frame)
    finally:
        db_session.close()

if __name__ == "__main__":
    download_sp500_intraday_data()
