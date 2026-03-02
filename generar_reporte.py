"""
generar_reporte.py — Identidad oficial Alcaldía de Jamundí
Colores: Azul #281FD0, Amarillo #FFE000
"""
import os, sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable

AZUL       = colors.HexColor("#281FD0")
AZUL_CLARO = colors.HexColor("#3A30F1")
AMARILLO   = colors.HexColor("#FFE000")
NEGRO      = colors.HexColor("#1A1A2E")
GRIS       = colors.HexColor("#606175")
GRIS_FONDO = colors.HexColor("#F4F4F8")
ROJO_ALT   = colors.HexColor("#C0392B")
VERDE      = colors.HexColor("#1A7A4A")

COD_MUNI = 76364
CARPETA  = "mindefensa_xlsx"
SALIDA   = "reporte_observatorio.pdf"
ESCUDO   = "escudo_jamundi.png"
MESES_ES = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

DATASETS = {
    "Homicidio Intencional":      {"file": "HOMICIDIO INTENCIONAL.xlsx",                               "col": "VICTIMAS"},
    "Lesiones Comunes":           {"file": "LESIONES COMUNES.xlsx",                                    "col": "CANTIDAD"},
    "Violencia Intrafamiliar":    {"file": "VIOLENCIA INTRAFAMILIAR.xlsx",                             "col": "CANTIDAD"},
    "Delitos Sexuales":           {"file": "DELITOS SEXUALES.xlsx",                                    "col": "CANTIDAD"},
    "Secuestro":                  {"file": "SECUESTRO.xlsx",                                           "col": "CANTIDAD"},
    "Extorsion":                  {"file": "EXTORSIÓN.xlsx",                                      "col": "CANTIDAD"},
    "Terrorismo":                 {"file": "TERRORISMO.xlsx",                                          "col": "CANTIDAD"},
    "Masacres":                   {"file": "MASACRES.xlsx",                                            "col": "VICTIMAS"},
    "Afectacion Fuerza Publica":  {"file": "AFECTACIÓN A LA FUERZA PÚBLICA.xlsx",            "col": "CANTIDAD"},
    "Pirateria Terrestre":        {"file": "PIRATERIÁ TERRESTRE.xlsx",                            "col": "CANTIDAD"},
    "Trata de Personas":          {"file": "TRATA DE PERSONAS Y TRÁFICO DE MIGRANTES.xlsx",       "col": "CANTIDAD"},
    "Invasion de Tierras":        {"file": "INVASIÓN DE TIERRAS.xlsx",                            "col": "CANTIDAD"},
    "Hurto a Personas":           {"file": "HURTO PERSONAS.xlsx",                                      "col": "CANTIDAD"},
    "Hurto a Residencias":        {"file": "HURTO A RESIDENCIAS.xlsx",                                 "col": "CANTIDAD"},
    "Hurto de Vehiculos":         {"file": "HURTO DE VEHÍCULOS.xlsx",                             "col": "CANTIDAD"},
    "Hurto a Comercio":           {"file": "HURTO A COMERCIO.xlsx",                                    "col": "CANTIDAD"},
    "Incautacion Cocaina":        {"file": "INCAUTACIÓN DE COCAINA.xlsx",                         "col": "CANTIDAD"},
    "Incautacion Marihuana":      {"file": "INCAUTACIÓN DE MARIHUANA.xlsx",                       "col": "CANTIDAD"},
}

def leer_datos():
    datos = {}
    for nombre, cfg in DATASETS.items():
        ruta = Path(CARPETA) / cfg["file"]
        if not ruta.exists():
            continue
        try:
            df = pd.read_excel(ruta, engine='calamine')
            df = df[df['COD_MUNI'] == COD_MUNI].copy()
            col_fecha = 'FECHA_HECHO' if 'FECHA_HECHO' in df.columns else 'FECHA HECHO'
            df['FECHA_HECHO'] = pd.to_datetime(df[col_fecha], errors='coerce')
            df['ANIO'] = df['FECHA_HECHO'].dt.year
            df['MES']  = df['FECHA_HECHO'].dt.month
            df['col_cantidad'] = df[cfg['col']]
            datos[nombre] = df
            print(f"  [OK] {nombre}: {len(df)} filas")
        except Exception as e:
            print(f"  [ERROR] {nombre}: {e}")
    return datos

def total_anio(df, anio, hasta_mes=None):
    sub = df[df['ANIO'] == anio]
    if hasta_mes:
        sub = sub[sub['MES'] <= hasta_mes]
    return int(sub['col_cantidad'].sum())


