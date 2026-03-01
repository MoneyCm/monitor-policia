import pandas as pd
import os

print("🔍 DIAGNÓSTICO DE ARCHIVOS - JAMUNDÍ")
print("="*70)

archivos = ["HOMICIDIO INTENCIONAL.xlsx", "SECUESTRO.xlsx"]

for ruta in archivos:
    if not os.path.exists(ruta):
        print(f"\n❌ No encontrado: {ruta}")
        continue
    
    print(f"\n{'='*70}")
    print(f"📁 ARCHIVO: {ruta}")
    print(f"{'='*70}")
    
    df = pd.read_excel(ruta)
    df.columns = [c.lower().strip() for c in df.columns]
    
    print(f"\n📋 TODAS LAS COLUMNAS ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    print(f"\n📈 Total registros: {len(df):,}")
    
    # Buscar columnas que podrían ser ubicación/municipio
    posibles_municipio = [c for c in df.columns if any(x in c.lower() for x in ["municipio","ciudad","localidad","area","cabecera","cod_mpio","departamento","zona","barrio","sector","comuna","vereda"])]
    
    if posibles_municipio:
        print(f"\n📍 POSIBLES COLUMNAS DE UBICACIÓN:")
        for col in posibles_municipio:
            print(f"  • {col}")
            valores_unicos = df[col].dropna().astype(str).unique()[:10]
            print(f"    → Ejemplos: {', '.join([str(v)[:30] for v in valores_unicos])}")
            if len(valores_unicos) > 10:
                print(f"    → ({len(valores_unicos)} valores únicos en total)")
            
            # Buscar si hay algo que se parezca a Jamundí
            jamundi_like = [v for v in valores_unicos if "jamund" in str(v).lower()]
            if jamundi_like:
                print(f"    ✅ ENCONTRÉ JAMUNDÍ: {jamundi_like[:5]}")
    else:
        print(f"\n⚠️ NO SE ENCONTRÓ NINGUNA COLUMNA QUE PAREZCA DE MUNICIPIO/UBICACIÓN")
        print(f"💡 ESTO SIGNIFICA QUE EL ARCHIVO PROBABLEMENTE YA ES SOLO DE JAMUNDÍ")
    
    # Mostrar primeras 3 filas completas
    print(f"\n📄 PRIMERAS 3 FILAS (para ver estructura):")
    print(df.head(3).to_string())

print("\n" + "="*70)
print("✅ DIAGNÓSTICO COMPLETADO")
print("="*70)
