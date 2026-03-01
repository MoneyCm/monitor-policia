@echo off
cd C:\Users\Usuario\.openclaw\workspace
python monitor_ok.py >> monitor_log.txt 2>&1
python enviar_reporte.py >> monitor_log.txt 2>&1
