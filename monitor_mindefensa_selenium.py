from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import json
import pandas as pd
import hashlib
from datetime import datetime
from pathlib import Path
import time

print("="*80)
print("🔍 MONITOR MINDEFENSA - SELENIUM (JavaScript activado)")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE = Path("mindefensa_selenium.json")
OUTPUT_CSV = Path("listado_completo_selenium.csv")

def configurar_chrome():
    """Configura Chrome en modo headless con opciones para cargar contenido dinámico"""
    options = Options()
    options.add_argument('--headless')  # Sin ventana visible
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    return options

def extraer_archivos_selenium(driver, timeout=30):
    """Navega a la página y extrae archivos después de que JavaScript cargue el contenido"""
    
    print(f"🌐 Cargando página: {URL}")
    driver.get(URL)
    
    # Esperar a que aparezcan elementos con .xlsx (contenido dinámico)
    try:
        print("⏳ Esperando carga de contenido dinámico...")
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.xlsx')] | //text()[contains(., '.xlsx')]"))
        )
        # Dar un poco más de tiempo para que termine de renderizar
        time.sleep(5)
    except:
        print("⚠️ Timeout esperando contenido, procediendo con lo disponible...")
    
    # Obtener el HTML completo después de JavaScript
    html = driver.page_source
    
    archivos = []
    
    # Método 1: Buscar enlaces <a> con .xlsx
    enlaces = driver.find_elements(By.XPATH, "//a[contains(@href, '.xlsx')]")
    for enlace in enlaces:
        try:
            texto = enlace.text.strip()
            href = enlace.get_attribute('href')
            if texto and '.xlsx' in texto:
                archivos.append({"nombre": texto, "url": href, "fecha": "N/A", "fuente": "enlace"})
        except:
            continue
    
    # Método 2: Buscar texto plano con patrón de archivo + fecha
    if len(archivos) < 10:  # Si no encontró suficientes, buscar en texto
        lineas = html.split('\n')
        for i, linea in enumerate(lineas):
            # Patrón: NOMBRE.xlsx seguido de fecha
            match = re.search(r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)\s*\n*\s*([\d/]+,\s*[\d:]+)', linea, re.IGNORECASE)
            if match:
                nombre, fecha = match.groups()
                # Construir URL tentativa
                url = f"https://www.mindefensa.gov.co/sites/default/files/datos-y-cifras/{nombre.replace(' ', '%20')}"
                archivos.append({"nombre": nombre.strip(), "url": url, "fecha": fecha.strip(), "fuente": "texto"})
    
    # Eliminar duplicados por nombre
    vistos = set()
    unicos = []
    for arch in archivos:
        nombre_norm = arch["nombre"].upper().strip()
        if nombre_norm not in vistos:
            vistos.add(nombre_norm)
            arch["hash"] = hashlib.md5(f"{arch['nombre']}{arch['fecha']}".encode()).hexdigest()[:10]
            unicos.append(arch)
    
    return unicos, html

def cargar_estado():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"archivos": {}}

def guardar_estado(estado):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)

def main():
    driver = None
    try:
        # Configurar y lanzar Chrome
        print("🚀 Iniciando navegador Chrome (headless)...")
        options = configurar_chrome()
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Extraer archivos
        archivos_actuales, html_raw = extraer_archivos_selenium(driver)
        
        if not archivos_actuales:
            print("\n⚠️ No se encontraron archivos .xlsx incluso con JavaScript")
            print("\n📄 Últimos 2000 caracteres del HTML renderizado:")
            print("-"*80)
            print(html_raw[-2000:])
            print("-"*80)
            return
        
        print(f"\n✅ Encontrados {len(archivos_actuales)} archivos con Selenium\n")
        
        # Cargar estado previo
        estado = cargar_estado()
        previos = estado.get("archivos", {})
        
        # Detectar cambios
        nuevos = [a for a in archivos_actuales if a["nombre"] not in previos]
        actualizados = [
            a for a in archivos_actuales 
            if a["nombre"] in previos and previos[a["nombre"]].get("hash") != a["hash"]
        ]
        
        # Mostrar resultados
        print("="*80)
        print("📊 RESULTADOS COMPLETOS")
        print("="*80)
        print(f"\n📋 RESUMEN:")
        print(f"   • Total archivos: {len(archivos_actuales)}")
        print(f"   • Nuevos: {len(nuevos)}")
        print(f"   • Actualizados: {len(actualizados)}")
        print(f"   • Última revisión: {estado.get('ultima_revision', 'N/A')}")
        
        # Listado completo
        print(f"\n📂 LISTADO DE ARCHIVOS:")
        print("-"*80)
        for i, arch in enumerate(sorted(archivos_actuales, key=lambda x: x["nombre"]), 1):
            estado_icon = "🆕" if arch in nuevos else "🔄" if arch in actualizados else "  "
            print(f"{estado_icon} {i:2d}. {arch['nombre']:<50} {arch['fecha']:>20}")
        
        # Guardar CSV
        df = pd.DataFrame(archivos_actuales)
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"\n💾 Listado guardado en: {OUTPUT_CSV}")
        
        # Guardar estado
        estado["ultima_revision"] = datetime.now().isoformat()
        estado["archivos"] = {a["nombre"]: a for a in archivos_actuales}
        guardar_estado(estado)
        print(f"💾 Estado guardado en: {STATE_FILE}")
        
        # Alertas
        if nuevos or actualizados:
            print(f"\n🎯 CAMBIOS DETECTADOS - ACCIÓN RECOMENDADA:")
            for a in nuevos:
                print(f"   🆕 {a['nombre']}")
            for a in actualizados:
                print(f"   🔄 {a['nombre']}: {previos[a['nombre']].get('fecha')} → {a['fecha']}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n🔚 Navegador cerrado")

if __name__ == "__main__":
    main()