def calcular_variacion_estado(v_prev: int, v_act: int):
    # Manejo de base cero (evita 0.0% incorrecto)
    if v_prev == 0 and v_act == 0:
        return "0.0%", "IGUAL"
    if v_prev == 0 and v_act > 0:
        return "N/A (base 0)", "APARECE"
    if v_prev > 0 and v_act == 0:
        return "-100.0%", "BAJA"

    var = ((v_act - v_prev) / v_prev) * 100.0
    if var > 0:
        return f"+{var:.1f}%", "SUBE"
    if var < 0:
        return f"{var:.1f}%", "BAJA"
    return "0.0%", "IGUAL"

def serie_mensual(df, anio):
    sub = df[df['ANIO'] == anio].groupby('MES')['col_cantidad'].sum()
    return [int(sub.get(m, 0)) for m in range(1, 13)]

def grafica_comparativa(datos, anio_actual, anio_anterior, hasta_mes=None):
    delitos  = list(datos.keys())
    vals_ant = [total_anio(datos[d], anio_anterior, hasta_mes=hasta_mes) for d in delitos]
    vals_act = [total_anio(datos[d], anio_actual, hasta_mes=hasta_mes)   for d in delitos]
    fig, ax = plt.subplots(figsize=(13, 5))
    fig.patch.set_facecolor('#F4F4F8')
    ax.set_facecolor('#F4F4F8')
    x = range(len(delitos))
    w = 0.36
    ax.bar([i - w/2 for i in x], vals_ant, w, label=str(anio_anterior), color='#606175', alpha=0.85, zorder=3)
    b2 = ax.bar([i + w/2 for i in x], vals_act, w, label=str(anio_actual), color='#281FD0', alpha=0.92, zorder=3)
    for bar in b2:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, str(int(h)), ha='center', va='bottom', fontsize=8, color='#281FD0', fontweight='bold')
    ax.set_xticks(list(x))
    ax.set_xticklabels([d.replace(' ', '\n') for d in delitos], fontsize=8.5, color='#1A1A2E')
    ax.set_ylabel('Casos', fontsize=9, color='#606175')
    ax.set_title(f'Comparativo ene-{MESES_ES[hasta_mes][:3] if hasta_mes else "Dic"} {anio_anterior} vs {anio_actual}', fontsize=11, fontweight='bold', color='#281FD0', pad=10)
    ax.legend(fontsize=9, framealpha=0.7)
    for spine in ['top','right']:
        ax.spines[spine].set_visible(False)
    ax.yaxis.grid(True, alpha=0.4, color='#C5C5D2', zorder=0)
    ax.set_axisbelow(True)
    ax.axhline(y=0, color='#FFE000', linewidth=2.5, zorder=4)
    plt.tight_layout()
    ruta = '/tmp/graf_comp.png'
    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor='#F4F4F8')
    plt.close()
    return ruta

def grafica_mensual(datos, anio_actual):
    meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    principales = ['Homicidio Intencional','Lesiones Comunes','Violencia Intrafamiliar']
    colores_l   = ['#281FD0','#FFB600','#C0392B']
    markers     = ['o','s','^']
    fig, ax = plt.subplots(figsize=(13, 4))
    fig.patch.set_facecolor('#F4F4F8')
    ax.set_facecolor('#F4F4F8')
    for delito, color, marker in zip(principales, colores_l, markers):
        if delito in datos:
            serie = serie_mensual(datos[delito], anio_actual)
            ax.plot(meses, serie, marker=marker, label=delito, color=color, linewidth=2, markersize=5, zorder=3)
            ax.fill_between(meses, serie, alpha=0.07, color=color)
    ax.set_title(f'Tendencia Mensual {anio_actual} — Delitos Prioritarios', fontsize=11, fontweight='bold', color='#281FD0', pad=10)
    ax.set_ylabel('Casos', fontsize=9, color='#606175')
    ax.legend(fontsize=8.5, loc='upper right', framealpha=0.7)
    for spine in ['top','right']:
        ax.spines[spine].set_visible(False)
    ax.yaxis.grid(True, alpha=0.4, color='#C5C5D2', zorder=0)
    ax.set_axisbelow(True)
    ax.axhline(y=0, color='#FFE000', linewidth=2, zorder=4)
    plt.tight_layout()
    ruta = '/tmp/graf_mens.png'
    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor='#F4F4F8')
    plt.close()
    return ruta

