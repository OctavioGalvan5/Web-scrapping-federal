#!/usr/bin/env python3
"""
Ejecuta el análisis IA sobre los expedientes de una fecha dada,
leyéndolos directamente de la base de datos.
"""
import sys
import os

sys.stdout.reconfigure(line_buffering=True)

if os.environ.get('DOCKER_ENV'):
    from webdriver_manager.chrome import ChromeDriverManager
    ChromeDriverManager.install = lambda self: os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

from codigo_con_deox_ia import analizar_expedientes_nuevos

usuario   = sys.argv[1]
password  = sys.argv[2]
headless  = sys.argv[3].lower() == 'true'
fecha     = sys.argv[4]  # DD/MM/YYYY

openai_api = os.environ.get('OPENAI_API_KEY', '')
if not openai_api:
    print("❌ OPENAI_API_KEY no configurada en el entorno")
    sys.exit(1)

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL no configurada")
    sys.exit(1)

import psycopg2
from datetime import datetime

try:
    fecha_dt = datetime.strptime(fecha, '%d/%m/%Y').date()
except ValueError:
    print(f"❌ Formato de fecha inválido: {fecha} (esperado DD/MM/YYYY)")
    sys.exit(1)

print(f"📅 Buscando expedientes del {fecha}...")

try:
    conn = psycopg2.connect(database_url)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT numero_expte, caratula, dependencia
            FROM expedientes
            WHERE fecha_ingreso = %s
        """, (fecha_dt,))
        filas = cur.fetchall()
    conn.close()
except Exception as e:
    print(f"❌ Error consultando la base de datos: {e}")
    sys.exit(1)

if not filas:
    print(f"ℹ️  No hay expedientes registrados para el {fecha}")
    sys.exit(0)

print(f"✅ {len(filas)} expediente(s) encontrado(s) para analizar")

# Convertir a formato que espera analizar_expedientes_nuevos
import re
expedientes = []
for numero_expte, caratula, dependencia in filas:
    # Extraer número y año del formato "FSA 007039/2026" o "12345/2024"
    m = re.search(r'(\d{1,9})/(\d{4})', numero_expte or '')
    if not m:
        print(f"   ⚠️  No se pudo parsear: {numero_expte}")
        continue
    expedientes.append({
        'numero_expediente': m.group(1),
        'ano_expediente':    m.group(2),
        'causa':             caratula or '',
        'juzgado':           dependencia or '',
        'estado':            '',
    })

analizar_expedientes_nuevos(expedientes, openai_api, usuario, password, headless)
