import pandas as pd
import os
from datetime import datetime

print("🔍 ANALIZANDO DATOS DE JAMUNDÍ...")
print("="*60)

archivos = {
    "HOMICIDIO INTENCIONAL": "HOMICIDIO INTENCIONAL.xlsx",
    "SECUESTRO": "SECUESTRO.xlsx"
}

resultados = []

for nombre, ruta in archivos.items():
    if not os.path.exists(ruta):
        print(f"❌ No encontré: {ruta}")
        continue
    
    df = pd.read_excel(ruta)
    df.columns = [c.lower().strip() for c in df.columns]
    
    print(f"\n📁 {nombre}")
    print("-"*40)
    print(f"✅ Registros totales: {len(df):,}")
    print(f"📋 Columnas: {', '.join(df.columns)}")
    
    # Buscar columna de fecha
    fecha_col = next((c for c in df.columns if "fecha" in c.lower()), None)
    if fecha_col:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        años = sorted(df[fecha_col].dropna().dt.year.unique().astype(int).tolist())
        print(f"📅 Años: {años if años else 'Sin datos'}")
        
        # TOP 5 fechas
        top_fechas = df[fecha_col].value_counts().head(5)
        print(f"📊 TOP 5 fechas con más casos:")
        for fecha, count in top_fechas.items():
            print(f"   • {fecha.strftime('%d/%m/%Y')}: {count} casos")
    
    # Buscar columna de ubicación (barrio, zona, sector, comuna, municipio)
    ubic_col = next((c for c in df.columns if any(x in c.lower() for x in ["barrio","zona","sector","comuna","municipio","localidad"])), None)
    if ubic_col:
        top_ubic = df[ubic_col].value_counts().head(5)
        print(f"📍 TOP 5 por {ubic_col}:")
        for ubic, count in top_ubic.items():
            print(f"   • {ubic}: {count} casos")
    
    # Guardar para el informe
    resultados.append({
        "nombre": nombre,
        "total": len(df),
        "años": años if fecha_col else [],
        "top_fechas": df[fecha_col].value_counts().head(5).to_dict() if fecha_col else {},
        "top_ubic": df[ubic_col].value_counts().head(5).to_dict() if ubic_col else {}
    })

# Generar informe para el concejo
print("\n" + "="*60)
print("📝 INFORME PARA EL CONCEJO DE SEGURIDAD - JAMUNDÍ")
print("="*60)

todos_anos = sorted(set(a for r in resultados for a in r["años"]))
rango = f"{min(todos_anos)}-{max(todos_anos)}" if todos_anos else "N/A"

print(f'''
FECHA: {datetime.now().strftime('%d/%m/%Y')}
PERÍODO ANALIZADO: {rango}

RESUMEN EJECUTIVO:
''')

for r in resultados:
    print(f"• {r['nombre']}: {r['total']:,} registros")
    if r["top_ubic"]:
        zona_critica = list(r["top_ubic"].items())[0]
        print(f"  → Zona más crítica: {zona_critica[0]} ({zona_critica[1]} casos)")

print('''
RECOMENDACIONES:
1. Reforzar patrullaje en zonas con mayor incidencia.
2. Coordinar operativos en fechas con picos históricos.
3. Fortalecer trabajo comunitario en barrios críticos.
4. Mantener monitoreo continuo de tendencias.

"La prevención requiere datos, coordinación y acción constante."
''')

# Guardar en archivo
with open("informe_jamundi_concejo.txt", "w", encoding="utf-8") as f:
    f.write(f"INFORME JAMUNDÍ - {datetime.now().strftime('%d/%m/%Y')}\n")
    f.write("="*60 + "\n")
    for r in resultados:
        f.write(f"\n{r['nombre']}: {r['total']:,} registros\n")
    f.write("\n" + "="*60)

print("💾 Informe guardado: informe_jamundi_concejo.txt")
print("✅ ¡Listo para presentar!")
