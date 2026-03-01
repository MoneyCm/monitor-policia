from playwright.sync_api import sync_playwright
import json

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
CHANNEL_TOKEN = "86fd5ad8af1b4db2b56bfc60a05ec867"

todas_las_requests = []

def on_request(request):
    todas_las_requests.append({
        "url": request.url,
        "method": request.method
    })

def on_response(response):
    url = response.url.lower()
    if any(x in url for x in [".xlsx", "download", "rendition", "attachment", "binary"]):
        print(f"[RED] {response.status} {response.url[:120]}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    page.on("request", on_request)
    page.on("response", on_response)

    print("Cargando pagina...")
    try:
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    except: pass
    page.wait_for_timeout(6000)

    print("Buscando elementos clicables...")
    # Buscar todos los elementos que contengan texto de archivos
    elementos = page.query_selector_all("a, button, [role='button'], [onclick]")
    print(f"Elementos encontrados: {len(elementos)}")

    # Mostrar los primeros 20 con su texto y href
    print("\nPrimeros elementos con texto relevante:")
    count = 0
    for el in elementos:
        try:
            texto = (el.inner_text() or "").strip()[:60]
            href  = el.get_attribute("href") or ""
            onclick = el.get_attribute("onclick") or ""
            if any(x in texto.upper() for x in ["XLSX","HOMICIDIO","HURTO","DELITO","SECUESTRO","EXTORS"]):
                print(f"  [{el.tag_name()}] texto='{texto}' href='{href[:80]}' onclick='{onclick[:60]}'")
                count += 1
                if count >= 5:
                    break
        except: pass

    # Intentar clic en el primer elemento que parezca un archivo
    print("\nIntentando descargar con expect_download...")
    try:
        with page.expect_download(timeout=15000) as dl_info:
            # Buscar por texto visible
            page.get_by_text("HOMICIDIO INTENCIONAL", exact=False).first.click(timeout=8000)
        dl = dl_info.value
        print(f"URL descarga: {dl.url}")
        print(f"Nombre sugerido: {dl.suggested_filename}")
    except Exception as e:
        print(f"Error clic: {e}")

    # Mostrar todas las requests que se hicieron
    print("\n--- Ultimas 20 requests de red ---")
    for r in todas_las_requests[-20:]:
        if any(x in r["url"].lower() for x in ["rendition","download","xlsx","binary","attachment","content"]):
            print(f"  {r['method']} {r['url'][:120]}")

    input("\nPRESIONA ENTER para cerrar el navegador (podés ver la pagina abierta)...")
    browser.close()
