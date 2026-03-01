import smtplib, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

CORREO_ORIGEN  = "forecesar@gmail.com"
CORREO_DESTINO = "forecesar@gmail.com"
APP_PASSWORD   = "xfrfdhpqzfzvdwnz"

STATE_FILE = Path("mindefensa_state.json")
LOG_FILE   = Path("monitor_log.txt")

def enviar_resumen():
    estado = {}
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            estado = json.load(f)

    ultima  = estado.get("ultima_revision", "—")
    total   = len(estado.get("archivos", {}))

    log_texto = ""
    if LOG_FILE.exists():
        lineas = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        log_texto = "\n".join(lineas[-40:])

    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""
    <html><body style="font-family:Calibri,Arial;background:#f4f4f8;padding:20px">
    <div style="max-width:600px;margin:0 auto;background:white;border-radius:4px;overflow:hidden">
      <div style="background:#281FD0;color:white;padding:20px 24px">
        <div style="font-size:18px;font-weight:bold;letter-spacing:1px">ALCALDÍA DE JAMUNDÍ</div>
        <div style="font-size:11px;opacity:.8;letter-spacing:2px;text-transform:uppercase">Observatorio del Delito · Reporte Automático</div>
        <div style="font-size:13px;color:#FFE000;margin-top:8px;font-weight:bold">{fecha_hoy}</div>
      </div>
      <div style="height:4px;background:linear-gradient(90deg,#281FD0 80%,#FFE000 80%)"></div>
      <div style="padding:24px">
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
          <tr style="background:#281FD0;color:white">
            <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px">INDICADOR</th>
            <th style="padding:8px 12px;text-align:right;font-size:11px;letter-spacing:1px">VALOR</th>
          </tr>
          <tr style="border-bottom:1px solid #eee">
            <td style="padding:8px 12px;font-size:13px">Archivos monitoreados</td>
            <td style="padding:8px 12px;text-align:right;font-weight:bold;color:#281FD0">{total}</td>
          </tr>
          <tr style="border-bottom:1px solid #eee;background:#fafafa">
            <td style="padding:8px 12px;font-size:13px">Última revisión</td>
            <td style="padding:8px 12px;text-align:right;font-size:12px;color:#606175">{ultima[:19]}</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;font-size:13px">Estado del sistema</td>
            <td style="padding:8px 12px;text-align:right;color:#2E7D32;font-weight:bold">✅ OPERATIVO</td>
          </tr>
        </table>
        <div style="background:#f4f4f8;border-left:4px solid #FFE000;padding:12px 16px;margin-bottom:16px">
          <div style="font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#606175;margin-bottom:6px">Log de ejecución</div>
          <pre style="font-size:11px;color:#3A3A44;white-space:pre-wrap;margin:0">{log_texto}</pre>
        </div>
        <div style="font-size:11px;color:#606175;text-align:center">
          Generado automáticamente · Monitor MinDefensa · Alcaldía de Jamundí
        </div>
      </div>
      <div style="background:#281FD0;color:rgba(255,255,255,0.6);padding:12px 24px;font-size:10px;text-align:center">
        www.jamundi.gov.co · Observatorio del Delito Municipal
      </div>
    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Monitor MinDefensa — {fecha_hoy} — {total} archivos"
    msg["From"]    = CORREO_ORIGEN
    msg["To"]      = CORREO_DESTINO
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(CORREO_ORIGEN, APP_PASSWORD.replace(" ",""))
        server.sendmail(CORREO_ORIGEN, CORREO_DESTINO, msg.as_string())

    print(f"Correo enviado a {CORREO_DESTINO}")

if __name__ == "__main__":
    enviar_resumen()
