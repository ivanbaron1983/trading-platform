import os
import pandas as pd
from alpaca_trade_api.rest import REST
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from backend.app.db import SessionLocal
from backend.app.models import SP500IntradayData
from dotenv import load_dotenv
import logging
import time
from pytz import timezone

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("alpaca_live_data_loader.log"),
        logging.StreamHandler()
    ]
)

# Configuración del horario de la Bolsa de Nueva York (NYSE)
NYSE_TZ = timezone("America/New_York")
MARKET_OPEN = "09:30:00"
MARKET_CLOSE = "16:00:00"

# Cargar variables de entorno del archivo .env
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_LIVE_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_LIVE_SECRET_KEY")

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError("Las claves API Live de Alpaca no están configuradas en el archivo .env")

# Configuración de Alpaca Live
alpaca_api = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://api.alpaca.markets")

# Ruta de la carpeta de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../../data/sp500_5min_live")
os.makedirs(DATA_DIR, exist_ok=True)
logging.info(f"Carpeta de datos asegurada: {DATA_DIR}")

def clear_intraday_table(session: Session):
    """Limpia la tabla de datos intradía antes de una nueva descarga."""
    try:
        session.execute(text("TRUNCATE TABLE sp500_intraday_data"))
        session.commit()
        logging.info("Tabla sp500_intraday_data limpiada exitosamente.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error al limpiar la tabla sp500_intraday_data: {e}")

def filter_market_hours(data: pd.DataFrame):
    """Filtra los datos para incluir solo las horas normales del mercado."""
    try:
        # Convertir Datetime a un objeto datetime y gestionar la zona horaria
        data["Datetime"] = pd.to_datetime(data["Datetime"], errors="coerce")

        if data["Datetime"].dt.tz is None:  # Si no tiene timezone
            data["Datetime"] = data["Datetime"].dt.tz_localize("UTC")
        else:  # Si ya tiene timezone, convertir a NYSE
            data["Datetime"] = data["Datetime"].dt.tz_convert(NYSE_TZ)

        # Filtrar solo las filas dentro del horario normal del mercado
        data["time"] = data["Datetime"].dt.strftime("%H:%M:%S")
        data = data[(data["time"] >= MARKET_OPEN) & (data["time"] <= MARKET_CLOSE)]

        # Crear una nueva copia eliminando la columna auxiliar 'time'
        data = data.drop(columns=["time"])

        logging.info(f"Datos filtrados al horario del mercado (NYSE). Filas restantes: {len(data)}.")
        return data
    except Exception as e:
        logging.error(f"Error al filtrar los datos al horario del mercado: {e}")
        return pd.DataFrame()




def download_5min_data(symbol, start_date="2000-01-01", retries=3):
    """Descarga datos históricos de 5 minutos para una acción desde Alpaca Live."""
    for attempt in range(retries):
        try:
            bars = alpaca_api.get_bars(
                symbol, timeframe="5Min", start=start_date, adjustment="all"
            ).df

            if bars.empty:
                logging.warning(f"No se encontraron datos para {symbol}.")
                return pd.DataFrame()

            bars.reset_index(inplace=True)
            bars.rename(columns={
                'timestamp': 'Datetime',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'trade_count': 'TradeCount',
                'vwap': 'VWAP'
            }, inplace=True)

            # Filtrar datos para el horario del mercado
            bars = filter_market_hours(bars)

            logging.info(f"Datos descargados para {symbol}. Filas válidas: {len(bars)}.")
            return bars
        except Exception as e:
            logging.error(f"Error al descargar los datos para {symbol}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                logging.error(f"Falló la descarga para {symbol} después de {retries} intentos.")
    return pd.DataFrame()

def save_to_db(session: Session, symbol: str, data: pd.DataFrame):
    """Guarda datos de 5 minutos en la base de datos."""
    logging.info(f"Comenzando el guardado de datos para {symbol}. Total de filas: {len(data)}")

    records = []
    for _, row in data.iterrows():
        try:
            record = SP500IntradayData(
                symbol=symbol,
                datetime=row["Datetime"],
                open=row["Open"],
                high=row["High"],
                low=row["Low"],
                close=row["Close"],
                volume=row["Volume"],
                trade_count=row["TradeCount"],
                vwap=row["VWAP"]
            )
            records.append(record)
        except Exception as e:
            logging.error(f"Error al procesar fila para {symbol}: {e}")
            continue

    try:
        session.bulk_save_objects(records)
        session.commit()
        logging.info(f"Datos guardados exitosamente para {symbol}.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error al guardar datos en la base de datos para {symbol}: {e}")

def download_live_data():
    """Descarga datos de 5 minutos para empresas del S&P 500 desde la cuenta Alpaca Live."""
    sp500_companies = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]

    if not sp500_companies.empty:
        db_session = SessionLocal()

        # Limpiar la tabla antes de la descarga
        clear_intraday_table(db_session)

        try:
            for _, row in sp500_companies.iterrows():
                symbol = row["Symbol"]
                logging.info(f"Procesando {symbol}...")
                stock_data = download_5min_data(symbol, start_date="2022-12-19")

                if not stock_data.empty:
                    save_to_db(db_session, symbol, stock_data)
                else:
                    logging.warning(f"No se encontraron datos válidos para {symbol}.")
        finally:
            db_session.close()
            logging.info("Conexión a la base de datos cerrada.")
    else:
        logging.error("No se pudo obtener la lista de empresas del S&P 500.")

if __name__ == "__main__":
    logging.info("Iniciando el proceso de descarga de datos de 5 minutos con Alpaca Live...")
    download_live_data()
z

