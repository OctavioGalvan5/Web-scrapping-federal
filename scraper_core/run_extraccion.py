#!/usr/bin/env python3
import sys
import os

# Forzar line-buffering para que los logs lleguen al frontend en tiempo real
sys.stdout.reconfigure(line_buffering=True)

# En Docker, usar el chromedriver del sistema en lugar de descargarlo
if os.environ.get('DOCKER_ENV'):
    from webdriver_manager.chrome import ChromeDriverManager
    ChromeDriverManager.install = lambda self: os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

from codigo_con_deox_ia import filtrar_por_fecha

fecha      = sys.argv[1]
paginas    = int(sys.argv[2])
usuario    = sys.argv[3]
password   = sys.argv[4]
headless   = sys.argv[5].lower() == 'true'
filas_deox = int(sys.argv[6])

todos_los_datos = filtrar_por_fecha(fecha, paginas, usuario, password, headless, filas_deox)

if not todos_los_datos:
    print("\n" + "=" * 60)
    print("📊 RESULTADO DE IMPORTACIÓN:")
    print("✅ 0 expedientes nuevos guardados")
    print("=" * 60)
    sys.exit(0)

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("\n⚠️  DATABASE_URL no disponible, no se guardó en base de datos")
    sys.exit(0)

import psycopg2
from datetime import datetime

print("\n" + "=" * 60)
print("📥 Importando resultados a la base de datos...")

try:
    conn = psycopg2.connect(database_url)
    fecha_dt = datetime.strptime(fecha, '%d/%m/%Y').date()
    nuevos = 0
    repetidos = []

    with conn:
        with conn.cursor() as cur:
            for fila in todos_los_datos:
                numero = fila.get('numero_expediente', '')
                ano    = fila.get('ano_expediente', '')
                if not numero or not ano:
                    continue
                numero_expte = f"{numero}/{ano}"

                cur.execute("""
                    INSERT INTO expedientes
                        (numero_expte, anio, caratula, dependencia,
                         situacion_actual, fecha_ingreso, origen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (numero_expte) DO NOTHING
                    RETURNING id
                """, (
                    numero_expte,
                    ano,
                    fila.get('causa', ''),
                    fila.get('juzgado', ''),
                    fila.get('estado', ''),
                    fecha_dt,
                    'scraper',
                ))

                if cur.fetchone():
                    nuevos += 1
                else:
                    cur.execute(
                        "SELECT caratula, created_at::date, origen FROM expedientes WHERE numero_expte=%s",
                        (numero_expte,)
                    )
                    ex = cur.fetchone()
                    repetidos.append({
                        'numero_expte': numero_expte,
                        'caratula': (ex[0] or '')[:60] if ex else '',
                        'fecha': ex[1].strftime('%d/%m/%Y') if ex else '',
                        'origen': ex[2] if ex else '',
                    })

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO scraper_runs
                    (fecha_buscada, paginas, filas_deox, usuario, resultado, nuevos, repetidos, error_msg)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (fecha_dt, paginas, filas_deox, usuario, 'ok', nuevos, len(repetidos), None))

    conn.close()

    print(f"\n📊 RESULTADO DE IMPORTACIÓN:")
    print(f"✅ {nuevos} expedientes nuevos guardados")
    if repetidos:
        print(f"⚠️  {len(repetidos)} ya existían (ignorados):")
        for rep in repetidos:
            print(f"   - {rep['numero_expte']} | {rep['caratula']}")
            print(f"     (ingresado el {rep['fecha']} - origen: {rep['origen']})")
    print("=" * 60)

except Exception as e:
    print(f"❌ Error importando a base de datos: {e}")
