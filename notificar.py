"""
notificar.py — Envío de correo con novedades de Mindefensa
"""
import smtplib, os, sys, json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path

# Configuración
CORREO  = os.environ.get("GMAIL_USER")
PASSWD  = os.environ.get("GMAIL_PASS")
DESTINO = os.environ.get("EMAIL_DEST") or CORREO
STATE_FILE  = Path("mindefensa_state.json")
REPORTE_PDF = Path("reporte_observatorio.pdf")
RESUMEN_ACT = Path("resumen_actual_mindefensa.json")
RESUMEN_ANT = Path("resumen_anterior_mindefensa.json")

MESES_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

def tipo_envio():
    t = sys.argv[1] if len(sys.argv) > 1 else "cambio"
    return t.lower().strip()

def asunto_y_titulo(tipo, fecha_hoy):
    if tipo == "reunion":
        return f"📋 Reunión Planeación — Mindefensa · {fecha_hoy}", "Boletín Preparatorio — Planeación", "Preparado para la reunión de los miércoles."
    if tipo == "consejo":
        return f"🛡️ Consejo de Seguridad — Mindefensa · {fecha_hoy}", "Boletín Consejo de Seguridad", "Consolidado estratégico para el Consejo de Seguridad."
    return f"🚨 Cambio Detectado — Mindefensa · {fecha_hoy}", "Actualización de Datos Detectada", "Se han identificado nuevos archivos o cambios en el portal de Mindefensa."

def obtener_novedades_html():
    if not RESUMEN_ACT.exists(): return ""
    with open(RESUMEN_ACT, "r", encoding="utf-8") as f: act = json.load(f)
    ant = {}
    if RESUMEN_ANT.exists():
        with open(RESUMEN_ANT, "r", encoding="utf-8") as f: ant = json.load(f)
    
    items = []
    for d, v_act in act.items():
        v_ant = ant.get(d, 0)
        diff = v_act - v_ant
        if diff > 0:
            items.append(f"<li style='margin-bottom:4px'><b>{d}</b>: <span style='color:#C0392B'>+{int(diff)}</span> (Total: {int(v_act)})</li>")
        elif diff < 0:
            items.append(f"<li style='margin-bottom:4px'><b>{d}</b>: <span style='color:#2E7D32'>{int(diff)}</span> (Total: {int(v_act)})</li>")
            
    if not items: return "<p style='font-size:12px;color:#606175'><i>Sin cambios en los totales de delitos prioritarios.</i></p>", False
    return "<div style='background:#f9f9fb;border-left:4px solid #281FD0;padding:12px;margin:15px 0'><b style='font-size:13px;color:#281FD0'>Resumen de Novedades:</b><ul style='font-size:12px;color:#1A1A2E;margin:8px 0 0;padding-left:18px'>" + "".join(items) + "</ul></div>", True

def enviar_resumen():
    if not CORREO or not PASSWD:
        print("Faltan credenciales GMAIL_USER / GMAIL_PASS")
        return

    estado = {}
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f: estado = json.load(f)

    ultima    = estado.get("ultima_revision", "—")
    total     = len(estado.get("archivos", {}))
    nuevos    = estado.get("nuevos_ultimo", 0)
    cambios   = estado.get("cambios_ultimo", 0)
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    tipo = tipo_envio()
    asunto, titulo, descripcion = asunto_y_titulo(tipo, fecha_hoy)
    color_badge = {"reunion": "#FFB600", "consejo": "#C0392B", "cambio": "#281FD0"}.get(tipo, "#281FD0")
    label_badge = {"reunion": "REUNIÓN PLANEACIÓN", "consejo": "CONSEJO SEGURIDAD", "cambio": "ACTUALIZACIÓN"}.get(tipo, "MONITOREO")

    novedades_html, hay_novedades = obtener_novedades_html()

    # Si es 'cambio' (monitoreo de rutina) y no hay cambios en portal ni en datos, abortar
    if tipo == "cambio":
        if nuevos == 0 and cambios == 0 and not hay_novedades:
            print("⏩ Sin cambios detectados. Se omite el envío de correo.")
            return

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f8;padding:20px;margin:0">
    <div style="max-width:620px;margin:0 auto;background:white;border-radius:6px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)">
      <div style="background:#281FD0;padding:24px 28px 16px">
        <div style="font-size:11px;color:#FFE000;letter-spacing:3px;font-weight:bold;text-transform:uppercase">Alcaldía de Jamundí · Valle del Cauca</div>
        <div style="font-size:20px;font-weight:bold;color:white;margin-top:4px">Observatorio del Delito</div>
        <div style="font-size:12px;color:rgba(255,255,255,.7);margin-top:4px">Mindefensa · {fecha_hoy}</div>
      </div>
      <div style="height:4px;background:linear-gradient(to right,#FFE000 20%,#281FD0 20%)"></div>
      <div style="padding:16px 28px 0">
        <span style="background:{color_badge};color:white;font-size:10px;font-weight:bold;letter-spacing:2px;padding:4px 12px;border-radius:20px">{label_badge}</span>
      </div>
      <div style="padding:20px 28px">
        <h2 style="color:#281FD0;font-size:16px;margin:0 0 8px">{titulo}</h2>
        <p style="color:#606175;font-size:13px;margin:0 0 20px">{descripcion}</p>
        
        {novedades_html}

        <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
          <tr>
            <td style="background:#f4f4f8;padding:12px;border-radius:4px;text-align:center;width:33%">
              <div style="font-size:24px;font-weight:bold;color:#281FD0">{total}</div>
              <div style="font-size:11px;color:#606175">Archivos en portal</div>
            </td>
            <td style="width:2%"></td>
            <td style="background:#f4f4f8;padding:12px;border-radius:4px;text-align:center;width:33%">
              <div style="font-size:24px;font-weight:bold;color:#{"C0392B" if nuevos > 0 else "2E7D32"}">{nuevos}</div>
              <div style="font-size:11px;color:#606175">Descargas nuevas</div>
            </td>
            <td style="width:2%"></td>
            <td style="background:#f4f4f8;padding:12px;border-radius:4px;text-align:center;width:33%">
              <div style="font-size:24px;font-weight:bold;color:#{"FFB600" if cambios > 0 else "2E7D32"}">{cambios}</div>
              <div style="font-size:11px;color:#606175">Actualizados</div>
            </td>
          </tr>
        </table>
        {"<p style='color:#2E7D32;font-weight:bold;font-size:13px'>✅ Se adjunta el boletín PDF con el análisis consolidado.</p>" if REPORTE_PDF.exists() else ""}
      </div>
      <div style="background:#281FD0;padding:12px 28px;border-top:3px solid #FFE000">
        <p style="color:rgba(255,255,255,.7);font-size:10px;margin:0;text-align:center">
          Alcaldía de Jamundí · Secretaría de Seguridad y Convivencia · Fuente: Mindefensa
        </p>
      </div>
    </div>
    </body></html>
    """

    msg = MIMEMultipart("mixed")
    msg["Subject"] = asunto
    msg["From"]    = CORREO
    msg["To"]      = DESTINO
    msg.attach(MIMEText(html, "html"))

    if REPORTE_PDF.exists():
        with open(REPORTE_PDF, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={REPORTE_PDF.name}")
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(CORREO, PASSWD)
        server.sendmail(CORREO, DESTINO, msg.as_string())
    print(f"Correo Mindefensa enviado a {DESTINO} [{tipo}]")

if __name__ == "__main__":
    enviar_resumen()
