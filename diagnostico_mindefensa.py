import requests
import re
import json
from datetime import datetime
from pathlib import Path

print("="*80)
print("🔍 DIAGNÓSTICO MINDEFENSA - VERSIÓN DETALLADA")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("="*80 + "\n")

URL = "https://www.mindefensa.gov.co/defensa-y-seguridad/datos-y-cifras/informacion-estadistica"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("📡 PASO 1: Conectando a MinDefensa...")
try:
    response = requests.get(URL, headers=headers, timeout=30)
    print(f"✅ Conexión exitosa (Status: {response.status_code})")
    print(f"📄 Tamaño del HTML: {len(response.text):,} caracteres\n")
except Exception as e:
    print(f"❌ ERROR DE CONEXIÓN: {e}")
    print("💡 Verificá tu internet o si la página está disponible")
    exit()

print("📡 PASO 2: Buscando archivos .xlsx en el HTML...")

# Método 1: Buscar enlaces <a href="*.xlsx">
enlaces_xlsx = re.findall(r'href=["\']([^"\']*\.xlsx)["\']', response.text, re.IGNORECASE)
print(f"   Método 1 (enlaces): {len(enlaces_xlsx)} encontrados")

# Método 2: Buscar nombres de archivo en texto plano
nombres_xlsx = re.findall(r'([A-ZÁ-Ú][A-ZÁ-Ú\s]+\.xlsx)', response.text)
print(f"   Método 2 (texto): {len(nombres_xlsx)} encontrados")

# Método 3: Buscar patrón completo (nombre + fecha + usuario)
patron_completo = re.findall(r'([A-ZÁ-Ú\s]+\.xlsx)\s*\n*\s*([\d/]+,\s*[\d:]+)\s*\n*\s*(\w+)', response.text, re.IGNORECASE)
print(f"   Método 3 (completo): {len(patron_completo)} encontrados\n")

if len(enlaces_xlsx) == 0 and len(nombres_xlsx) == 0 and len(patron_completo) == 0:
    print("⚠️ NO SE ENCONTRARON ARCHIVOS .XLSX")
    print("\n📄 FRAGMENTO DEL HTML (primeros 3000 caracteres):")
    print("-"*80)
    print(response.text[:3000])
    print("-"*80)
else:
    print("✅ ARCHIVOS ENCONTRADOS:\n")
    
    archivos = []
    
    # Usar el método que encontró más resultados
    if len(patron_completo) > 0:
        for nombre, fecha, usuario in patron_completo:
            archivos.append({"nombre": nombre.strip(), "fecha": fecha.strip(), "usuario": usuario.strip()})
    elif len(nombres_xlsx) > 0:
        for nombre in set(nombres_xlsx):
            archivos.append({"nombre": nombre.strip(), "fecha": "N/A", "usuario": "N/A"})
    
    print(f"📋 TOTAL: {len(archivos)} archivos\n")
    
    # Mostrar todos
    for i, arch in enumerate(archivos, 1):
        print(f"{i:2d}. {arch['nombre']:<50} {arch['fecha']:>20}")

print("\n" + "="*80)
print("✅ DIAGNÓSTICO COMPLETADO")
print("="*80)
