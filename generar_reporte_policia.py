"""
generar_reporte_policia.py — Identidad oficial Alcaldía de Jamundí (Sincronizado con Mindefensa)
Colores: Azul #281FD0, Amarillo #FFE000
"""

import os
import re
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable

# ── Identidad ────────────────────────────────────────────────────────────────
AZUL       = colors.HexColor("#281FD0")
AMARILLO   = colors.HexColor("#FFE000")
NEGRO      = colors.HexColor("#1A1A2E")
GRIS       = colors.HexColor("#606175")
GRIS_FONDO = colors.HexColor("#F4F4F8")
ROJO_ALT   = colors.HexColor("#C0392B")
VERDE      = colors.HexColor("#1A7A4A")

MESES_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

MUNICIPIO_FILTRO = "Jamundí"
CARPETA  = "policia_xlsx"
SALIDA   = "reporte_policia.pdf"
ESCUDO   = "escudo_jamundi.png"

# ── Cache de Header ──
HEADER_POS_CACHE = {}

def _read_excel_smart(path: Path, engine: str) -> pd.DataFrame:
    """Busca la fila de cabecera real en el Excel de la Policía de forma rápida."""
    # Intentar con la última posición conocida para este tipo de archivo
    tipo = path.stem[:8] # Prefijo del nombre del archivo
    skip = HEADER_POS_CACHE.get(tipo, 0)
    
    try:
        df = pd.read_excel(path, engine=engine, skiprows=skip)
        cols = [str(c).upper() for c in df.columns]
        if any(cand in cols for cand in ("MUNICIPIO", "CANTIDAD", "FECHA")):
            return df
    except: pass

    # Si falla, buscar en las primeras 15 filas
    for i in range(0, 15):
        try:
            df = pd.read_excel(path, engine=engine, skiprows=i)
            cols = [str(c).upper() for c in df.columns]
            if any(cand in cols for cand in ("MUNICIPIO", "CANTIDAD", "FECHA")):
                HEADER_POS_CACHE[tipo] = i
                return df
        except: continue
    return pd.read_excel(path, engine=engine)

def _safe_read_excel(path: Path) -> pd.DataFrame:
    try: return _read_excel_smart(path, engine="calamine")
    except: return _read_excel_smart(path, engine="openpyxl")

def descubrir_datasets():
    base = Path(CARPETA)
    if not base.exists(): return {}
    archivos = list(base.glob("*.xlsx"))
    datasets = {}
    for arc in archivos:
        nombre_limpio = re.sub(r"202\d(_\d)?", "", arc.stem).strip()
        if nombre_limpio not in datasets: datasets[nombre_limpio] = []
        datasets[nombre_limpio].append(arc.name)
    return datasets

def leer_datos() -> dict:
    datos = {}
    base = Path(CARPETA)
    datasets_dinamicos = descubrir_datasets()
    print(f"📊 Procesando {len(datasets_dinamicos)} tipos de delitos...")
    for nombre, archivos in datasets_dinamicos.items():
        frames = []
        for archivo in archivos:
            try:
                print(f"  → Cargando {archivo}...", end="\r")
                df = _safe_read_excel(base / archivo)
                col_muni = next((c for c in df.columns if "MUNICIPIO" in c.upper()), None)
                if col_muni:
                    df = df[df[col_muni].astype(str).str.strip().str.lower() == MUNICIPIO_FILTRO.lower()].copy()
                col_fecha = next((c for c in df.columns if "FECHA" in c.upper()), None)
                if col_fecha:
                    df["FECHA_HECHO"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors="coerce")
                    df = df.dropna(subset=["FECHA_HECHO"])
                    df["ANIO"] = df["FECHA_HECHO"].dt.year
                    df["MES"]  = df["FECHA_HECHO"].dt.month
                col_cant = next((c for c in df.columns if "CANTIDAD" in c.upper()), None)
                df["col_cantidad"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0) if col_cant else 0
                frames.append(df)
            except: pass
        if frames: 
            datos[nombre] = pd.concat(frames, ignore_index=True)
            print(f"  [OK] {nombre}: {len(datos[nombre])} registros filtrados")
    return datos

# ── Cálculos ──
def total_anio(df, anio, hasta_mes=None):
    if df is None: return 0
    sub = df[df["ANIO"] == anio]
    if hasta_mes: sub = sub[sub["MES"] <= hasta_mes]
    return float(sub["col_cantidad"].sum())

def fmt_val(v):
    try: return f"{int(round(float(v))):,}".replace(",", ".")
    except: return str(v)

def calcular_variacion_estado(v_prev, v_act):
    if v_prev == 0: return ("N/A", "APARECE") if v_act > 0 else ("0.0%", "IGUAL")
    var = ((v_act - v_prev) / v_prev) * 100.0
    txt = f"{var:+.1f}%"
    est = "SUBE" if var > 0 else ("BAJA" if var < 0 else "IGUAL")
    return txt, est

