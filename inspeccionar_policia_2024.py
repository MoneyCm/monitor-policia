from playwright.sync_api import sync_playwright
import re

URL = "https://www.policia.gov.co/index.php/estadistica-delictiva-old"


def opts(select):
    out = []
    for o in select.query_selector_all("option"):
        out.append(((o.inner_text() or "").strip(), (o.get_attribute("value") or "").strip()))
    return out


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)

    selects = page.query_selector_all("select")
    scored = []
    for s in selects:
        o = opts(s)
        years = sum(1 for t, v in o if re.fullmatch(r"20\d{2}", t) or re.fullmatch(r"20\d{2}", v))
        scored.append((years, s, o))
    scored.sort(key=lambda x: x[0], reverse=True)

    _, select_year, year_opts = scored[0]
    select_delito = next(s for s in selects if s != select_year)

    years_map = {t: v for t, v in year_opts if re.fullmatch(r"20\d{2}", t)}
    if "2024" in years_map:
        if years_map["2024"]:
            select_year.select_option(value=years_map["2024"])
        else:
            select_year.select_option(label="2024")

    btn = page.locator("button:has-text('Buscar')").first
    delito_opts = [(t, v) for t, v in opts(select_delito) if t and "any" not in t.lower()]

    for t, v in delito_opts[:12]:
        if v:
            select_delito.select_option(value=v)
        else:
            select_delito.select_option(label=t)
        btn.click()
        page.wait_for_timeout(1200)

        links = []
        for a in page.query_selector_all("a[href]"):
            href = a.get_attribute("href") or ""
            if any(ext in href.lower() for ext in (".xlsx", ".xls", ".csv")):
                links.append(href)

        print(f"{t}: {len(links)} links")
        for h in links[:3]:
            print("  ", h)

    browser.close()
