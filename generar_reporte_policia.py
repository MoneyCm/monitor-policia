"""
generar_reporte_policia.py — Observatorio del Delito (Jamundí)
PDF con identidad institucional (Azul #281FD0, Amarillo #FFE000) + escudo.
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

# ── Utilidades de Lectura ───────────────────────────────────────────────────
def _read_excel_smart(path: Path, engine: str) -> pd.DataFrame:
    """Busca la fila de cabecera real en el Excel de la Policía."""
    for i in range(0, 20):
        try:
            df = pd.read_excel(path, engine=engine, skiprows=i)
            cols = [str(c).upper() for c in df.columns]
            if any(cand in cols for cand in ("MUNICIPIO", "CANTIDAD", "FECHA")):
                return df
        except: continue
    return pd.read_excel(path, engine=engine) # Fallback

def _safe_read_excel(path: Path) -> pd.DataFrame:
    try:
        return _read_excel_smart(path, engine="calamine")
    except:
        return _read_excel_smart(path, engine="openpyxl")

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
    for nombre, archivos in datasets_dinamicos.items():
        frames = []
        for archivo in archivos:
            try:
                df = _safe_read_excel(base / archivo)
                # Filtrar Jamundí
                col_muni = next((c for c in df.columns if "MUNICIPIO" in c.upper()), None)
                if col_muni:
                    df = df[df[col_muni].astype(str).str.strip().str.lower() == MUNICIPIO_FILTRO.lower()].copy()
                # Parsear Fecha
                col_fecha = next((c for c in df.columns if "FECHA" in c.upper()), None)
                if col_fecha:
                    df["FECHA_HECHO"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors="coerce")
                    df = df.dropna(subset=["FECHA_HECHO"])
                    df["ANIO"] = df["FECHA_HECHO"].dt.year
                    df["MES"]  = df["FECHA_HECHO"].dt.month
                # Cantidad
                col_cant = next((c for c in df.columns if "CANTIDAD" in c.upper()), None)
                df["col_cantidad"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0) if col_cant else 0
                frames.append(df)
                print(f"  [OK] {nombre} / {archivo}: {len(df)} filas")
            except Exception as e:
                print(f"  [ERROR] {nombre} / {archivo}: {e}")
        if frames: datos[nombre] = pd.concat(frames, ignore_index=True)
    return datos

# ── Cálculos ────────────────────────────────────────────────────────────────
def total_anio(df, anio, hasta_mes=None):
    sub = df[df["ANIO"] == anio]
    if hasta_mes: sub = sub[sub["MES"] <= hasta_mes]
    return float(sub["col_cantidad"].sum())

def calcular_variacion_estado(v_prev, v_act):
    if v_prev == 0: return ("N/A (base 0)", "APARECE") if v_act > 0 else ("0.0%", "IGUAL")
    var = ((v_act - v_prev) / v_prev) * 100.0
    txt = f"{var:+.1f}%"
    est = "SUBE" if var > 0 else ("BAJA" if var < 0 else "IGUAL")
    return txt, est

# ── Gráficas ────────────────────────────────────────────────────────────────
def grafica_comparativa(datos, anio_act, anio_ant, hasta_mes):
    delitos = sorted(datos.keys(), key=lambda d: total_anio(datos[d], anio_act, hasta_mes), reverse=True)[:12]
    v_ant = [total_anio(datos[d], anio_ant, hasta_mes) for d in delitos]
    v_act = [total_anio(datos[d], anio_act, hasta_mes) for d in delitos]
    
    fig, ax = plt.subplots(figsize=(13, 5), dpi=120)
    x = range(len(delitos))
    w = 0.35
    ax.bar([i - w/2 for i in x], v_ant, width=w, color="#FFD700", label=f"{anio_ant}", zorder=3)
    ax.bar([i + w/2 for i in x], v_act, width=w, color="#1E90FF", label=f"{anio_act}", zorder=3)
    
    y_max = max(max(v_act), max(v_ant), 1)
    for i, (va, vb) in enumerate(zip(v_ant, v_act)):
        ax.text(i + w/2, vb + y_max*0.02, str(int(vb)), ha="center", fontweight="bold", color="#003366")
        if vb > va: ax.text(i + w/2, vb + y_max*0.08, "▲", ha="center", color="red")
        elif vb < va: ax.text(i + w/2, vb + y_max*0.08, "▼", ha="center", color="green")

    ax.set_xticks(list(x))
    ax.set_xticklabels([d[:20] for d in delitos], rotation=30, ha="right")
    ax.set_title(f"COMPARATIVO INTERANUAL CORTE A {MESES_ES[hasta_mes].upper()} (JAMUNDÍ)", fontweight="bold", pad=15)
    ax.legend()
    plt.tight_layout()
    out = "comparativo_policia.png"
    plt.savefig(out)
    plt.close()
    return out

def grafica_tendencia(datos, fecha_max):
    plt.figure(figsize=(10, 3.5), dpi=120)
    delitos_top = sorted(datos.keys(), key=lambda d: len(datos[d]), reverse=True)[:5]
    for d in delitos_top:
        df = datos[d]
        s = df.groupby(["ANIO", "MES"])["col_cantidad"].sum().tail(24)
        plt.plot(range(len(s)), s.values, marker="o", label=d)
    plt.title("TENDENCIA ÚLTIMOS MESES (TOP 5 DELITOS)")
    plt.legend(fontsize=7)
    out = "tendencia_policia.png"
    plt.savefig(out)
    plt.close()
    return out

# ── PDF ──────────────────────────────────────────────────────────────────────
def generar_pdf(datos, salida):
    fecha_max = pd.Timestamp(max(df["FECHA_HECHO"].max() for df in datos.values()))
    mes_corte = fecha_max.month if fecha_max.day > 25 else (fecha_max.month - 1 or 12)
    anio_act = fecha_max.year
    anio_ant = anio_act - 1

    doc = SimpleDocTemplate(salida, pagesize=A4, margin=(1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm))
    W = A4[0] - 3*cm
    h = []
    
    def P(txt, sz=9, b=False, c=NEGRO, a=TA_LEFT):
        return Paragraph(txt, ParagraphStyle("n", fontSize=sz, fontName="Helvetica-Bold" if b else "Helvetica", textColor=c, alignment=a))

    # Encabezado
    h.append(P("ALCALDÍA DE JAMUNDÍ — OBSERVATORIO DEL DELITO", 14, True, AZUL))
    h.append(P(f"Boletín Estadístico Policía Nacional - Corte: {MESES_ES[mes_corte]} {anio_act}", 10, True, GRIS))
    h.append(Spacer(1, 0.5*cm))

    # Tabla Resumen
    filas = [[P("Delito",8,True,colors.white), P(str(anio_ant),8,True,colors.white), P(str(anio_act),8,True,colors.white), P("Var %",8,True,colors.white), P("Estado",8,True,colors.white)]]
    for d, df in datos.items():
        ant, act = total_anio(df, anio_ant, mes_corte), total_anio(df, anio_act, mes_corte)
        v, e = calcular_variacion_estado(ant, act)
        clr = ROJO_ALT if e in ("SUBE", "APARECE") else (VERDE if e == "BAJA" else GRIS)
        filas.append([P(d,8), P(str(int(ant)),8), P(str(int(act)),8,True), P(v,8,True,clr), P(e,8,True,clr)])

    t = Table(filas, colWidths=[W*0.4, W*0.15, W*0.15, W*0.15, W*0.15])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),AZUL), ("GRID",(0,0),(-1,-1),0.5,colors.grey), ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    h.append(t)
    h.append(Spacer(1, 0.8*cm))

    # Gráficas
    h.append(P("COMPARATIVO POR DELITO", 11, True, AZUL))
    h.append(Image(grafica_comparativa(datos, anio_act, anio_ant, mes_corte), width=W, height=W*0.4))
    h.append(Spacer(1, 0.8*cm))
    h.append(P("TENDENCIA HISTÓRICA (TOP 5)", 11, True, AZUL))
    h.append(Image(grafica_tendencia(datos, fecha_max), width=W, height=W*0.35))

    doc.build(h)
    print(f"✅ Reporte generado: {salida}")

if __name__ == "__main__":
    d = leer_datos()
    if d: generar_pdf(d, SALIDA)
    else: print("No hay datos para procesar.")
