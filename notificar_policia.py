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

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS") or os.environ.get("GMAIL_APP_PASSWORD")
EMAIL_DEST = os.environ.get("EMAIL_DEST") or GMAIL_USER
PDF_PATH   = "reporte_policia.pdf"

MESES_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

def enviar(asunto: str, cuerpo_html: str):
    if not GMAIL_USER or not GMAIL_PASS:
        print("Aviso: Faltan las credenciales GMAIL_USER o GMAIL_PASS. Se omite el envío de correo.")
        return

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

    print(f"Email enviado: {asunto}")


def html_base(titulo: str, cuerpo: str) -> str:
    import hashlib
    sha_pdf = "N/A"
    if Path(PDF_PATH).exists():
        try:
            sha256_hash = hashlib.sha256()
            with open(PDF_PATH, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            sha_pdf = sha256_hash.hexdigest()
        except Exception as e:
            print(f"Error calculando SHA256: {e}")

    return f"""
    <html>
    <body style="font-family:'Segoe UI',Arial,sans-serif;color:#1A1A2E;max-width:640px;margin:auto;background-color:#f4f4f8;padding:20px;">
      <div style="background:#281FD0;padding:24px 28px;border-bottom:4px solid #FFE000;border-radius:6px 6px 0 0;box-shadow:0 4px 10px rgba(0,0,0,0.1);">
        <div style="font-size:10px;color:#FFE000;letter-spacing:2px;font-weight:bold;text-transform:uppercase;">Alcaldía de Jamundí · Valle del Cauca</div>
        <h2 style="color:white;margin:6px 0 0;font-size:18px;">🚔 OBSERVATORIO DEL DELITO — POLICÍA NACIONAL</h2>
        <p style="color:rgba(255,255,255,.75);margin:4px 0 0;font-size:12px;">Monitoreo de Estadística Delictiva Oficial</p>
      </div>
      <div style="padding:28px;background:white;border-radius:0 0 6px 6px;box-shadow:0 4px 10px rgba(0,0,0,0.1);">
        <h3 style="color:#281FD0;margin-top:0;font-size:15px;text-transform:uppercase;">{titulo}</h3>
        {cuerpo}
        
        <!-- Caja de Integridad del Reporte -->
        <div style="margin-top:24px;padding:12px 16px;background:#fffde7;border-left:4px solid #FFE000;font-size:11px;color:#555566;border-radius:4px;">
          <b>Integridad del Reporte (Archivo PDF Adjunto):</b><br>
          SHA256 Checksum: <code style="font-size:10px;font-family:monospace;color:#281FD0;">{sha_pdf}</code>
        </div>
        
        <!-- Firma Profesional del Elaborador -->
        <div style="margin-top:30px;border-top:1px solid #e1e2eb;padding-top:15px;">
          <p style="margin:0;font-size:13px;font-weight:bold;color:#281FD0;">Elaborado por:</p>
          <p style="margin:4px 0 0;font-size:12px;color:#444455;line-height:1.4;">
            <b>César Alfonso Forero Molano</b><br>
            Profesional Secretaría de Seguridad y Convivencia<br>
            Alcaldía de Jamundí
          </p>
        </div>
      </div>
      <div style="background:#f8f9fa;padding:14px;text-align:center;font-size:11px;color:#999;border-top:1px solid #eee;border-radius:0 0 6px 6px;margin-top:15px;">
        Fuente: Policía Nacional / DIJIN · Municipio Jamundí (76364) · Generado automáticamente vía GitHub Actions
      </div>
    </body>
    </html>
    """


import json

def obtener_novedades():
    """Compara resumen_actual.json con resumen_anterior.json y genera texto HTML."""
    path_act = Path("resumen_actual.json")
    path_ant = Path("resumen_anterior.json")
    
    if not path_act.exists():
        return "", False
    
    with open(path_act, "r", encoding="utf-8") as f:
        act = json.load(f)
    
    ant = {}
    if path_ant.exists():
        with open(path_ant, "r", encoding="utf-8") as f:
            ant = json.load(f)
    
    novedades = []
    # Usar todas las llaves disponibles (delitos, delitos_2024, delitos_2025)
    for key, total_act in act.items():
        total_ant = ant.get(key, 0)
        diff = total_act - total_ant
        
        if diff == 0:
            continue
            
        # Limpiar etiqueta para el correo (ej: "Homicidios_2024" -> "Homicidios (2024)")
        label = key.replace("_202", " (202")
        if "(" in label: label += ")"
            
        if diff > 0:
            novedades.append(f"<li><b>{label}</b>: <span style='color:#C0392B'>+{int(diff)} nuevos</span> (Total: {int(total_act)})</li>")
        elif diff < 0:
            novedades.append(f"<li><b>{label}</b>: <span style='color:#1A7A4A'>{int(diff)} casos</span> (Total: {int(total_act)})</li>")
            
    if not novedades:
        return "<p style='color:#606175'><i>No hay cambios numéricos significativos en los datos analizados.</i></p>", False
    
    return "<p><b>Novedades detectadas en la base de datos:</b></p><ul>" + "".join(novedades) + "</ul>", True

def main():
    tipo = sys.argv[1].lower().strip() if len(sys.argv) > 1 else "cambio"
    hoy  = datetime.now()
    mes  = MESES_ES[hoy.month]
    
    html_novedades, hay_cambios = obtener_novedades()

    # Si es un monitoreo de rutina (cambio o diario) y no hay cambios, no enviar nada
    if tipo in ["cambio", "diario"] and not hay_cambios:
        print(f"Sin cambios detectados. Se omite el envío de correo ({tipo}).")
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
