import pandas as pd
import os

# Rutas correctas (archivos en el mismo directorio donde se ejecuta)
arch_homicidio = r'HOMICIDIO INTENCIONAL.xlsx'
arch_secuestro = r'SECUESTRO.xlsx'

report = []
report.append("INFORME SISC - CONCEJO DE SEGURIDAD JAMUNDÍ")
report.append(f"Fecha: {pd.Timestamp.now().strftime('%d/%m/%Y')}")
report.append("="*50)

# Función para procesar cada archivo
def procesar_archivo(ruta, nombre):
    if not os.path.exists(ruta):
        return f"❌ No encontré: {nombre}"
    
    df = pd.read_excel(ruta)
    df.columns = [c.lower().strip() for c in df.columns]
    
    resultado = [f"\n{nombre.upper()}", "-"*30]
    resultado.append(f"📋 Columnas: {list(df.columns)}")
    resultado.append(f"📈 Total registros: {len(df)}")
    
    # Buscar y convertir columna de fecha
    fecha_col = next((c for c in df.columns if "fecha" in c.lower()), None)
    years = []
    
    if fecha_col:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        years = sorted(df[fecha_col].dropna().dt.year.unique().astype(int).tolist())
        resultado.append(f"📅 Años disponibles: {years}")
        if years:
            resultado.append(f"📊 Rango: {min(years)} - {max(years)}")
        
        # TOP 5 por fecha
        top5 = df[fecha_col].value_counts().head(5)
        resultado.append(f"\n📊 TOP 5 FECHAS CON MÁS REGISTROS:")
        resultado.append(top5.to_string())
    else:
        resultado.append(f"\n⚠️ No encontré columna de fecha. Primeras 3 filas:")
        resultado.append(df.head(3).to_string())
    
    # Buscar columna de barrio/municipio si existe
    barrio_col = next((c for c in df.columns if any(x in c.lower() for x in ["barrio","zona","sector","comuna","municipio"])), None)
    if barrio_col:
        top5_barrio = df[barrio_col].value_counts().head(5)
        resultado.append(f"\n📍 TOP 5 POR {barrio_col.upper()}:")
        resultado.append(top5_barrio.to_string())
    
    return "\n".join(resultado), years

# Procesar ambos archivos
resultado_h, years_h = procesar_archivo(arch_homicidio, "HOMICIDIO INTENCIONAL")
report.append(resultado_h)

report.append("\n" + "="*50)

resultado_s, years_s = procesar_archivo(arch_secuestro, "SECUESTRO")
report.append(resultado_s)

# Texto para presentación (1 minuto)
report.append("\n" + "="*50)
report.append("📝 TEXTO PARA PRESENTACIÓN EN EL CONCEJO (1 min):")
report.append("="*50)

anos_info = ""
if years_h or years_s:
    todos = sorted(set(years_h + years_s))
    if todos:
        anos_info = f" (años {min(todos)}-{max(todos)})"

report.append(f'''
"Buenas tardes, miembros del Concejo de Seguridad.

Presento el resumen de delitos en Jamundí{anos_info}:

1. HOMICIDIOS: Se registraron múltiples casos en fechas específicas que requieren atención focalizada.

2. SECUESTROS: También se presentan patrones por fecha que debemos analizar.

Recomendación: Incrementar patrullaje en las fechas y zonas con mayor incidencia, y fortalecer la coordinación entre fuerzas de seguridad.

Gracias."
''')

# Guardar informe
with open("informe_jamundi.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print("✅ Informe generado: informe_jamundi.txt")
print("\n" + "\n".join(report))
