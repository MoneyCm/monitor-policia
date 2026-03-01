import requests, json
from pathlib import Path

CHANNEL_TOKEN = "86fd5ad8af1b4db2b56bfc60a05ec867"
STATE_FILE = Path("mindefensa_state.json")

# Cargar los IDs que ya tenemos guardados
with open(STATE_FILE, encoding="utf-8") as f:
    estado = json.load(f)

archivos = list(estado["archivos"].items())[:5]  # probar con 5

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
}

BASE = "https://www.mindefensa.gov.co/sites/web/content/published/api/v1.1"

for nombre, info in archivos:
    item_id = info.get("id","")
    if not item_id:
        print(f"Sin ID: {nombre}")
        continue

    # Probar las 3 variantes de URL
    urls = [
        f"{BASE}/assets/{item_id}/native?siteId=Sitio-Web-Ministerio-Defensa&channelToken={CHANNEL_TOKEN}",
        f"{BASE}/assets/{item_id}/native?channelToken={CHANNEL_TOKEN}",
        f"{BASE}/items/{item_id}/renditions/Attachment?channelToken={CHANNEL_TOKEN}",
    ]

    print(f"\n{nombre} (ID: {item_id[:20]}...):")
    for url in urls:
        r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        tipo = r.headers.get("content-type","")
        print(f"  [{r.status_code}] {len(r.content):,} bytes | {tipo[:60]}")
        print(f"  URL: {url[:100]}")
        if r.status_code == 200 and len(r.content) > 5000:
            Path(f"test_{nombre}").write_bytes(r.content)
            print(f"  ✅ GUARDADO!")
            break
