import pandas as pd
import numpy as np
import os
from datetime import datetime

print("🔍 OBSERVATORIO DEL DELITO - JAMUNDÍ (VALLE DEL CAUCA)")
print("="*70)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("Análisis filtrado exclusivamente para el municipio de Jamundí")
print("="*70 + "\n")

# Configuración
MUNICIPIO_OBJETIVO = "JAMUNDÍ"  # Puede ajustarse si el dato viene en mayúsculas/minúsculas

archivos = {
    "HOMICIDIO INTENCIONAL": "HOMICIDIO INTENCIONAL.xlsx",
    "SECUESTRO": "SECUESTRO.xlsx"
}

# Función para detectar columnas por palabras clave
def detectar_columna(df, keywords):
    cols_lower = [str(c).lower().strip() for c in df.columns]
    for kw in keywords:
        for i, col in enumerate(cols_lower):
            if kw in col:
                return df.columns[i]
    return None

# Función para filtrar por Jamundí
def filtrar_jamundi(df, col_municipio, objetivo="JAMUNDÍ"):
    if not col_municipio:
        return df  # Si no hay columna, asumimos que todo es Jamundí
    # Filtrado flexible: contiene "jamundí" sin importar mayúsculas/minúsculas
    return df[df[col_municipio].astype(str).str.contains(objetivo, case=False, na=False)].copy()

report = []
report.append("OBSERVATORIO DEL DELITO - MUNICIPIO DE JAMUNDÍ, VALLE DEL CAUCA")
report.append(f"Reporte generado: {datetime.now().strftime('%d/%m/%Y')}")
report.append("Fuente: Datos oficiales filtrados para Jamundí")
report.append("Herramienta: OpenClaw + Python/pandas")
report.append("="*70 + "\n")

# 1. CONTEXTO MUNICIPAL
report.append("📍 CONTEXTO: JAMUNDÍ, VALLE DEL CAUCA")
report.append("-"*70)
report.append("""
• Ubicación: Sur del Valle del Cauca, área metropolitana de Cali
• Población estimada: ~150.000 habitantes (DANE 2024)
• Características: Corredor estratégico Cali-Popayán, zona rural-urbana mixta
• Retos de seguridad: Movilidad delictiva, presencia de grupos armados, microtráfico
""")

# 2. CARGA Y FILTRADO DE DATOS
report.append("📥 PROCESAMIENTO DE DATOS")
report.append("-"*70)

datos_jamundi = {}
total_filtrado = 0

for tipo, ruta in archivos.items():
    if not os.path.exists(ruta):
        report.append(f"⚠️ Archivo no encontrado: {ruta}")
        continue
    
    df_original = pd.read_excel(ruta)
    df_original.columns = [c.lower().strip() for c in df_original.columns]
    total_original = len(df_original)
    
    # Detectar columna de municipio/ciudad
    col_municipio = detectar_columna(df_original, ["municipio", "ciudad", "localidad", "cabecera", "area"])
    
    # Filtrar por Jamundí
    if col_municipio:
        df_filtrado = filtrar_jamundi(df_original, col_municipio, MUNICIPIO_OBJETIVO)
        report.append(f"\n{tipo}:")
        report.append(f"  • Registros originales: {total_original:,}")
        report.append(f"  • Columna de municipio detectada: '{col_municipio}'")
        report.append(f"  • Registros filtrados para Jamundí: {len(df_filtrado):,} ({len(df_filtrado)/total_original*100:.2f}%)")
    else:
        # Si no hay columna de municipio, asumimos que el archivo YA es de Jamundí
        df_filtrado = df_original.copy()
        report.append(f"\n{tipo}:")
        report.append(f"  • Registros cargados: {total_original:,}")
        report.append(f"  • ⚠️ Sin columna de municipio: se asume que todos los registros son de Jamundí")
    
    if len(df_filtrado) == 0:
        report.append(f"  ❌ No se encontraron registros para Jamundí en este archivo")
        continue
    
    total_filtrado += len(df_filtrado)
    
    # Detectar columnas clave para análisis
    fecha_col = detectar_columna(df_filtrado, ["fecha", "date", "time", "hecho", "ocurrencia"])
    ubic_col = detectar_columna(df_filtrado, ["barrio", "zona", "sector", "comuna", "vereda", "direccion", "lugar"])
    victima_col = detectar_columna(df_filtrado, ["víctima", "victim", "edad", "sexo", "género"])
    modalidad_col = detectar_columna(df_filtrado, ["modalidad", "tipo", "clase", "método", "arma"])
    
    datos_jamundi[tipo] = {
        "df": df_filtrado,
        "fecha_col": fecha_col,
        "ubic_col": ubic_col,
        "victima_col": victima_col,
        "modalidad_col": modalidad_col,
        "total": len(df_filtrado)
    }

report.append(f"\n📊 TOTAL DE REGISTROS ANALIZADOS PARA JAMUNDÍ: {total_filtrado:,}")

