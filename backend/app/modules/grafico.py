import pandas as pd
import matplotlib.pyplot as plt
import datetime

# Ruta de entrada y salida
input_file = '/Users/ivanbaron/Documents/trading-platform/date_ranges.csv'  # Reemplaza con la ruta de tu archivo actual
output_file = 'date_ranges_with_quality.csv'

# 1. Cargar los datos desde el archivo CSV
try:
    data = pd.read_csv(input_file)
    print(f"Archivo cargado: {input_file}")
except Exception as e:
    print(f"Error al cargar el archivo: {e}")
    exit()

# 2. Convertir columnas de fechas a tipo datetime
try:
    data['MinDate'] = pd.to_datetime(data['MinDate'])
    data['MaxDate'] = pd.to_datetime(data['MaxDate'])
except Exception as e:
    print(f"Error al convertir fechas: {e}")
    exit()

# 3. Clasificar la calidad de los datos
def classify_quality(row):
    date_range_days = (row['MaxDate'] - row['MinDate']).days
    if row['TotalRows'] >= 50000 and date_range_days >= 540:
        return "Alta"
    elif row['TotalRows'] >= 40000:
        return "Moderada"
    else:
        return "Baja"

try:
    data['Quality'] = data.apply(classify_quality, axis=1)
    print("Clasificación de calidad completada.")
except Exception as e:
    print(f"Error al clasificar calidad: {e}")
    exit()

# 4. Guardar el archivo actualizado con la columna `Quality`
try:
    data.to_csv(output_file, index=False)
    print(f"Archivo actualizado guardado en: {output_file}")
except Exception as e:
    print(f"Error al guardar el archivo actualizado: {e}")
    exit()

# 5. Generar gráfico
def plot_data_quality(data):
    # Asignar colores según la calidad
    color_mapping = {"Alta": "green", "Moderada": "yellow", "Baja": "red"}
    data['Color'] = data['Quality'].map(color_mapping)

    # Crear gráfica
    plt.figure(figsize=(12, 6))
    plt.bar(data['Symbol'], data['TotalRows'], color=data['Color'], edgecolor='black')
    plt.axhline(y=50000, color='blue', linestyle='--', label='Umbral Alta Calidad')
    plt.axhline(y=40000, color='orange', linestyle='--', label='Umbral Moderada Calidad')

    # Etiquetas y título
    plt.xlabel("Símbolos")
    plt.ylabel("Total de Filas")
    plt.title("Calidad de los datos por símbolo")
    plt.xticks(rotation=90, fontsize=8)
    plt.legend()

    # Guardar gráfica
    plt.tight_layout()
    output_graph = "data_quality_graph.png"
    plt.savefig(output_graph)
    plt.show()
    print(f"Gráfica generada: {output_graph}")

# Llamar a la función para graficar
try:
    plot_data_quality(data)
except Exception as e:
    print(f"Error al generar la gráfica: {e}")


