import pandas as pd
import numpy as np
import os
from datetime import datetime

print("🔍 OBSERVATORIO DEL DELITO - JAMUNDÍ, VALLE DEL CAUCA")
print("="*70)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*70 + "\n")

# Configuración: Jamundí puede estar escrito de varias formas
JAMUNDI_NAMES = ["JAMUNDÍ", "JAMUNDI", "Jamundí", "Jamundi", "jamundí", "jamundi"]
JAMUNDI_CODE = 76364  # Código DANE oficial de Jamundí, Valle

archivos = {
    "HOMICIDIO INTENCIONAL": "HOMICIDIO INTENCIONAL.xlsx",
    "SECUESTRO": "SECUESTRO.xlsx"
}

def detectar_columna(df, keywords):
    cols_lower = [str(c).lower().strip() for c in df.columns]
    for kw in keywords:
        for i, col in enumerate(cols_lower):
            if kw in col:
                return df.columns[i]
    return None

def es_jamundi(valor):
    """Verifica si un valor corresponde a Jamundí (nombre o código)"""
    if pd.isna(valor):
        return False
    val_str = str(valor).strip().upper()
    # Por nombre
    if any(j.upper() in val_str for j in JAMUNDI_NAMES):
        return True
    # Por código DANE
    try:
        if int(float(valor)) == JAMUNDI_CODE:
            return True
    except:
        pass
    return False

report = []
report.append("OBSERVATORIO DEL DELITO - MUNICIPIO DE JAMUNDÍ, VALLE DEL CAUCA")
report.append(f"Reporte generado: {datetime.now().strftime('%d/%m/%Y')}")
report.append("Fuente: Datos nacionales filtrados para Jamundí (cod_muni=76364)")
report.append("Herramienta: OpenClaw + Python/pandas")
report.append("="*70 + "\n")

# 1. CONTEXTO
report.append("📍 CONTEXTO: JAMUNDÍ, VALLE DEL CAUCA")
report.append("-"*70)
report.append("""
• Código DANE: 76364 | Departamento: Valle del Cauca (76)
• Ubicación: Sur del Valle, área metropolitana de Cali
• Población: ~150.000 hab. | Característica: Corredor Cali-Popayán
• Retos: Movilidad delictiva, microtráfico, presencia de grupos armados
""")

# 2. CARGA Y FILTRADO
report.append("📥 FILTRADO DE DATOS NACIONALES → JAMUNDÍ")
report.append("-"*70)

datos_jamundi = {}
total_jamundi = 0

for tipo, ruta in archivos.items():
    if not os.path.exists(ruta):
        report.append(f"⚠️ No encontrado: {ruta}")
        continue
    
    df = pd.read_excel(ruta)
    df.columns = [c.lower().strip() for c in df.columns]
    total_original = len(df)
    
    # Detectar columnas
    col_municipio = detectar_columna(df, ["municipio"])
    col_cod_muni = detectar_columna(df, ["cod_muni", "codigo_municipio", "cod_mpio"])
    
    # Filtrar por Jamundí (nombre O código)
    if col_municipio:
        mask_nombre = df[col_municipio].astype(str).str.upper().str.contains("JAMUNDI", na=False)
    else:
        mask_nombre = pd.Series([False]*len(df))
    
    if col_cod_muni:
        mask_codigo = df[col_cod_muni].astype(str).str.strip() == str(JAMUNDI_CODE)
    else:
        mask_codigo = pd.Series([False]*len(df))
    
    mask_final = mask_nombre | mask_codigo
    df_jamundi = df[mask_final].copy()
    
    report.append(f"\n{tipo}:")
    report.append(f"  • Registros nacionales: {total_original:,}")
    report.append(f"  • Filtro aplicado: municipio LIKE '%JAMUNDI%' OR cod_muni = {JAMUNDI_CODE}")
    report.append(f"  • ✅ Registros de Jamundí: {len(df_jamundi):,} ({len(df_jamundi)/total_original*100:.3f}%)")
    
    if len(df_jamundi) == 0:
        report.append(f"  ⚠️ No se encontraron registros. Verificando valores únicos...")
        if col_municipio and len(df) > 0:
            ejemplos = df[col_municipio].dropna().astype(str).unique()[:20]
            jamundi_like = [v for v in ejemplos if "JAMUND" in v.upper()]
            if jamundi_like:
                report.append(f"  💡 Posibles variantes: {jamundi_like}")
        continue
    
    total_jamundi += len(df_jamundi)
    
    # Detectar columnas para análisis
    datos_jamundi[tipo] = {
        "df": df_jamundi,
        "fecha_col": detectar_columna(df_jamundi, ["fecha", "date", "hecho", "ocurrencia"]),
        "ubic_col": detectar_columna(df_jamundi, ["zona", "barrio", "sector", "comuna", "vereda", "direccion"]),
        "modalidad_col": detectar_columna(df_jamundi, ["modalidad", "descripcion", "conducta", "tipo", "arma"]),
        "victima_col": detectar_columna(df_jamundi, ["sexo", "edad", "víctima", "genero"])
    }