# 3. ANÁLISIS TEMPORAL (solo Jamundí)
report.append("\n📅 TENDENCIAS TEMPORALES - JAMUNDÍ")
report.append("-"*70)

for tipo, datos in datos_jamundi.items():
    df = datos["df"]
    fecha_col = datos["fecha_col"]
    
    if fecha_col and len(df) > 0:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        df_time = df[df[fecha_col].notna()].copy()
        
        if len(df_time) > 0:
            años = sorted(df_time[fecha_col].dt.year.dropna().unique().astype(int).tolist())
            
            report.append(f"\n{tipo} en Jamundí:")
            report.append(f"  • Período disponible: {min(años) if años else 'N/A'} - {max(años) if años else 'N/A'}")
            report.append(f"  • Registros con fecha: {len(df_time):,} ({len(df_time)/len(df)*100:.1f}%)")
            
            # Tendencia anual
            if len(años) >= 2:
                anual = df_time.groupby(df_time[fecha_col].dt.year).size()
                primera, ultima = anual.iloc[0], anual.iloc[-1]
                cambio = ((ultima - primera) / primera * 100) if primera != 0 else 0
                tendencia = "📈 ALZA" if cambio > 10 else "📉 BAJA" if cambio < -10 else "➡️ ESTABLE"
                report.append(f"  • Tendencia ({min(años)}→{max(años)}): {tendencia} ({cambio:+.1f}%)")
            
            # Estacionalidad mensual
            if len(df_time) >= 12:
                meses_top = df_time[fecha_col].dt.month_name(locale='es_ES').value_counts().head(3)
                if len(meses_top) > 0:
                    report.append(f"  • Meses con más casos: {', '.join(meses_top.index.tolist())}")
            
            # Días críticos
            dias_top = df_time[fecha_col].dt.date.value_counts().head(3)
            if len(dias_top) > 0:
                report.append(f"  • Fechas con picos históricos:")
                for fecha, count in dias_top.items():
                    report.append(f"    - {fecha}: {count} casos")
        else:
            report.append(f"\n{tipo}: ⚠️ Sin fechas válidas para análisis temporal en Jamundí")
    else:
        report.append(f"\n{tipo}: ⚠️ Sin datos temporales para análisis en Jamundí")

# 4. ANÁLISIS GEOGRÁFICO DENTRO DE JAMUNDÍ
report.append("\n🗺️ DISTRIBUCIÓN TERRITORIAL DENTRO DE JAMUNDÍ")
report.append("-"*70)

for tipo, datos in datos_jamundi.items():
    df = datos["df"]
    ubic_col = datos["ubic_col"]
    
    if ubic_col and ubic_col in df.columns:
        df_ubic = df[df[ubic_col].notna()].copy()
        
        if len(df_ubic) > 0:
            top_ubic = df_ubic[ubic_col].value_counts().head(5)
            total_ubic = len(df_ubic)
            
            report.append(f"\n{tipo} - ZONAS CRÍTICAS EN JAMUNDÍ:")
            report.append(f"  (Registros con ubicación: {total_ubic:,} / {len(df):,} = {total_ubic/len(df)*100:.1f}%)")
            
            for i, (zona, count) in enumerate(top_ubic.items(), 1):
                pct = count / total_ubic * 100
                barra = "█" * int(pct / 4)
                zona_clean = str(zona)[:35].ljust(35)
                report.append(f"  {i}. {zona_clean} {count:4d} casos {barra} {pct:5.1f}%")
            
            # Alerta de hiperconcentración
            if len(top_ubic) > 0:
                top1_pct = top_ubic.iloc[0] / total_ubic * 100
                if top1_pct > 20:
                    report.append(f"\n  ⚠️ ALERTA: {top_ubic.index[0]} concentra el {top1_pct:.1f}% de los casos")
        else:
            report.append(f"\n{tipo}: ⚠️ Sin datos de ubicación dentro de Jamundí")
    else:
        report.append(f"\n{tipo}: ⚠️ Sin columna de barrio/zona para análisis intra-municipal")

# 5. PERFILIZACIÓN EN JAMUNDÍ
report.append("\n👥 CARACTERIZACIÓN DE CASOS EN JAMUNDÍ")
report.append("-"*70)

for tipo, datos in datos_jamundi.items():
    df = datos["df"]
    modalidad_col = datos["modalidad_col"]
    
    if modalidad_col and modalidad_col in df.columns:
        top_mod = df[modalidad_col].value_counts().head(5)
        report.append(f"\n{tipo} - MODALIDADES MÁS FRECUENTES EN JAMUNDÍ:")
        for i, (mod, count) in enumerate(top_mod.items(), 1):
            pct = count / len(df) * 100
            mod_clean = str(mod)[:45].ljust(45)
            report.append(f"  {i}. {mod_clean} {pct:5.1f}%")
    else:
        report.append(f"\n{tipo}: ⚠️ Sin datos de modalidad para caracterización")

