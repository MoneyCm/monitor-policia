import pandas as pd
import numpy as np
import os
from datetime import datetime

print("🔍 OBSERVATORIO DEL DELITO - JAMUNDÍ")
print("="*70)
print(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*70)

# Configuración
archivos = {
    "HOMICIDIO INTENCIONAL": "HOMICIDIO INTENCIONAL.xlsx",
    "SECUESTRO": "SECUESTRO.xlsx"
}

# Función para detectar columnas por palabras clave
def detectar_columna(df, keywords):
    cols_lower = [c.lower().strip() for c in df.columns]
    for kw in keywords:
        for i, col in enumerate(cols_lower):
            if kw in col:
                return df.columns[i]
    return None

# Función para formato de números
def fmt(n): return f"{n:,.0f}" if pd.notna(n) else "N/A"

report = []
report.append("OBSERVATORIO DEL DELITO - MUNICIPIO DE JAMUNDÍ")
report.append(f"Reporte generado: {datetime.now().strftime('%d/%m/%Y')}")
report.append("Fuente: Datos oficiales procesados por OpenClaw")
report.append("="*70 + "\n")

# 1. RESUMEN EJECUTIVO
report.append("📋 RESUMEN EJECUTIVO")
report.append("-"*70)

total_general = 0
datos_por_tipo = {}

for tipo, ruta in archivos.items():
    if not os.path.exists(ruta):
        report.append(f"⚠️ Archivo no encontrado: {ruta}")
        continue
    
    df = pd.read_excel(ruta)
    df.columns = [c.lower().strip() for c in df.columns]
    total = len(df)
    total_general += total
    
    # Detectar columnas clave
    fecha_col = detectar_columna(df, ["fecha", "date", "time", "hecho"])
    ubic_col = detectar_columna(df, ["barrio", "zona", "sector", "comuna", "municipio", "localidad", "direccion"])
    victima_col = detectar_columna(df, ["víctima", "victim", "edad", "sexo", "género"])
    modalidad_col = detectar_columna(df, ["modalidad", "tipo", "clase", "método"])
    
    datos_por_tipo[tipo] = {
        "df": df,
        "total": total,
        "fecha_col": fecha_col,
        "ubic_col": ubic_col,
        "victima_col": victima_col,
        "modalidad_col": modalidad_col
    }
    
    report.append(f"• {tipo}: {fmt(total)} registros")

report.append(f"\n📊 TOTAL GENERAL DE DELITOS ANALIZADOS: {fmt(total_general)}\n")

# 2. ANÁLISIS TEMPORAL
report.append("📅 ANÁLISIS TEMPORAL")
report.append("-"*70)

for tipo, datos in datos_por_tipo.items():
    df = datos["df"]
    fecha_col = datos["fecha_col"]
    
    if fecha_col:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        df_clean = df[df[fecha_col].notna()].copy()
        
        if len(df_clean) > 0:
            años = sorted(df_clean[fecha_col].dt.year.dropna().unique().astype(int).tolist())
            reporte_anual = df_clean.groupby(df_clean[fecha_col].dt.year).size()
            
            report.append(f"\n{tipo}:")
            report.append(f"  • Período: {min(años)} - {max(años)}")
            report.append(f"  • Registros con fecha válida: {fmt(len(df_clean))} ({len(df_clean)/len(df)*100:.1f}%)")
            report.append(f"  • Promedio anual: {fmt(reporte_anual.mean())} casos/año")
            
            # Tendencia
            if len(reporte_anual) >= 2:
                primera = reporte_anual.iloc[0]
                ultima = reporte_anual.iloc[-1]
                cambio = ((ultima - primera) / primera * 100) if primera != 0 else 0
                tendencia = "📈 ALZA" if cambio > 10 else "📉 BAJA" if cambio < -10 else "➡️ ESTABLE"
                report.append(f"  • Tendencia ({min(años)}→{max(años)}): {tendencia} ({cambio:+.1f}%)")
            
            # Estacionalidad (por mes)
            if len(df_clean) >= 12:
                meses = df_clean[fecha_col].dt.month_name(locale='es_ES').value_counts().head(3)
                if len(meses) > 0:
                    report.append(f"  • Meses con mayor incidencia: {', '.join([f'{m}' for m in meses.index[:3]])}")
        else:
            report.append(f"\n{tipo}: ⚠️ Sin fechas válidas para análisis temporal")
    else:
        report.append(f"\n{tipo}: ⚠️ No se detectó columna de fecha")

# 3. ANÁLISIS GEOGRÁFICO (si hay datos de ubicación)
report.append("\n📍 ANÁLISIS GEOGRÁFICO")
report.append("-"*70)

for tipo, datos in datos_por_tipo.items():
    df = datos["df"]
    ubic_col = datos["ubic_col"]
    
    if ubic_col:
        top_ubic = df[ubic_col].value_counts().head(5)
        total_ubic = df[ubic_col].notna().sum()
        
        report.append(f"\n{tipo} - TOP 5 ZONAS CRÍTICAS:")
        report.append(f"  (Registros con ubicación: {fmt(total_ubic)} / {fmt(len(df))} = {total_ubic/len(df)*100:.1f}%)")
        for i, (zona, count) in enumerate(top_ubic.items(), 1):
            pct = count / total_ubic * 100 if total_ubic > 0 else 0
            barra = "█" * int(pct / 5)
            report.append(f"  {i}. {str(zona)[:40]:<40} {fmt(count):>5} casos {barra} {pct:.1f}%")
    else:
        report.append(f"\n{tipo}: ⚠️ Sin datos geográficos para análisis espacial")

