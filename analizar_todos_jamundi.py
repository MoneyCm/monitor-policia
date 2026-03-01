import pandas as pd
import os
import json
from datetime import datetime
from pathlib import Path

print("🔍 ANALIZADOR MASIVO - OBSERVATORIO JAMUNDÍ")
print("="*70)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print(f"Espacio de trabajo: {Path.cwd()}")
print("="*70 + "\n")

# Configuración
JAMUNDI_CODE = 76364
JAMUNDI_NAMES = ["JAMUNDÍ", "JAMUNDI", "Jamundí", "Jamundi", "jamundí", "jamundi"]
WORKSPACE = Path.cwd()
ARCHIVOS = list(WORKSPACE.glob("*.xlsx"))

def detectar_columna(df, keywords):
    cols_lower = [str(c).lower().strip() for c in df.columns]
    for kw in keywords:
        for i, col in enumerate(cols_lower):
            if kw in col:
                return df.columns[i]
    return None

def es_jamundi(valor):
    if pd.isna(valor): return False
    val = str(valor).strip().upper()
    if any(j.upper() in val for j in JAMUNDI_NAMES): return True
    try:
        if int(float(valor)) == JAMUNDI_CODE: return True
    except: pass
    return False

def procesar_archivo(ruta):
    resultado = {
        "archivo": ruta.name,
        "total_original": 0,
        "total_jamundi": 0,
        "columnas": [],
        "años": [],
        "tendencia": "N/A",
        "zona_dist": {},
        "error": None
    }
    
    try:
        df = pd.read_excel(ruta)
        df.columns = [c.lower().strip() for c in df.columns]
        resultado["total_original"] = len(df)
        resultado["columnas"] = list(df.columns)
        
        # Detectar columnas clave
        col_muni = detectar_columna(df, ["municipio", "cod_muni", "codigo_municipio"])
        col_fecha = detectar_columna(df, ["fecha", "date", "hecho", "ocurrencia"])
        col_zona = detectar_columna(df, ["zona", "barrio", "sector", "comuna", "vereda"])
        
        # Filtrar por Jamundí
        if col_muni:
            if "cod_muni" in col_muni.lower():
                mask = df[col_muni].astype(str).str.strip() == str(JAMUNDI_CODE)
            else:
                mask = df[col_muni].astype(str).str.upper().str.contains("JAMUNDI", na=False)
            df_j = df[mask].copy()
        else:
            df_j = df.copy()  # Si no hay columna de municipio, asumimos que todo es Jamundí
        
        resultado["total_jamundi"] = len(df_j)
        
        # Análisis temporal si hay fecha
        if col_fecha and len(df_j) > 0:
            df_j[col_fecha] = pd.to_datetime(df_j[col_fecha], errors='coerce')
            df_time = df_j[df_j[col_fecha].notna()]
            if len(df_time) > 0:
                años = sorted(df_time[col_fecha].dt.year.dropna().unique().astype(int).tolist())
                resultado["años"] = años
                
                # Tendencia simple
                if len(años) >= 2:
                    anual = df_time.groupby(df_time[col_fecha].dt.year).size()
                    primera, ultima = anual.iloc[0], anual.iloc[-1]
                    if primera > 0:
                        cambio = ((ultima - primera) / primera) * 100
                        if cambio > 10: resultado["tendencia"] = "📈 ALZA"
                        elif cambio < -10: resultado["tendencia"] = "📉 BAJA"
                        else: resultado["tendencia"] = "➡️ ESTABLE"
        
        # Distribución por zona si existe
        if col_zona and col_zona in df_j.columns:
            zona_counts = df_j[col_zona].value_counts().head(5)
            resultado["zona_dist"] = {str(k): int(v) for k, v in zona_counts.items()}
            
    except Exception as e:
        resultado["error"] = str(e)
    
    return resultado

# Procesar todos los archivos
print(f"📁 Encontrados {len(ARCHIVOS)} archivos Excel. Procesando...\n")
resultados = []

for i, ruta in enumerate(ARCHIVOS, 1):
    print(f"[{i}/{len(ARCHIVOS)}] {ruta.name}...", end=" ")
    res = procesar_archivo(ruta)
    resultados.append(res)
    
    if res["error"]:
        print(f"❌ Error: {res['error'][:50]}")
    elif res["total_jamundi"] > 0:
        print(f"✅ Jamundí: {res['total_jamundi']:,} registros")
    else:
        print(f"⚪ Sin datos de Jamundí")

