import os
import pandas as pd
from alpaca_trade_api.rest import REST
from sqlalchemy.orm import Session
from backend.app.db import SessionLocal
from backend.app.models import SP500Data
from dotenv import load_dotenv
import logging
import time

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("sp500_data_loader.log"),
        logging.StreamHandler()
    ]
)

# Cargar variables de entorno del archivo .env
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError("Las claves API de Alpaca no están configuradas en el archivo .env")

# Configuración de Alpaca
alpaca_api = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")

# Ruta de la carpeta de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../../data/sp500")

# Crear la carpeta de datos
os.makedirs(DATA_DIR, exist_ok=True)
logging.info(f"Carpeta de datos asegurada: {DATA_DIR}")

def fetch_sp500_companies():
    """Obtiene la lista de empresas del S&P 500 desde Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url)
        sp500_table = tables[0]
        logging.info("Lista de empresas del S&P 500 obtenida con éxito.")
        return sp500_table[["Symbol", "Security"]]
    except Exception as e:
        logging.error(f"Error al obtener las empresas del S&P 500: {e}")
        return pd.DataFrame(columns=["Symbol", "Security"])

def download_stock_data(symbol, start_date="2000-01-01", retries=3):
    """Descarga los datos históricos de una acción desde Alpaca con manejo de errores y paginación."""
    for attempt in range(retries):
        try:
            # Obtener datos históricos diarios
            bars = alpaca_api.get_bars(
                symbol, timeframe="1Day", start=start_date, adjustment="all"
            ).df

            if bars.empty:
                logging.warning(f"No se encontraron datos para {symbol}.")
                return pd.DataFrame()

            # Procesar datos
            bars.reset_index(inplace=True)
            bars.rename(columns={
                'timestamp': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)

            bars["Adj Close"] = bars["Close"]  # Alpaca no proporciona "Adj Close", se iguala a "Close"
            logging.info(f"Datos descargados para {symbol}.")
            return bars
        except Exception as e:
            logging.error(f"Error al descargar los datos para {symbol}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Retraso exponencial antes de reintentar
            else:
                logging.error(f"Falló la descarga para {symbol} después de {retries} intentos.")
    return pd.DataFrame()

def clean_data(data: pd.DataFrame):
    """Limpia y valida los datos descargados."""
    try:
        required_columns = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logging.error(f"Columnas faltantes: {missing_columns}")
            return pd.DataFrame()

        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data["Open"] = pd.to_numeric(data["Open"], errors="coerce")
        data["High"] = pd.to_numeric(data["High"], errors="coerce")
        data["Low"] = pd.to_numeric(data["Low"], errors="coerce")
        data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
        data["Adj Close"] = pd.to_numeric(data["Adj Close"], errors="coerce")
        data["Volume"] = pd.to_numeric(data["Volume"], errors="coerce").fillna(0).astype(int)

        data.dropna(inplace=True)
        logging.info(f"Datos limpiados. Filas válidas: {len(data)}.")
        return data
    except Exception as e:
        logging.error(f"Error al limpiar los datos: {e}")
        return pd.DataFrame()

def save_or_update_data_to_db(session: Session, symbol: str, company_name: str, data: pd.DataFrame):
    """Guarda o actualiza los datos en la base de datos."""
    for _, row in data.iterrows():
        try:
            existing_record = session.query(SP500Data).filter(
                SP500Data.symbol == symbol, SP500Data.date == row["Date"]
            ).first()
            if existing_record:
                existing_record.open, existing_record.high = row["Open"], row["High"]
                existing_record.low, existing_record.close = row["Low"], row["Close"]
                existing_record.adj_close, existing_record.volume = row["Adj Close"], row["Volume"]
            else:
                session.add(SP500Data(
                    symbol=symbol,
                    name=company_name,
                    date=row["Date"],
                    open=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    adj_close=row["Adj Close"],
                    volume=row["Volume"],
                ))
        except Exception as e:
            logging.error(f"Error al guardar/actualizar el registro para {symbol}: {e}")
    try:
        session.commit()
        logging.info(f"Datos para {symbol} guardados/actualizados en la base de datos.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error al guardar datos en la base de datos: {e}")

def download_sp500_data():
    """Descarga datos históricos de empresas del S&P 500 y los guarda en la base de datos."""
    sp500_companies = fetch_sp500_companies()

    if not sp500_companies.empty:
        db_session = SessionLocal()
        try:
            for _, row in sp500_companies.iterrows():
                symbol, company_name = row["Symbol"], row["Security"]
                logging.info(f"Procesando {symbol} - {company_name}...")
                stock_data = download_stock_data(symbol)

                if not stock_data.empty:
                    clean_stock_data = clean_data(stock_data)
                    if not clean_stock_data.empty:
                        save_or_update_data_to_db(db_session, symbol, company_name, clean_stock_data)

                        file_path = os.path.join(DATA_DIR, f"{symbol}.csv")
                        clean_stock_data.to_csv(file_path, index=False)
                        logging.info(f"Datos guardados como CSV: {file_path}")
                        try:
                            os.remove(file_path)
                            logging.info(f"Archivo CSV eliminado: {file_path}")
                        except PermissionError as e:
                            logging.error(f"No se pudo eliminar el archivo {file_path}: {e}")
                    else:
                        logging.warning(f"Datos no válidos para {symbol}.")
                else:
                    logging.warning(f"No se encontraron datos para {symbol}.")
        finally:
            db_session.close()
            logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    download_sp500_data()
