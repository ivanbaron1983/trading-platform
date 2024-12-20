import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la conexión a la base de datos
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def verify_intraday_data(df_intraday, symbol):
    """
    Verifica la calidad de los datos intradía para un símbolo.
    """
    df_symbol = df_intraday[df_intraday['symbol'] == symbol].copy()
    df_symbol.loc[:, 'date'] = pd.to_datetime(df_symbol['datetime']).dt.date

    # Contar registros por día
    daily_counts = df_symbol.groupby('date').size()

    # Identificar días incompletos (menos de 390 registros por día)
    incomplete_days = daily_counts[daily_counts < 390]

    return incomplete_days

def compare_with_daily_data(df_intraday, df_daily, symbol):
    """
    Verifica la consistencia entre los datos intradía y diarios.
    """
    df_intraday_symbol = df_intraday[df_intraday['symbol'] == symbol].copy()
    df_intraday_symbol.loc[:, 'date'] = pd.to_datetime(df_intraday_symbol['datetime']).dt.date

    df_daily_symbol = df_daily[df_daily['symbol'] == symbol]

    # Comparar precios de cierre por día
    inconsistencies = []
    for date in df_daily_symbol['date']:
        daily_close = df_daily_symbol[df_daily_symbol['date'] == date]['close'].values[0]
        intraday_close = (
            df_intraday_symbol[df_intraday_symbol['date'] == date]
            .sort_values(by='datetime')['close']
            .values[-1]
            if not df_intraday_symbol[df_intraday_symbol['date'] == date].empty
            else None
        )
        if intraday_close is None or abs(daily_close - intraday_close) > 0.01:
            inconsistencies.append(date)

    return inconsistencies

def generate_report(df_intraday, df_daily, symbols):
    """
    Genera un reporte de calidad para todos los símbolos.
    """
    report = []
    for symbol in symbols:
        # Verificar días incompletos
        incomplete_days = verify_intraday_data(df_intraday, symbol)

        # Verificar consistencia con datos diarios
        inconsistencies = compare_with_daily_data(df_intraday, df_daily, symbol)

        # Determinar si el símbolo es apto
        if len(incomplete_days) > 0 or len(inconsistencies) > 0:
            status = 'problematic'
        else:
            status = 'ok'

        report.append({
            'symbol': symbol,
            'status': status,
            'incomplete_days': len(incomplete_days),
            'inconsistencies': len(inconsistencies),
            'incomplete_days_list': incomplete_days.index.tolist(),
            'inconsistencies_list': inconsistencies
        })
    return pd.DataFrame(report)

def process_data(report, df_intraday):
    """
    Filtra datos intradía eliminando símbolos problemáticos y guardando los datos limpios.
    """
    # Filtrar símbolos recuperables (menos de 5 días incompletos y menos de 10 inconsistencias)
    recoverable_symbols = report[
        (report['incomplete_days'] <= 5) & (report['inconsistencies'] <= 10)
    ]['symbol']
    print(f"Símbolos recuperables: {len(recoverable_symbols)}")

    # Filtrar datos intradía
    df_filtered = df_intraday[df_intraday['symbol'].isin(recoverable_symbols)]

    # Guardar los datos filtrados en una nueva tabla
    df_filtered.to_sql('filtered_intraday_data', engine, if_exists='replace', index=False)
    print("Datos intradía filtrados guardados en la base de datos.")

    return df_filtered

# Cargar datos desde la base de datos
df_intraday = pd.read_sql("SELECT * FROM sp500_intraday_data", engine)
df_daily = pd.read_sql("SELECT * FROM sp500_data", engine)

# Lista de símbolos únicos
symbols = df_intraday['symbol'].unique()

# Generar reporte de calidad
report = generate_report(df_intraday, df_daily, symbols)

# Guardar el reporte como archivo CSV
report.to_csv("quality_report.csv", index=False)
print("Reporte de calidad guardado como 'quality_report.csv'.")

# Procesar datos y guardar datos filtrados
df_filtered = process_data(report, df_intraday)

# Resumen de resultados
print(f"Total de símbolos procesados: {len(symbols)}")
print(f"Total de símbolos problemáticos: {len(report[report['status'] == 'problematic'])}")
