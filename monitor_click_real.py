from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json, re, pandas as pd, os, time
from datetime import datetime
from pathlib import Path

print("="*80)
print("🔍 MONITOR + DESCARGA REAL - CLICK EN ENLACES")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
STATE_FILE = Path("mindefensa_monitor_final.json")
OUTPUT_CSV = Path("listado_mindefensa_final.csv")
DOWNLOAD_DIR = Path("workspace")
DOWNLOAD_DIR.mkdir(exist_ok=True)

JAMUNDI_CODE = 76364
ARCHIVOS_INTERES = [
    "HOMICIDIO INTENCIONAL.xlsx", "SECUESTRO.xlsx", "EXTORSIÓN.xlsx",
    "HURTO PERSONAS.xlsx", "VIOLENCIA INTRAFAMILIAR.xlsx",
    "DELITOS INFORMÁTICOS.xlsx", "TERRORISMO.xlsx", "MASACRES.xlsx"
]

archivos_encontrados = []

def interceptar_respuesta(response):
    """Captura archivos desde APIs de Oracle SCS"""
    if response.status != 200 or "json" not in response.headers.get("content-type", "").lower():
        return
    try:
        buscar_en_json(response.json())
    except:
        pass

def buscar_en_json(obj, nivel=0):
    if nivel > 5: return
    if isinstance(obj, dict):
        if obj.get("type") == "DocumentFile" and "fields" in obj:
            fields = obj.get("fields", {})
            nombre = fields.get("name") or fields.get("filename") or obj.get("name")
            if nombre and str(nombre).upper().endswith(".XLSX"):
                archivos_encontrados.append({"nombre": str(nombre).strip(), "id": obj.get("id")})
        for v in obj.values():
            if isinstance(v, (dict, list)): buscar_en_json(v, nivel+1)
    elif isinstance(obj, list):
        for item in obj: buscar_en_json(item, nivel+1)

def cargar_estado():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"archivos": {}}

def descargar_con_click(page, nombre_archivo, max_intentos=3):
    """Intenta descargar haciendo clic en el enlace visible"""
    for intento in range(max_intentos):
        try:
            # Buscar enlace por texto exacto o parcial
            selector = f"a:has-text('{nombre_archivo}'), a[href*='{nombre_archivo.replace(' ', '%20')}']"
            elemento = page.query_selector(selector)
            
            if not elemento:
                # Buscar en toda la página por texto
                elementos = page.query_selector_all(f"text={nombre_archivo}")
                if elementos:
                    elemento = elementos[0]
            
            if elemento:
                print(f"   📥 Clic en: {nombre_archivo} (intento {intento+1})...")
                
                # Esperar la descarga
                with page.expect_download(timeout=45000) as dl_info:
                    elemento.click(force=True)
                
                download = dl_info.value
                ruta_destino = DOWNLOAD_DIR / download.suggested_filename or nombre_archivo
                download.save_as(ruta_destino)
                
                tamaño = ruta_destino.stat().st_size
                if tamaño > 10000:  # Mínimo 10KB para considerar válido
                    print(f"   ✅ Guardado: {ruta_destino.name} ({tamaño/1024:.1f} KB)")
                    return True
                else:
                    print(f"   ⚠️ Archivo muy pequeño ({tamaño} bytes), reintentando...")
                    ruta_destino.unlink(missing_ok=True)
            else:
                print(f"   ⚠️ No se encontró enlace para: {nombre_archivo}")
                return False
                
        except PlaywrightTimeout:
            print(f"   ⚠️ Timeout en descarga, reintentando...")
            time.sleep(2)
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            time.sleep(2)
    
    return False

def analizar_jamundi(archivo_path):
    try:
        import pandas as pd
        df = pd.read_excel(archivo_path)
        df.columns = [c.lower().strip() for c in df.columns]
        
        col_muni = next((c for c in df.columns if "municipio" in c.lower() or "cod_muni" in c.lower()), None)
        col_fecha = next((c for c in df.columns if "fecha" in c.lower()), None)
        
        if not col_muni: return {"error": "No hay columna de municipio"}
        
        if "cod_muni" in col_muni.lower():
            df_j = df[df[col_muni].astype(str).str.strip() == str(JAMUNDI_CODE)].copy()
        else:
            df_j = df[df[col_muni].astype(str).str.upper().str.contains("JAMUNDI", na=False)].copy()
        
        resultado = {"total_original": len(df), "total_jamundi": len(df_j)}
        if col_fecha and len(df_j) > 0:
            df_j[col_fecha] = pd.to_datetime(df_j[col_fecha], errors='coerce')
            años = sorted(df_j[col_fecha].dropna().dt.year.unique().astype(int).tolist())
            resultado["años"] = años
            if len(años) >= 2:
                anual = df_j.groupby(df_j[col_fecha].dt.year).size()
                cambio = ((anual.iloc[-1] - anual.iloc[0]) / anual.iloc[0] * 100) if anual.iloc[0] != 0 else 0
                resultado["tendencia"] = "📈 ALZA" if cambio > 10 else "📉 BAJA" if cambio < -10 else "➡️ ESTABLE"
        return resultado
    except Exception as e:
        return {"error": str(e)}