# ── Gráficas ──
def grafica_comparativa(datos, anio_act, anio_ant, hasta_mes):
    delitos = sorted(datos.keys(), key=lambda d: total_anio(datos[d], anio_act, hasta_mes), reverse=True)[:12]
    v_ant = [total_anio(datos[d], anio_ant, hasta_mes) for d in delitos]
    v_act = [total_anio(datos[d], anio_act, hasta_mes) for d in delitos]
    
    fig, ax = plt.subplots(figsize=(13, 5), dpi=140)
    fig.patch.set_facecolor('#F4F4F8')
    ax.set_facecolor('#F4F4F8')
    
    x = range(len(delitos))
    w = 0.36
    ax.bar([i - w/2 for i in x], v_ant, w, label=str(anio_ant), color='#606175', alpha=0.85, zorder=3)
    bars_act = ax.bar([i + w/2 for i in x], v_act, w, label=str(anio_act), color='#281FD0', alpha=0.92, zorder=3)
    
    y_max = max(max(v_act) if v_act else 0, max(v_ant) if v_ant else 0, 1)
    for i, (bar, va, vb) in enumerate(zip(bars_act, v_ant, v_act)):
        if vb > 0:
            ax.text(bar.get_x() + bar.get_width()/2, vb + y_max*0.02, fmt_val(vb), 
                    ha='center', va='bottom', fontsize=8, color='#281FD0', fontweight='bold')
        if vb > va: ax.text(bar.get_x() + bar.get_width()/2, vb + y_max*0.08, "▲", ha='center', color="#C0392B", fontsize=8)
        elif vb < va: ax.text(bar.get_x() + bar.get_width()/2, vb + y_max*0.08, "▼", ha='center', color="#1A7A4A", fontsize=8)

    ax.set_xticks(list(x))
    ax.set_xticklabels([d[:20] for d in delitos], rotation=30, ha="right", fontsize=8.5)
    ax.set_title(f"COMPARATIVO ENE-{MESES_ES[hasta_mes][:3].upper()} {anio_ant} vs {anio_act}", fontsize=11, fontweight='bold', color='#281FD0', pad=15)
    ax.legend(fontsize=9)
    ax.yaxis.grid(True, alpha=0.4, color='#C5C5D2', zorder=0)
    for spine in ['top','right']: ax.spines[spine].set_visible(False)
    
    plt.tight_layout()
    out = "graf_comp_policia.png"
    plt.savefig(out, facecolor='#F4F4F8')
    plt.close()
    return out

def grafica_tendencia(datos, fecha_max):
    plt.figure(figsize=(10, 3.3), dpi=140)
    plt.gca().set_facecolor('#F4F4F8')
    delitos_top = sorted(datos.keys(), key=lambda d: total_anio(datos[d], fecha_max.year), reverse=True)[:5]
    for d in delitos_top:
        df = datos[d]
        s = df.groupby(["ANIO", "MES"])["col_cantidad"].sum().tail(24)
        plt.plot(range(len(s)), s.values, marker="o", label=d, linewidth=2)
    plt.title("TENDENCIA HISTÓRICA — TOP 5 DELITOS (JAMUNDÍ)", fontweight="bold", color="#281FD0")
    plt.legend(fontsize=7, loc="upper right")
    plt.grid(True, alpha=0.2)
    out = "graf_tend_policia.png"
    plt.tight_layout()
    plt.savefig(out, facecolor='#F4F4F8')
    plt.close()
    return out