def generar_pdf(datos, ruta_salida):
    hoy           = datetime.now()
    anio_actual   = hoy.year
    anio_anterior = anio_actual - 1
    # Detectar hasta que fecha tiene datos realmente MinDefensa
    import pandas as _pd
    fecha_max = max(df['FECHA_HECHO'].max() for df in datos.values())
    # Si no llego al dia 25 del mes, usar mes anterior (mes incompleto)
    if fecha_max.day < 25:
        mes_actual = fecha_max.month - 1 if fecha_max.month > 1 else 12
    else:
        mes_actual = fecha_max.month
    mes_nombre = MESES_ES[mes_actual]
    print(f"  Datos hasta: {fecha_max.strftime('%d/%m/%Y')} -> comparando hasta {mes_nombre}")
    doc = SimpleDocTemplate(ruta_salida, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.2*cm, bottomMargin=1.5*cm)
    W = A4[0] - 3.6*cm
    estilos = getSampleStyleSheet()

    def E(nombre, **kw):
        return ParagraphStyle(nombre, parent=estilos['Normal'], **kw)

    historia = []

    # ── ENCABEZADO ────────────────────────────────────────────────────────────
    tiene_escudo = Path(ESCUDO).exists()
    bloque_nombre = Table([
        [Paragraph("ALCALDÍA DE JAMUNDÍ", E('i', fontSize=15, fontName='Helvetica-Bold', textColor=NEGRO))],
        [Paragraph("VALLE DEL CAUCA",     E('d', fontSize=9,  fontName='Helvetica', textColor=GRIS))],
        [Spacer(1,3)],
        [Paragraph(f"Observatorio del Delito — Boletín {mes_nombre} {anio_actual}",
                   E('o', fontSize=9, fontName='Helvetica-Bold', textColor=AZUL_CLARO))],
    ], colWidths=[W*0.62])
    bloque_nombre.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0)]))

    bloque_fecha = Table([
        [Paragraph(hoy.strftime('%d/%m/%Y %H:%M'), E('f1', fontSize=8, textColor=GRIS, alignment=TA_RIGHT))],
        [Paragraph("Secretaría de Seguridad y Convivencia", E('f2', fontSize=7.5, textColor=GRIS, alignment=TA_RIGHT))],
        [Paragraph("Fuente: Ministerio de Defensa Nacional", E('f3', fontSize=7.5, textColor=GRIS, alignment=TA_RIGHT))],
    ], colWidths=[W*0.38])

    if tiene_escudo:
        enc_data   = [[Image(ESCUDO, width=1.4*cm, height=1.9*cm), bloque_nombre, bloque_fecha]]
        anchos_enc = [1.7*cm, W*0.60, W*0.40 - 1.7*cm]
    else:
        enc_data   = [[bloque_nombre, bloque_fecha]]
        anchos_enc = [W*0.62, W*0.38]

    tabla_enc = Table(enc_data, colWidths=anchos_enc)
    tabla_enc.setStyle(TableStyle([
        ('VALIGN',     (0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),4),
        ('BACKGROUND', (0,0),(-1,-1),colors.white),
        ('ROWPADDING', (0,0),(-1,-1),8),
    ]))
    historia.append(tabla_enc)

    # Línea azul + toque amarillo
    historia.append(Table([['']], colWidths=[W]).setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),AZUL),('ROWPADDING',(0,0),(-1,-1),2)])) or None)
    # Workaround: crear tablas línea por separado
    # Linea decorativa: azul con bloque amarillo al inicio (segun manual identidad)
    tl = Table([['','']], colWidths=[W*0.18, W*0.82])
    tl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,0),AMARILLO),
        ('BACKGROUND',(1,0),(1,0),AZUL),
        ('ROWPADDING',(0,0),(-1,-1),3),
    ]))
    historia.append(tl)
    historia.append(Spacer(1, 0.4*cm))

    # ── RESUMEN EJECUTIVO ─────────────────────────────────────────────────────
    historia.append(Paragraph("RESUMEN EJECUTIVO", E('h2', fontSize=11, fontName='Helvetica-Bold', textColor=AZUL, spaceBefore=4, spaceAfter=4)))
    historia.append(HRFlowable(width=W, thickness=2, color=AMARILLO))
    historia.append(Spacer(1, 0.2*cm))

    def TH(t): return Paragraph(f"<b>{t}</b>", E('th', fontSize=8, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))
    def TD(t, bold=False, clr=NEGRO, align=TA_LEFT):
        return Paragraph(f"<b>{t}</b>" if bold else str(t), E('td', fontSize=8.5, textColor=clr, alignment=align))

    filas = [[TH("Delito"), TH(str(anio_anterior)), TH(str(anio_actual)), TH("Variación"), TH("Estado")]]
    for nombre, df in datos.items():
        ant   = total_anio(df, anio_anterior, hasta_mes=mes_actual)
        act   = total_anio(df, anio_actual, hasta_mes=mes_actual)
        delta = act - ant
        pct   = (delta / ant * 100) if ant > 0 else 0
        signo = "+" if pct > 0 else ""
        var_txt, flecha = calcular_variacion_estado(ant, act)
        clr_v  = ROJO_ALT if delta > 0 else (VERDE if delta < 0 else GRIS)
        filas.append([
            TD(nombre),
            TD(str(ant), align=TA_CENTER),
            TD(str(act), bold=True, align=TA_CENTER),
            TD(f"{signo}{pct:.1f}%", clr=clr_v, align=TA_CENTER, bold=True),
            TD(flecha, clr=clr_v, align=TA_CENTER, bold=True),
        ])

    tabla_res = Table(filas, colWidths=[W*0.38, W*0.13, W*0.13, W*0.20, W*0.16], repeatRows=1)
    tabla_res.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0), AZUL),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, GRIS_FONDO]),
        ('GRID',          (0,0),(-1,-1), 0.4, colors.HexColor('#C5C5D2')),
        ('ROWPADDING',    (0,0),(-1,-1), 7),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('LINEBELOW',     (0,0),(-1,0), 2.5, AMARILLO),
    ]))
    historia.append(tabla_res)
    historia.append(Spacer(1, 0.5*cm))

    # ── GRÁFICAS ──────────────────────────────────────────────────────────────
    historia.append(Paragraph("COMPARATIVO ANUAL POR DELITO", E('h3', fontSize=11, fontName='Helvetica-Bold', textColor=AZUL, spaceAfter=4)))
    historia.append(HRFlowable(width=W, thickness=2, color=AMARILLO))
    historia.append(Spacer(1, 0.15*cm))
    try:
        historia.append(Image(grafica_comparativa(datos, anio_actual, anio_anterior, hasta_mes=mes_actual), width=W, height=W*0.38))
    except Exception as e:
        historia.append(Paragraph(f"Grafica no disponible: {e}", E('err', fontSize=8)))

    historia.append(Spacer(1, 0.4*cm))
    historia.append(Paragraph("TENDENCIA MENSUAL — DELITOS PRIORITARIOS", E('h4', fontSize=11, fontName='Helvetica-Bold', textColor=AZUL, spaceAfter=4)))
    historia.append(HRFlowable(width=W, thickness=2, color=AMARILLO))
    historia.append(Spacer(1, 0.15*cm))
    try:
        historia.append(Image(grafica_mensual(datos, anio_actual), width=W, height=W*0.30))
    except Exception as e:
        historia.append(Paragraph(f"Grafica no disponible: {e}", E('err2', fontSize=8)))

    # ── PIE ───────────────────────────────────────────────────────────────────
    historia.append(Spacer(1, 0.4*cm))
    tabla_pie = Table([
        [Paragraph("ALCALDÍA DE JAMUNDÍ — SECRETARÍA DE SEGURIDAD Y CONVIVENCIA",
                   E('p1', fontSize=7.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))],
        [Paragraph(f"Fuente: MinDefensa · Código municipio: {COD_MUNI} · www.jamundi.gov.co · Generado automáticamente vía GitHub Actions",
                   E('p2', fontSize=7, textColor=colors.white, alignment=TA_CENTER))],
    ], colWidths=[W])
    tabla_pie.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), AZUL),
        ('ROWPADDING', (0,0),(-1,-1), 7),
        ('LINEABOVE',  (0,0),(-1,0), 3, AMARILLO),
    ]))
    historia.append(tabla_pie)

    doc.build(historia)
    print(f"\n REPORTE GENERADO: {ruta_salida}")

if __name__ == '__main__':
    print("=" * 60)
    print("OBSERVATORIO DEL DELITO — ALCALDIA DE JAMUNDI")
    print("=" * 60)
    datos = leer_datos()
    if not datos:
        print("No se encontraron datos.")
        sys.exit(1)
    salida = sys.argv[1] if len(sys.argv) > 1 else SALIDA
    generar_pdf(datos, salida)