report.append(f"\n📊 TOTAL REGISTROS DE JAMUNDÍ ANALIZADOS: {total_jamundi:,}")

if total_jamundi == 0:
    report.append("\n❌ ERROR: No se encontraron registros para Jamundí con los filtros aplicados.")
    report.append("💡 Posibles causas:")
    report.append("   • El nombre en los datos es diferente (ej: código numérico)")
    report.append("   • Los archivos ya son solo de Jamundí (no necesitan filtro)")
    report.append("   • Jamundí aparece con otro formato (revisar valores únicos)")
else:
    # 3. ANÁLISIS TEMPORAL
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
                report.append(f"  • Período: {min(años) if años else 'N/A'} - {max(años) if años else 'N/A'}")
                report.append(f"  • Registros con fecha: {len(df_time):,}")
                
                # Tendencia
                if len(años) >= 2:
                    anual = df_time.groupby(df_time[fecha_col].dt.year).size()
                    primera, ultima = anual.iloc[0], anual.iloc[-1]
                    cambio = ((ultima - primera) / primera * 100) if primera != 0 else 0
                    tendencia = "📈 ALZA" if cambio > 10 else "📉 BAJA" if cambio < -10 else "➡️ ESTABLE"
                    report.append(f"  • Tendencia: {tendencia} ({cambio:+.1f}%)")
                
                # Meses críticos
                if len(df_time) >= 12:
                    meses = df_time[fecha_col].dt.month_name(locale='es_ES').value_counts().head(3)
                    if len(meses) > 0:
                        report.append(f"  • Meses con más casos: {', '.join(meses.index.tolist())}")
                
                # Fechas pico
                dias = df_time[fecha_col].dt.date.value_counts().head(3)
                if len(dias) > 0:
                    report.append(f"  • Fechas con picos:")
                    for f, c in dias.items():
                        report.append(f"    - {f}: {c} casos")
    
    # 4. ANÁLISIS GEOGRÁFICO (zonas dentro de Jamundí)
    report.append("\n🗺️ DISTRIBUCIÓN INTRA-MUNICIPAL - JAMUNDÍ")
    report.append("-"*70)
    
    for tipo, datos in datos_jamundi.items():
        df = datos["df"]
        ubic_col = datos["ubic_col"]
        
        if ubic_col and ubic_col in df.columns:
            df_ubic = df[df[ubic_col].notna()].copy()
            if len(df_ubic) > 0:
                top = df_ubic[ubic_col].value_counts().head(5)
                report.append(f"\n{tipo} - TOP ZONAS EN JAMUNDÍ:")
                for i, (zona, count) in enumerate(top.items(), 1):
                    pct = count / len(df_ubic) * 100
                    barra = "█" * int(pct / 5)
                    report.append(f"  {i}. {str(zona)[:30]:<30} {count:4d} {barra} {pct:.1f}%")
            else:
                report.append(f"\n{tipo}: ⚠️ Sin datos de zona/barrio")
        else:
            # Mostrar valores de 'zona' si existe
            if "zona" in df.columns:
                top_zona = df["zona"].value_counts()
                report.append(f"\n{tipo} - Distribución por ZONA:")
                for zona, count in top_zona.items():
                    pct = count / len(df) * 100
                    report.append(f"  • {zona}: {count:,} ({pct:.1f}%)")
    
    # 5. CARACTERIZACIÓN
    report.append("\n👥 CARACTERIZACIÓN DE CASOS - JAMUNDÍ")
    report.append("-"*70)
    
    for tipo, datos in datos_jamundi.items():
        df = datos["df"]
        
        # Por sexo (si hay columna)
        if datos["victima_col"] and datos["victima_col"] in df.columns:
            col = datos["victima_col"]
            top_sex = df[col].value_counts().head(3)
            report.append(f"\n{tipo} - Por {col}:")
            for val, count in top_sex.items():
                pct = count / len(df) * 100
                report.append(f"  • {val}: {pct:.1f}%")
        
        # Por modalidad (si hay columna)
        if datos["modalidad_col"] and datos["modalidad_col"] in df.columns:
            col = datos["modalidad_col"]
            top_mod = df[col].value_counts().head(5)
            report.append(f"\n{tipo} - Modalidades:")
            for val, count in top_mod.items():
                pct = count / len(df) * 100
                report.append(f"  • {str(val)[:40]}: {pct:.1f}%")
    
    # 6. INDICADORES DE RIESGO
    report.append("\n⚠️ INDICADORES DE RIESGO - JAMUNDÍ")
    report.append("-"*70)
    
    for tipo, datos in datos_jamundi.items():
        df = datos["df"]
        fecha_col = datos["fecha_col"]
        
        if fecha_col and len(df) > 20:
            df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
            df_clean = df[df[fecha_col].notna()]
            if len(df_clean) > 0:
                # Concentración por día
                dias = df_clean[fecha_col].dt.date.value_counts()
                if len(dias) > 0 and dias.max() / len(df_clean) > 0.03:
                    report.append(f"• {tipo}: Picos agudos ({dias.max()} casos en un día)")
                
                # Estacionalidad marcada
                meses = df_clean[fecha_col].dt.month.value_counts()
                if len(meses) > 0 and meses.max() / len(df_clean) > 0.15:
                    mes_name = pd.Timestamp(2024, meses.index[0], 1).month_name(locale='es_ES')
                    report.append(f"• {tipo}: Estacionalidad en {mes_name} ({meses.max()/len(df_clean)*100:.1f}% de casos)")
    
    # 7. RECOMENDACIONES
    report.append("\n🎯 RECOMENDACIONES - CONCEJO DE SEGURIDAD JAMUNDÍ")
    report.append("-"*70)
    report.append("""
1. VIGILANCIA DINÁMICA
   • Patrullaje preventivo en fechas con picos históricos identificados
   • Coordinación con CAI y cuadrantes de Policía para rotación inteligente

2. ENFOQUE TERRITORIAL
   • Intervenciones focalizadas en zonas/barrios con mayor incidencia
   • Trabajo con Juntas de Acción Comunal para prevención comunitaria

3. CORREDOR ESTRATÉGICO CALI-JAMUNDÍ-POPAYÁN
   • Controles en vías de acceso (prevención de movilidad delictiva)
   • Operativos conjuntos con municipios vecinos del Valle

4. PREVENCIÓN SITUACIONAL
   • Mejorar iluminación y vigilancia en puntos críticos
   • Promover canales de denuncia anónima municipales

5. MONITOREO CONTINUO
   • Actualizar análisis mensualmente para detectar cambios de tendencia
   • Cruzar con datos de captura y judicialización local

6. COORDINACIÓN INTERINSTITUCIONAL
   • Socializar hallazgos con Policía, Fiscalía, Personería y Gobernación del Valle
   • Alinear con Plan de Desarrollo Municipal y PESV de Jamundí
""")
    
    # 8. LIMITACIONES
    report.append("⚠️ LIMITACIONES")
    report.append("-"*70)
    report.append("""
• Datos filtrados por nombre/código de municipio; posibles falsos negativos si el formato varía
• Registros reflejan ocurrencias reportadas, no necesariamente casos judicializados
• Ausencia de columnas clave limita análisis de perfilización completa
• Se recomienda validar con fuentes locales: Policía, Inspección, Personería de Jamundí
""")

# Guardar informe
nombre_archivo = f"OBSERVATORIO_JAMUNDI_{datetime.now().strftime('%Y%m%d')}.txt"
with open(nombre_archivo, "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print(f"\n✅ INFORME GENERADO: {nombre_archivo}")
print(f"💾 Ruta: C:\\Users\\Usuario\\.openclaw\\workspace\\{nombre_archivo}")
print("\n📬 Listo para presentar ante el Concejo de Seguridad de Jamundí.")
