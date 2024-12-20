import os
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.db import SessionLocal
from backend.app.models import SP500IntradayData
from alpaca_trade_api.rest import REST
from dotenv import load_dotenv
import logging
from pytz import timezone
import datetime as dt

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("gap_analysis.log"),
        logging.StreamHandler()
    ]
)

# Configuración de horario de la Bolsa de Nueva York
NYSE_TZ = timezone("America/New_York")

# Cargar claves API desde el archivo .env
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_LIVE_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_LIVE_SECRET_KEY")

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError("Las claves API Live de Alpaca no están configuradas en el archivo .env")

# Configuración de Alpaca Live
alpaca_api = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://api.alpaca.markets")


# Función para extraer datos de la base de datos
def fetch_data_from_db(session: Session, symbol: str):
    """Extrae datos para un símbolo específico desde la base de datos."""
    try:
        query = session.query(SP500IntradayData.datetime).filter(SP500IntradayData.symbol == symbol)
        data = pd.read_sql(query.statement, session.bind)
        
        if data.empty:
            logging.warning(f"No se encontraron datos para {symbol} en la base de datos.")
            return pd.DataFrame()

        # Convertir el campo datetime a un índice con formato datetime
        data['datetime'] = pd.to_datetime(data['datetime'])
        data.set_index('datetime', inplace=True)
        return data
    except Exception as e:
        logging.error(f"Error al extraer datos para {symbol}: {e}")
        return pd.DataFrame()


# Función para identificar lagunas en los datos
def identify_gaps(data: pd.DataFrame, symbol: str, start_date, end_date):
    """Identifica lagunas de tiempo en los datos de un símbolo."""
    try:
        # Crear un rango completo de fechas de 5 minutos entre start_date y end_date
        full_range = pd.date_range(start=start_date, end=end_date, freq='5min', tz=NYSE_TZ)
        available_data = data.index
        missing_times = full_range.difference(available_data)

        if missing_times.empty:
            logging.info(f"No se encontraron lagunas de datos para {symbol}.")
            return None

        # Crear un DataFrame con las fechas faltantes
        gaps = pd.DataFrame(missing_times, columns=["MissingDatetime"])
        gaps.to_csv(f"missing_times_{symbol}.csv", index=False)
        logging.warning(f"Se encontraron lagunas de datos para {symbol}. Archivo: missing_times_{symbol}.csv")
        return gaps
    except Exception as e:
        logging.error(f"Error al identificar lagunas de tiempo para {symbol}: {e}")
        return None


# Función para rellenar los datos faltantes desde Alpaca
def fetch_missing_data(symbol: str, missing_times: pd.DataFrame):
    """Descarga datos para rellenar las lagunas identificadas."""
    try:
        filled_data = []

        for missing_time in missing_times["MissingDatetime"]:
            start = missing_time - pd.Timedelta(minutes=10)
            end = missing_time + pd.Timedelta(minutes=10)

            # Descargar datos para el rango faltante
            bars = alpaca_api.get_bars(
                symbol, 
                timeframe="5Min", 
                start=start.isoformat(), 
                end=end.isoformat(), 
                adjustment="all"
            ).df

            if not bars.empty:
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
                bars['Datetime'] = pd.to_datetime(bars['Datetime'])
                filled_data.append(bars)

        # Guardar los datos rellenados en un archivo CSV
        if filled_data:
            filled_data = pd.concat(filled_data)
            filled_data.to_csv(f"filled_data_{symbol}.csv", index=False)
            logging.info(f"Datos rellenados para {symbol}. Archivo: filled_data_{symbol}.csv")
            return filled_data
        else:
            logging.warning(f"No se pudo rellenar ninguna laguna para {symbol}.")
            return None
    except Exception as e:
        logging.error(f"Error al rellenar lagunas para {symbol}: {e}")
        return None


# Función principal para analizar y rellenar gaps
def analyze_gaps():
    """Analiza lagunas de tiempo para cada símbolo y rellena datos faltantes si es posible."""
    session = SessionLocal()
    try:
        # Verificar si la tabla tiene datos
        if not session.query(SP500IntradayData).first():
            logging.error("La tabla SP500IntradayData está vacía. Verifica el proceso de carga.")
            return

        # Obtener los símbolos únicos en la base de datos
        symbols = session.query(SP500IntradayData.symbol).distinct().all()
        symbols = [s[0] for s in symbols]
        logging.info(f"Símbolos detectados: {symbols}")

        for symbol in symbols:
            logging.info(f"Analizando lagunas para {symbol}...")
            data = fetch_data_from_db(session, symbol)

            if data.empty:
                continue

            # Rango de fechas disponibles
            min_date = data.index.min()
            max_date = data.index.max()
            logging.info(f"Rango de datos para {symbol}: {min_date} a {max_date}")

            # Identificar lagunas
            gaps = identify_gaps(data, symbol, start_date=min_date, end_date=max_date)

            # Rellenar datos faltantes si se encuentran lagunas
            if gaps is not None and not gaps.empty:
                fetch_missing_data(symbol, gaps)
    except Exception as e:
        logging.error(f"Error durante el análisis de lagunas: {e}")
    finally:
        session.close()
        logging.info("Conexión a la base de datos cerrada.")


# Punto de entrada del programa
if __name__ == "__main__":
    logging.info("Iniciando análisis de lagunas en los datos...")
    analyze_gaps()


