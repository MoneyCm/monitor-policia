import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re

print("🔍 LISTADOR DE ARCHIVOS - MINDEFENSA COLOMBIA")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("Fuente: https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    print("📡 Conectando a MinDefensa...")
    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    archivos = []
    
    # Buscar enlaces a archivos Excel/PDF
    # MinDefensa suele usar estructuras como <a href="*.xlsx"> o tablas con datos
    enlaces = soup.find_all('a', href=True)
    
    for link in enlaces:
        href = link['href']
        texto = link.get_text(strip=True)
        
        # Filtrar solo archivos de datos
        if any(ext in href.lower() for ext in ['.xlsx', '.xls', '.csv', '.pdf']):
            # Limpiar nombre
            nombre = texto if texto else href.split('/')[-1]
            
            # Intentar extraer fecha del contexto cercano
            fecha = "N/A"
            parent = link.find_parent()
            if parent:
                # Buscar texto con formato de fecha cerca del enlace
                texto_cercano = parent.get_text(strip=True)
                match_fecha = re.search(r'\d{1,2}/\d{1,2}/\d{4}', texto_cercano)
                if match_fecha:
                    fecha = match_fecha.group()
            
            # Tamaño (si está en la página)
            tamaño = "N/A"
            match_tamaño = re.search(r'[\d\.]+\s*(KB|MB|GB)', href + texto, re.I)
            if match_tamaño:
                tamaño = match_tamaño.group()
            
            # URL completa
            url_completa = href if href.startswith('http') else f"https://www.mindefensa.gov.co{href}"
            
            archivos.append({
                "Nombre": nombre,
                "Fecha": fecha,
                "Tamaño": tamaño,
                "Enlace": url_completa,
                "Tipo": href.split('.')[-1].upper()
            })
    
    # Si no encontró con el método anterior, buscar en tablas
    if len(archivos) == 0:
        print("🔍 Buscando en tablas de la página...")
        tablas = soup.find_all('table')
        for tabla in tablas:
            filas = tabla.find_all('tr')
            for fila in filas:
                celdas = fila.find_all(['td', 'th'])
                if len(celdas) >= 2:
                    nombre = celdas[0].get_text(strip=True)
                    fecha = celdas[1].get_text(strip=True) if len(celdas) > 1 else "N/A"
                    enlace_tag = celdas[0].find('a', href=True)
                    if enlace_tag and any(ext in enlace_tag['href'].lower() for ext in ['.xlsx', '.xls', '.csv']):
                        href = enlace_tag['href']
                        url_completa = href if href.startswith('http') else f"https://www.mindefensa.gov.co{href}"
                        archivos.append({
                            "Nombre": nombre,
                            "Fecha": fecha,
                            "Tamaño": "N/A",
                            "Enlace": url_completa,
                            "Tipo": href.split('.')[-1].upper() if '.' in href else "DESC"
                        })
    
    # Mostrar resultados
    if archivos:
        print(f"✅ Encontrados {len(archivos)} archivos de datos\n")
        
        # Crear DataFrame para mejor visualización
        df = pd.DataFrame(archivos)
        
        # Guardar en CSV para que lo abras en Excel
        df.to_csv("listado_mindefensa.csv", index=False, encoding='utf-8-sig')
        print(f"💾 Lista guardada en: listado_mindefensa.csv\n")
        
        # Mostrar en pantalla (primeros 30)
        print("📋 PRIMEROS 30 ARCHIVOS:")
        print("-"*80)
        for i, row in df.head(30).iterrows():
            print(f"{i+1:2d}. [{row['Tipo']:<4}] {row['Nombre'][:50]:<50} {row['Fecha']:>12}")
        
        if len(df) > 30:
            print(f"\n... y {len(df)-30} archivos más (ver archivo CSV completo)")
        
        # Resumen por tipo
        print(f"\n📊 RESUMEN POR TIPO DE ARCHIVO:")
        for tipo, count in df['Tipo'].value_counts().items():
            print(f"   • {tipo}: {count} archivos")
        
        # Filtros útiles
        print(f"\n🔎 FILTROS RÁPIDOS (podés usar estos comandos después):")
        print(f"   • Solo Excel: df[df['Tipo']=='XLSX']")
        print(f"   • Actualizados en 2026: df[df['Fecha'].str.contains('2026', na=False)]")
        print(f"   • Buscar por nombre: df[df['Nombre'].str.contains('HOMICIDIO', case=False, na=False)]")
        
    else:
        print("⚠️ No se encontraron archivos de datos con los métodos actuales.")
        print("💡 Posibles causas:")
        print("   • La página usa JavaScript para cargar los archivos (necesita Selenium)")
        print("   • Los enlaces tienen una estructura diferente")
        print("   • Requiere autenticación o cookies")
        
        # Mostrar un fragmento del HTML para diagnóstico
        print(f"\n🔍 Fragmento del HTML (para diagnóstico):")
        print(soup.prettify()[:2000])
        
except requests.exceptions.RequestException as e:
    print(f"❌ Error de conexión: {e}")
    print("💡 Verificá tu conexión a internet o si la página está disponible")
except Exception as e:
    print(f"❌ Error inesperado: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ Proceso completado")
