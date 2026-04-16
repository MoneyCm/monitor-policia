"""
notificar_policia.py — Envío de email con reporte PDF Policía Nacional
Uso: python notificar_policia.py [cambio|planificacion|consejo]
"""

import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_PASS"]
EMAIL_DEST = os.environ["EMAIL_DEST"]
PDF_PATH   = "reporte_policia.pdf"

MESES_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

def enviar(asunto: str, cuerpo_html: str):
    msg = MIMEMultipart("mixed")
    msg["From"]    = GMAIL_USER
    msg["To"]      = EMAIL_DEST
    msg["Subject"] = asunto

    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    if Path(PDF_PATH).exists():
        with open(PDF_PATH, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f'attachment; filename="reporte_policia.pdf"')
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, EMAIL_DEST, msg.as_string())

    print(f"✅ Email enviado: {asunto}")


def html_base(titulo: str, cuerpo: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#1A1A2E;max-width:640px;margin:auto">
      <div style="background:#281FD0;padding:18px 24px;border-bottom:4px solid #FFE000">
        <h2 style="color:white;margin:0;font-size:16px">🚔 OBSERVATORIO DEL DELITO — POLICÍA NACIONAL</h2>
        <p style="color:#c0c8ff;margin:4px 0 0;font-size:12px">Alcaldía de Jamundí · Secretaría de Seguridad y Convivencia</p>
      </div>
      <div style="padding:20px 24px;background:#f9f9fd">
        <h3 style="color:#281FD0">{titulo}</h3>
        {cuerpo}
      </div>
      <div style="background:#281FD0;padding:10px 24px;border-top:3px solid #FFE000">
        <p style="color:#c0c8ff;font-size:11px;margin:0">
          Fuente: Policía Nacional / DIJIN · Municipio Jamundí (76364) ·
          Generado automáticamente vía GitHub Actions
        </p>
      </div>
    </body></html>
    """


import json

def obtener_novedades():
    """Compara resumen_actual.json con resumen_anterior.json y genera texto HTML."""
    path_act = Path("resumen_actual.json")
    path_ant = Path("resumen_anterior.json")
    
    if not path_act.exists():
        return ""
    
    with open(path_act, "r", encoding="utf-8") as f:
        act = json.load(f)
    
    ant = {}
    if path_ant.exists():
        with open(path_ant, "r", encoding="utf-8") as f:
            ant = json.load(f)
    
    novedades = []
    for delito, total_act in act.items():
        total_ant = ant.get(delito, 0)
        diff = total_act - total_ant
        if diff > 0:
            novedades.append(f"<li><b>{delito}</b>: <span style='color:#C0392B'>+{int(diff)} nuevos</span> (Total: {int(total_act)})</li>")
        elif diff < 0:
            novedades.append(f"<li><b>{delito}</b>: <span style='color:#1A7A4A'>{int(diff)} casos</span> (Total: {int(total_act)})</li>")
            
    if not novedades:
        return "<p style='color:#606175'><i>No hay cambios numéricos en los totales de los delitos analizados.</i></p>", False
    
    return "<p><b>Resumen de novedades detectadas:</b></p><ul>" + "".join(novedades) + "</ul>", True

def main():
    tipo = sys.argv[1].lower().strip() if len(sys.argv) > 1 else "cambio"
    hoy  = datetime.now()
    mes  = MESES_ES[hoy.month]
    
    html_novedades, hay_cambios = obtener_novedades()

    # Si es un monitoreo de rutina (cambio o diario) y no hay cambios, no enviar nada
    if tipo in ["cambio", "diario"] and not hay_cambios:
        print(f"⏩ Sin cambios detectados. Se omite el envío de correo ({tipo}).")
        return

    if tipo == "cambio" or tipo == "diario":
        asunto = f"🚨 Cambio detectado — Datos Policía Nacional · {hoy.strftime('%d/%m/%Y %H:%M')}"
        cuerpo = f"""
        <p>Se detectaron <b>nuevos datos o actualizaciones</b> en la estadística delictiva de la Policía Nacional para Jamundí.</p>
        {html_novedades}
        <p>El reporte detallado se adjunta a este correo en formato PDF.</p>
        """

    elif tipo == "planificacion":
        asunto = f"📋 Reporte Policía — Reunión de Planificación · {mes} {hoy.year}"
        cuerpo = f"""
        <p>Adjunto el <strong>Boletín de Estadística Delictiva (Policía Nacional)</strong>
        correspondiente a <strong>{mes} {hoy.year}</strong>,
        preparado para la reunión de planificación del lunes.</p>
        <p>Este reporte incluye comparativo anual y tendencia de los principales delitos
        registrados por la Policía Nacional en el municipio de Jamundí.</p>
        """

    elif tipo == "consejo":
        asunto = f"🛡️ Reporte Policía — Consejo de Seguridad · {mes} {hoy.year}"
        cuerpo = f"""
        <p>Adjunto el <strong>Boletín de Estadística Delictiva (Policía Nacional)</strong>
        correspondiente a <strong>{mes} {hoy.year}</strong>,
        preparado para el Consejo de Seguridad del viernes.</p>
        <p>Este reporte complementa los datos del Ministerio de Defensa con la
        perspectiva operativa de la Policía Nacional en Jamundí.</p>
        """

    else:
        asunto = f"📊 Reporte Policía Nacional — {mes} {hoy.year}"
        cuerpo = "<p>Adjunto el reporte de estadística delictiva (Policía Nacional).</p>"

    enviar(asunto, html_base(asunto, cuerpo))


if __name__ == "__main__":
    main()
