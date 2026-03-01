import requests

CHANNEL_TOKEN = "86fd5ad8af1b4db2b56bfc60a05ec867"
BASE = "https://www.mindefensa.gov.co/sites/web/content/published/api/v1.1"

# IDs reales capturados en sesiones anteriores
pruebas = [
    ("DELITOS CONTRA EL MEDIO AMBIENTE.xlsx", "CONT8A90C91C09374BC0BBD44108E631B2B1"),
    ("AFECTACION A LA FUERZA PUBLICA.xlsx",   "CONT9DC8FFA70F73409DBD3B60EBAF72A7C3"),
    ("DESMOVILIZADOS ELN.xlsx",               "CONT28FBFDEE1CEB493B8271EE7CED2A3B38"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"
}

for nombre, item_id in pruebas:
    print(f"\n{nombre}:")
    urls = [
        f"{BASE}/assets/{item_id}/native?siteId=Sitio-Web-Ministerio-Defensa&channelToken={CHANNEL_TOKEN}",
        f"{BASE}/assets/{item_id}/native?channelToken={CHANNEL_TOKEN}",
        f"{BASE}/items/{item_id}/renditions/Attachment?channelToken={CHANNEL_TOKEN}",
        f"{BASE}/items/{item_id}/rendition?channelToken={CHANNEL_TOKEN}",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
            ct = r.headers.get("content-type","")
            print(f"  [{r.status_code}] {len(r.content):,} bytes | {ct[:50]}")
            print(f"       {url[60:120]}")
            if r.status_code == 200 and len(r.content) > 5000:
                with open(f"TEST_{nombre}", "wb") as f:
                    f.write(r.content)
                print(f"  ✅ DESCARGADO!")
                break
        except Exception as e:
            print(f"  ERROR: {e}")