# 4. PERFILIZACIÓN (si hay datos de víctimas o modalidades)
report.append("\n👥 PERFILIZACIÓN Y MODALIDADES")
report.append("-"*70)

for tipo, datos in datos_por_tipo.items():
    df = datos["df"]
    modalidad_col = datos["modalidad_col"]
    
    if modalidad_col and modalidad_col in df.columns:
        top_mod = df[modalidad_col].value_counts().head(5)
        report.append(f"\n{tipo} - TOP 5 MODALIDADES:")
        for i, (mod, count) in enumerate(top_mod.items(), 1):
            pct = count / len(df) * 100
            report.append(f"  {i}. {str(mod)[:50]:<50} {pct:.1f}%")
    else:
        report.append(f"\n{tipo}: ⚠️ Sin datos de modalidad para perfilización")

# 5. INDICADORES DE RIESGO
report.append("\n⚠️ INDICADORES DE RIESGO IDENTIFICADOS")
report.append("-"*70)

riesgos = []

for tipo, datos in datos_por_tipo.items():
    df = datos["df"]
    fecha_col = datos["fecha_col"]
    
    # Concentración temporal
    if fecha_col:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        df_clean = df[df[fecha_col].notna()]
        if len(df_clean) > 10:
            dias = df_clean[fecha_col].dt.date.value_counts()
            if len(dias) > 0:
                max_dia = dias.max()
                pct_concentracion = max_dia / len(df_clean) * 100
                if pct_concentracion > 5:
                    riesgos.append(f"• {tipo}: Alta concentración en fechas específicas ({pct_concentracion:.1f}% en un solo día)")

# Zonas críticas
for tipo, datos in datos_por_tipo.items():
    ubic_col = datos["ubic_col"]
    if ubic_col:
        top1 = datos["df"][ubic_col].value_counts().iloc[0] if len(datos["df"][ubic_col].dropna()) > 0 else None
        if top1:
            pct_zona = datos["df"][ubic_col].value_counts().iloc[0] / len(datos["df"]) * 100
            if pct_zona > 15:
                riesgos.append(f"• {tipo}: Zona hiperconcentrada ({pct_zona:.1f}% de casos en una sola ubicación)")

if riesgos:
    for r in riesgos:
        report.append(f"  {r}")
else:
    report.append("  • No se identificaron patrones de riesgo extremo con los datos disponibles")

# 6. RECOMENDACIONES OPERATIVAS
report.append("\n🎯 RECOMENDACIONES OPERATIVAS")
report.append("-"*70)
report.append("""
1. VIGILANCIA DINÁMICA
   • Desplegar patrullaje preventivo en fechas con histórico de picos delictivos
   • Rotar horarios de cobertura según patrones temporales identificados

2. ENFOQUE TERRITORIAL
   • Priorizar intervenciones en las zonas TOP 3 de cada tipo delictivo
   • Coordinar con Juntas de Acción Comunal para prevención comunitaria

3. ANÁLISIS CONTINUO
   • Actualizar este reporte mensualmente para detectar cambios de tendencia
   • Cruzar con datos de denuncia, captura y judicialización para medir efectividad

4. PREVENCIÓN SITUACIONAL
   • Mejorar iluminación y vigilancia en puntos críticos identificados
   • Promover denuncias anónimas y canales de alerta temprana

5. COORDINACIÓN INTERINSTITUCIONAL
   • Socializar hallazgos con Policía, Fiscalía, Personería y Gobernación
   • Alinear operativos con el Plan de Seguridad Ciudadana municipal
""")

# 7. LIMITACIONES METODOLÓGICAS
report.append("⚠️ LIMITACIONES DEL ANÁLISIS")
report.append("-"*70)
report.append("""
• Los resultados dependen de la calidad y completitud de los datos fuente
• La ausencia de columnas clave (ubicación, fecha, víctima) limita el análisis
• Este reporte refleja registros, no necesariamente casos judicializados
• Se recomienda validar hallazgos con fuentes complementarias (denuncias, capturas)
""")

# 8. METADATOS
report.append("\n📄 METADATOS DEL REPORTE")
report.append("-"*70)
report.append(f"• Archivos procesados: {', '.join([f'{k} ({v})' for k,v in archivos.items()])}")
report.append(f"• Herramienta: OpenClaw + Python/pandas")
report.append(f"• Método: Análisis descriptivo con detección automática de columnas")
report.append(f"• Clasificación: Uso interno - Concejo de Seguridad de Jamundí")

# Guardar informe
nombre_archivo = f"OBSERVATORIO_JAMUNDI_{datetime.now().strftime('%Y%m%d')}.txt"
with open(nombre_archivo, "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print(f"\n✅ INFORME GENERADO: {nombre_archivo}")
print(f"💾 Ubicado en: C:\\Users\\Usuario\\.openclaw\\workspace\\{nombre_archivo}")
print("\n📬 Listo para presentar ante el Concejo de Seguridad.")