# 6. INDICADORES DE RIESGO ESPECÍFICOS PARA JAMUNDÍ
report.append("\n⚠️ INDICADORES DE RIESGO - CONTEXTO JAMUNDÍ")
report.append("-"*70)

riesgos_jamundi = []

for tipo, datos in datos_jamundi.items():
    df = datos["df"]
    fecha_col = datos["fecha_col"]
    ubic_col = datos["ubic_col"]
    
    # Concentración temporal en Jamundí
    if fecha_col and len(df) > 10:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        df_clean = df[df[fecha_col].notna()]
        if len(df_clean) > 0:
            dias = df_clean[fecha_col].dt.date.value_counts()
            if len(dias) > 0 and dias.max() / len(df_clean) > 0.05:
                riesgos_jamundi.append(f"• {tipo}: Picos agudos en fechas específicas (hasta {dias.max()} casos en un día)")
    
    # Concentración espacial en Jamundí
    if ubic_col and ubic_col in df.columns:
        top1 = df[ubic_col].value_counts().iloc[0] if len(df[ubic_col].dropna()) > 0 else None
        if top1 and top1 / len(df) > 0.15:
            zona = df[ubic_col].value_counts().index[0]
            riesgos_jamundi.append(f"• {tipo}: Hiperconcentración en '{zona}' ({top1/len(df)*100:.1f}% de casos)")

if riesgos_jamundi:
    for r in riesgos_jamundi:
        report.append(f"  {r}")
else:
    report.append("  • No se identificaron patrones de riesgo extremo con los datos disponibles para Jamundí")

# 7. RECOMENDACIONES OPERATIVAS PARA JAMUNDÍ
report.append("\n🎯 RECOMENDACIONES PARA EL CONCEJO DE SEGURIDAD DE JAMUNDÍ")
report.append("-"*70)
report.append(f"""
1. VIGILANCIA DINÁMICA EN JAMUNDÍ
   • Desplegar patrullaje preventivo en fechas con histórico de picos delictivos
   • Coordinar con CAI y cuadrantes de la Policía para rotación inteligente

2. ENFOQUE BARRIAL
   • Priorizar intervenciones en las zonas TOP 3 identificadas dentro del municipio
   • Trabajar con Juntas de Acción Comunal para prevención comunitaria focalizada

3. CORREDOR CALI-JAMUNDÍ-POPAYÁN
   • Fortalecer controles en vías de acceso al municipio (movilidad delictiva)
   • Coordinar con municipios vecinos para operativos conjuntos

4. PREVENCIÓN SITUACIONAL LOCAL
   • Mejorar iluminación en puntos críticos identificados dentro de Jamundí
   • Promover denuncias anónimas a través de canales municipales

5. MONITOREO CONTINUO
   • Actualizar este análisis mensualmente para detectar cambios de tendencia
   • Cruzar con datos de captura y judicialización del municipio

6. COORDINACIÓN INTERINSTITUCIONAL
   • Socializar hallazgos con Policía, Fiscalía, Personería y Gobernación del Valle
   • Alinear con el Plan de Desarrollo Municipal y el PESV de Jamundí
""")

# 8. LIMITACIONES ESPECÍFICAS
report.append("⚠️ LIMITACIONES DEL ANÁLISIS PARA JAMUNDÍ")
report.append("-"*70)
report.append("""
• Los resultados dependen de que los datos fuente incluyan identificación municipal
• Si no hay columna de municipio, se asume que todo el archivo corresponde a Jamundí
• La ausencia de columnas clave (barrio, fecha, víctima) limita el análisis intra-municipal
• Este reporte refleja registros, no necesariamente casos judicializados en Jamundí
• Se recomienda validar con fuentes locales: Policía, Inspección de Policía, Personería
""")

# 9. METADATOS
report.append("\n📄 METADATOS DEL REPORTE")
report.append("-"*70)
report.append(f"• Municipios filtrados: {MUNICIPIO_OBJETIVO}, Valle del Cauca")
report.append(f"• Archivos procesados: {', '.join(archivos.keys())}")
report.append(f"• Registros totales analizados para Jamundí: {total_filtrado:,}")
report.append(f"• Herramienta: OpenClaw + Python/pandas")
report.append(f"• Clasificación: Uso interno - Concejo de Seguridad de Jamundí")

# Guardar informe
nombre_archivo = f"OBSERVATORIO_JAMUNDI_{datetime.now().strftime('%Y%m%d')}.txt"
with open(nombre_archivo, "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print(f"\n✅ INFORME GENERADO: {nombre_archivo}")
print(f"💾 Ubicado en: C:\\Users\\Usuario\\.openclaw\\workspace\\{nombre_archivo}")
print("\n📬 Listo para presentar ante el Concejo de Seguridad de Jamundí.")