# ── PDF ──
def generar_pdf(datos, salida):
    todas_fechas = [df["FECHA_HECHO"].max() for df in datos.values() if not df.empty]
    if not todas_fechas: return
    fecha_max = pd.Timestamp(max(todas_fechas))
    mes_actual = fecha_max.month if fecha_max.day > 25 else (fecha_max.month - 1 or 12)
    anio_act, anio_ant = fecha_max.year, fecha_max.year - 1

    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.2*cm, bottomMargin=1.5*cm)
    W = A4[0] - 3.6*cm
    h = []
    
    def P(txt, sz=9, b=False, c=NEGRO, a=TA_LEFT):
        return Paragraph(txt, ParagraphStyle("n", fontSize=sz, fontName="Helvetica-Bold" if b else "Helvetica", textColor=c, alignment=a))

    # Encabezado (Idéntico a Mindefensa)
    bloque_izq = Table([
        [P("ALCALDÍA DE JAMUNDÍ", 15, True)],
        [P("VALLE DEL CAUCA", 9, False, GRIS)],
        [Spacer(1,3)],
        [P(f"Observatorio del Delito — Boletín Policía {MESES_ES[mes_actual]} {anio_act}", 9, True, AZUL)],
    ], colWidths=[W*0.62])
    
    bloque_der = Table([
        [P(datetime.now().strftime("%d/%m/%Y %H:%M"), 8, False, GRIS, TA_RIGHT)],
        [P("Secretaría de Seguridad y Convivencia", 7.5, False, GRIS, TA_RIGHT)],
        [P("Fuente: Policía Nacional / DIJIN", 7.5, False, GRIS, TA_RIGHT)],
    ], colWidths=[W*0.38])

    enc = Table([[Image(ESCUDO, 1.4*cm, 1.9*cm) if Path(ESCUDO).exists() else "", bloque_izq, bloque_der]], colWidths=[1.7*cm, W*0.58, W*0.35])
    enc.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('LEFTPADDING',(0,0),(-1,-1),0)]))
    h.append(enc)

    tl = Table([['','']], colWidths=[W*0.18, W*0.82])
    tl.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),AMARILLO), ('BACKGROUND',(1,0),(1,0),AZUL), ('ROWPADDING',(0,0),(-1,-1),3)]))
    h.append(tl)
    h.append(Spacer(1, 0.4*cm))

    # Resumen Ejecutivo
    h.append(P("RESUMEN EJECUTIVO", 11, True, AZUL))
    h.append(HRFlowable(width=W, thickness=2, color=AMARILLO))
    h.append(Spacer(1, 0.2*cm))

    filas = [[P("Delito",8,True,colors.white,TA_CENTER), P(str(anio_ant),8,True,colors.white,TA_CENTER), P(str(anio_act),8,True,colors.white,TA_CENTER), P("Variación",8,True,colors.white,TA_CENTER), P("Estado",8,True,colors.white,TA_CENTER)]]
    for d, df in sorted(datos.items(), key=lambda x: total_anio(x[1], anio_act, mes_actual), reverse=True):
        ant, act = total_anio(df, anio_ant, mes_actual), total_anio(df, anio_act, mes_actual)
        v, e = calcular_variacion_estado(ant, act)
        clr = ROJO_ALT if e in ("SUBE", "APARECE") else (VERDE if e == "BAJA" else GRIS)
        filas.append([P(d,8), P(fmt_val(ant),8,False,NEGRO,TA_CENTER), P(fmt_val(act),8,True,NEGRO,TA_CENTER), P(v,8,True,clr,TA_CENTER), P(e,8,True,clr,TA_CENTER)])

    t = Table(filas, colWidths=[W*0.38, W*0.13, W*0.13, W*0.20, W*0.16])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),AZUL), ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, GRIS_FONDO]), ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#C5C5D2')), ('ROWPADDING',(0,0),(-1,-1),7), ('LINEBELOW',(0,0),(-1,0),2.5,AMARILLO)]))
    h.append(t)
    h.append(Spacer(1, 0.6*cm))

    # Gráficas
    h.append(P("COMPARATIVO ANUAL POR DELITO", 11, True, AZUL))
    h.append(HRFlowable(width=W, thickness=2, color=AMARILLO))
    h.append(Spacer(1, 0.15*cm))
    h.append(Image(grafica_comparativa(datos, anio_act, anio_ant, mes_actual), width=W, height=W*0.38))
    h.append(Spacer(1, 0.6*cm))
    h.append(P("TENDENCIA HISTÓRICA — TOP 5 DELITOS PRIORITARIOS", 11, True, AZUL))
    h.append(HRFlowable(width=W, thickness=2, color=AMARILLO))
    h.append(Spacer(1, 0.15*cm))
    h.append(Image(grafica_tendencia(datos, fecha_max), width=W, height=W*0.35))

    # Pie
    h.append(Spacer(1, 0.6*cm))
    pie = Table([[P("ALCALDÍA DE JAMUNDÍ — SECRETARÍA DE SEGURIDAD Y CONVIVENCIA", 7.5, True, colors.white, TA_CENTER)], [P("Fuente: Policía Nacional / DIJIN · Municipio: Jamundí (76364) · Generado automáticamente vía GitHub Actions", 7, False, colors.white, TA_CENTER)]], colWidths=[W])
    pie.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),AZUL), ('ROWPADDING',(0,0),(-1,-1),7), ('LINEABOVE',(0,0),(-1,0),3,AMARILLO)]))
    h.append(pie)

    doc.build(h)
    print(f"✅ Reporte generado: {salida}")
    
    # Exportar totales para comparación en el correo
    import json
    resumen = {}
    for d, df in datos.items():
        resumen[d] = int(total_anio(df, anio_act, mes_actual))
    
    with open("resumen_actual.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print("📊 Totales exportados a resumen_actual.json")

if __name__ == "__main__":
    d = leer_datos()
    if d: generar_pdf(d, SALIDA)
