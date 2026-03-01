import pandas as pd
import matplotlib.pyplot as plt

# Cargar datos
df = pd.read_excel("delitos_2024.xlsx")

# Filtrar por barrio (suponiendo columna 'Barrio')
barrios = df.groupby("Barrio").size().reset_index(name="Total")

# Crear gráfico
plt.figure(figsize=(10, 6))
plt.bar(barrios["Barrio"], barrios["Total"], color='skyblue')
plt.title("Delitos por Barrio en Jamundí")
plt.xlabel("Barrio")
plt.ylabel("Número de Delitos")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig("delitos_por_barrio.png")

# Generar reporte
report = f"""
INFORME SISC - JAMUNDÍ
Fecha: {pd.Timestamp.now().strftime("%d/%m/%Y")}
---------------------------
TENDENCIAS DE DELITOS 2024
Delito            | Total | Variación vs 2023
-------------------|-------|-------------------
{df.groupby("Delito").size().reset_index(name="Total").to_string(index=False)}
Gráfico de delitos por barrio: delitos_por_barrio.png
"""

# Guardar reporte
with open("informe_sisc_jamundi.txt", "w") as f:
    f.write(report)