def main():
    print("🚀 Iniciando monitoreo + descarga real...")
    
    # === FASE 1: Detectar archivos ===
    print("\n📡 FASE 1: Detectando archivos...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        page.on("response", interceptar_respuesta)
        page.goto(URL, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(5000)
        for i in range(3):
            page.evaluate(f"window.scrollTo(0, {i*400})")
            page.wait_for_timeout(500)
        browser.close()
    
    # Eliminar duplicados
    vistos, unicos = set(), []
    for a in archivos_encontrados:
        clave = a["nombre"].upper().strip()
        if clave and clave not in vistos:
            vistos.add(clave)
            unicos.append(a)
    
    print(f"   ✅ Encontrados {len(unicos)} archivos")
    
    # === FASE 2: Comparar estado ===
    print("\n🔍 FASE 2: Comparando con estado anterior...")
    estado = cargar_estado()
    previos = estado.get("archivos", {})
    
    nuevos = [a for a in unicos if a["nombre"] not in previos]
    actualizados = [a for a in unicos if a["nombre"] in previos]
    para_descargar = nuevos + actualizados[:5]
    
    print(f"   🆕 Nuevos: {len(nuevos)} | 🔄 Actualizados: {min(5, len(actualizados))}")
    
    # === FASE 3: Descargar con clicks reales ===
    descargados = 0
    if para_descargar:
        print(f"\n📥 FASE 3: Descargando con clicks reales...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=['--no-sandbox'])  # Headless=False para evitar bloqueos
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                accept_downloads=True
            )
            context.set_default_timeout(60000)
            page = context.new_page()
            
            # Configurar ruta de descarga
            page.set_extra_http_headers({"Referer": URL})
            page.goto(URL, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(3000)
            
            for arch in para_descargar:
                if descargar_con_click(page, arch["nombre"]):
                    descargados += 1
                    if any(inter in arch["nombre"].upper() for inter in [i.upper() for i in ARCHIVOS_INTERES]):
                        print(f"   🔍 Analizando Jamundí...")
                        res = analizar_jamundi(DOWNLOAD_DIR / arch["nombre"])
                        if "error" not in res:
                            print(f"      📊 Jamundí: {res['total_jamundi']:,} / {res['total_original']:,}")
                            if "años" in res: print(f"      📅 Años: {res['años']}")
                            if "tendencia" in res: print(f"      📈 Tendencia: {res['tendencia']}")
            
            browser.close()
        print(f"   ✅ Descargas: {descargados}/{len(para_descargar)}")
    
    # === FASE 4: Guardar estado ===
    print("\n💾 FASE 4: Guardando estado...")
    estado["ultima_revision"] = datetime.now().isoformat()
    estado["archivos"] = {a["nombre"]: {"detectado": datetime.now().isoformat()} for a in unicos}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    
    df = pd.DataFrame(unicos)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"   ✅ Listado: {OUTPUT_CSV}")
    
    # Resumen Jamundí
    informe = []
    for arch in DOWNLOAD_DIR.glob("*.xlsx"):
        if any(inter in arch.name.upper() for inter in [i.upper() for i in ARCHIVOS_INTERES]):
            res = analizar_jamundi(arch)
            if "total_jamundi" in res:
                informe.append({"archivo": arch.name, "jamundi": res["total_jamundi"], "total": res["total_original"]})
    
    if informe:
        with open(DOWNLOAD_DIR / "resumen_jamundi.txt", 'w', encoding='utf-8') as f:
            f.write("RESUMEN JAMUNDÍ\n" + "="*50 + "\n")
            for i in sorted(informe, key=lambda x: x["jamundi"], reverse=True):
                f.write(f"{i['archivo']}: {i['jamundi']:,} / {i['total']:,}\n")
        print(f"   📄 Resumen: resumen_jamundi.txt")
    
    print("\n" + "="*80)
    print("✅ PROCESO COMPLETADO")
    print("="*80)

if __name__ == "__main__":
    main()
