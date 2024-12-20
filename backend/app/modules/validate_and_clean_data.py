import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from backend.app.db import SessionLocal
from backend.app.models import SP500IntradayData
import logging
import datetime
from pytz import timezone

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data_validation.log"),
        logging.StreamHandler()
    ]
)

# Configuración de parámetros de validación
MIN_REQUIRED_BARS = 50000  # Aproximadamente 18 meses de velas de 5 minutos
VALIDATION_START_DATE = (datetime.datetime.now() - datetime.timedelta(days=18 * 30)).date()
NYSE_TZ = timezone("America/New_York")  # Huso horario de la Bolsa de Nueva York

def fetch_data_from_db(session: Session, symbol: str):
    """Extrae datos de un símbolo específico desde la base de datos."""
    try:
        query = session.query(SP500IntradayData).filter(SP500IntradayData.symbol == symbol)
        data = pd.read_sql(query.statement, session.bind)
        logging.info(f"Datos extraídos para {symbol}. Total de filas: {len(data)}")
        return data
    except Exception as e:
        logging.error(f"Error al extraer datos para {symbol}: {e}")
        return pd.DataFrame()

def adjust_to_nyse_time(data: pd.DataFrame):
    """Ajusta los datos al horario de la Bolsa de Nueva York (sin horario de verano)."""
    try:
        # Convertir el campo 'datetime' a zona horaria de NYSE
        data["datetime"] = pd.to_datetime(data["datetime"], errors="coerce")
        data["datetime"] = data["datetime"].dt.tz_localize("UTC").dt.tz_convert(NYSE_TZ)
        
        # Filtro: solo incluir datos de 9:00 AM a 4:00 PM
        data["hour"] = data["datetime"].dt.hour
        data = data[(data["hour"] >= 9) & (data["hour"] <= 16)].copy()

        # Eliminar la columna auxiliar 'hour'
        data.drop(columns=["hour"], inplace=True)

        logging.info("Datos ajustados exitosamente al horario de NYSE.")
        return data
    except Exception as e:
        logging.error(f"Error al ajustar los datos al horario de NYSE: {e}")
        return pd.DataFrame()

def validate_data_quality(data: pd.DataFrame, symbol: str):
    """Valida la calidad de los datos extraídos."""
    if data.empty:
        logging.warning(f"No se encontraron datos para {symbol}.")
        return False, "No data"

    try:
        # Validar columnas necesarias
        required_columns = ["datetime", "open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logging.error(f"Columnas faltantes para {symbol}: {missing_columns}")
            return False, f"Missing columns: {missing_columns}"

        # Ajustar al horario de NYSE
        data = adjust_to_nyse_time(data)
        if data.empty:
            return False, "No data in NYSE trading hours"

        # Validar rango de fechas
        min_date, max_date = data["datetime"].min(), data["datetime"].max()
        if (max_date - min_date).days < 18 * 30:
            logging.warning(f"Rango de fechas insuficiente para {symbol}: {min_date} a {max_date}")
            return False, "Insufficient date range"

        # Validar cantidad de datos
        if len(data) < MIN_REQUIRED_BARS:
            logging.warning(f"Datos insuficientes para {symbol}: {len(data)} filas disponibles.")
            return False, "Insufficient bars"

        # Validar valores negativos y nulos
        for col in ["open", "high", "low", "close", "volume"]:
            if data[col].isnull().any() or (data[col] < 0).any():
                logging.warning(f"Valores inválidos encontrados en {col} para {symbol}.")
                return False, f"Invalid values in {col}"

        logging.info(f"Datos validados correctamente para {symbol}.")
        return True, "Data valid"
    except Exception as e:
        logging.error(f"Error al validar datos para {symbol}: {e}")
        return False, "Validation error"

def calculate_indicators(data: pd.DataFrame):
    """Calcula indicadores como medias móviles."""
    try:
        data["SMA_50"] = data["close"].rolling(window=50).mean()
        data["SMA_200"] = data["close"].rolling(window=200).mean()
        data.dropna(inplace=True)  # Eliminar filas sin cálculos válidos
        logging.info("Indicadores calculados exitosamente.")
        return data
    except Exception as e:
        logging.error(f"Error al calcular indicadores: {e}")
        return pd.DataFrame()

def process_validation():
    """Valida y clasifica los datos de la base de datos."""
    session = SessionLocal()
    try:
        symbols = session.query(SP500IntradayData.symbol).distinct().all()
        symbols = [s[0] for s in symbols]
        logging.info(f"Se encontraron {len(symbols)} símbolos en la base de datos.")

        report = []

        for symbol in symbols:
            logging.info(f"Procesando validación para {symbol}...")
            data = fetch_data_from_db(session, symbol)

            valid, message = validate_data_quality(data, symbol)
            if valid:
                processed_data = calculate_indicators(data)
                if not processed_data.empty:
                    report.append({"Symbol": symbol, "Status": "Valid", "Message": "Data ready for backtesting"})
                    logging.info(f"Datos listos para backtesting para {symbol}.")
                else:
                    report.append({"Symbol": symbol, "Status": "Error", "Message": "Error calculating indicators"})
            else:
                report.append({"Symbol": symbol, "Status": "Invalid", "Message": message})

        # Generar reporte
        report_df = pd.DataFrame(report)
        report_path = "validation_report.csv"
        report_df.to_csv(report_path, index=False)
        logging.info(f"Reporte generado: {report_path}")

    except Exception as e:
        logging.error(f"Error en el proceso de validación: {e}")
    finally:
        session.close()
        logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    logging.info("Iniciando proceso de validación de datos...")
    process_validation()