# Generar informe consolidado
print("\n" + "="*70)
print("📊 GENERANDO INFORME CONSOLIDADO")
print("="*70)

# Filtrar solo archivos con datos de Jamundí
con_datos = [r for r in resultados if r["total_jamundi"] > 0]

informe = []
informe.append("OBSERVATORIO DEL DELITO - JAMUNDÍ, VALLE DEL CAUCA")
informe.append(f"Reporte generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
informe.append(f"Archivos analizados: {len(ARCHIVOS)} | Con datos de Jamundí: {len(con_datos)}")
informe.append("="*70 + "\n")

# Resumen ejecutivo
informe.append("📋 RESUMEN EJECUTIVO")
informe.append("-"*70)
total_general = sum(r["total_jamundi"] for r in con_datos)
informe.append(f"• Total de registros de Jamundí (todos los delitos): {total_general:,}")
informe.append(f"• Archivos con información de Jamundí: {len(con_datos)}\n")

# Tabla resumen por delito
informe.append("📊 DETALLE POR TIPO DE DELITO")
informe.append("-"*70)
informe.append(f"{'Archivo':<45} {'Total Jamundí':>12} {'Años':<15} {'Tendencia':<10}")
informe.append("-"*70)

for r in sorted(con_datos, key=lambda x: x["total_jamundi"], reverse=True):
    nombre = r["archivo"].replace(".xlsx", "")[:44]
    total = f"{r['total_jamundi']:,}"
    años = f"{min(r['años'])}-{max(r['años'])}" if r["años"] else "N/A"
    tendencia = r["tendencia"]
    informe.append(f"{nombre:<45} {total:>12} {años:<15} {tendencia:<10}")

# Top 10 delitos por frecuencia en Jamundí
informe.append("\n🔝 TOP 10 DELITOS CON MÁS REGISTROS EN JAMUNDÍ")
informe.append("-"*70)
top10 = sorted(con_datos, key=lambda x: x["total_jamundi"], reverse=True)[:10]
for i, r in enumerate(top10, 1):
    nombre = r["archivo"].replace(".xlsx", "")
    informe.append(f"{i}. {nombre}: {r['total_jamundi']:,} registros")

# Distribución por zona (si hay datos)
zonas_consolidadas = {}
for r in con_datos:
    for zona, count in r["zona_dist"].items():
        zonas_consolidadas[zona] = zonas_consolidadas.get(zona, 0) + count

if zonas_consolidadas:
    informe.append("\n🗺️ DISTRIBUCIÓN POR ZONA (consolidado)")
    informe.append("-"*70)
    for zona, count in sorted(zonas_consolidadas.items(), key=lambda x: x[1], reverse=True)[:5]:
        pct = count / total_general * 100 if total_general > 0 else 0
        barra = "█" * int(pct / 2)
        informe.append(f"• {zona:<20} {count:>6,} {barra} {pct:.1f}%")

# Recomendaciones
informe.append("\n🎯 RECOMENDACIONES PARA EL CONCEJO DE SEGURIDAD")
informe.append("-"*70)
informe.append("""
1. PRIORIZACIÓN: Enfocar recursos en los delitos TOP 5 con mayor incidencia en Jamundí.
2. TEMPORALIDAD: Reforzar operativos en años/meses con tendencia al alza identificada.
3. TERRITORIALIDAD: Si hay datos de zona, focalizar intervenciones en áreas críticas.
4. MONITOREO: Ejecutar este análisis mensualmente para detectar cambios de tendencia.
5. COORDINACIÓN: Socializar hallazgos con Policía, Fiscalía y Gobernación del Valle.
""")

# Guardar informe
nombre_archivo = f"OBSERVATORIO_JAMUNDI_CONSOLIDADO_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
with open(nombre_archivo, "w", encoding="utf-8") as f:
    f.write("\n".join(informe))

# Guardar datos crudos en JSON para análisis futuro
with open("resultados_jamundi.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)

print(f"\n✅ INFORME GENERADO: {nombre_archivo}")
print(f"💾 Datos crudos: resultados_jamundi.json")
print(f"📬 Listo para presentar ante el Concejo de Seguridad de Jamundí.")

# Mostrar resumen en pantalla
print("\n" + "\n".join(informe[:30]))  # Mostrar primeras 30 líneas
