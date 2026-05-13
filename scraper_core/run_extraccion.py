#!/usr/bin/env python3
import sys
import os

# Forzar line-buffering para que los logs lleguen al frontend en tiempo real
sys.stdout.reconfigure(line_buffering=True)

# En Docker, usar el chromedriver del sistema en lugar de descargarlo
if os.environ.get('DOCKER_ENV'):
    from webdriver_manager.chrome import ChromeDriverManager
    ChromeDriverManager.install = lambda self: os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

from codigo_con_deox_ia import filtrar_por_fecha, analizar_expedientes_nuevos

fecha       = sys.argv[1]
paginas     = int(sys.argv[2])
usuario     = sys.argv[3]
password    = sys.argv[4]
headless    = sys.argv[5].lower() == 'true'
filas_deox  = int(sys.argv[6])
openai_api  = os.environ.get('OPENAI_API_KEY', '')

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

expedientes_para_analizar = []

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

                # Mismo expediente mismo dia -> ignorar (no analizar)
                cur.execute(
                    "SELECT id FROM expedientes WHERE numero_expte=%s AND fecha_ingreso=%s",
                    (numero_expte, fecha_dt)
                )
                if cur.fetchone():
                    repetidos.append({'numero_expte': numero_expte, 'caratula': fila.get('causa', '')[:60], 'fecha': fecha_dt.strftime('%d/%m/%Y'), 'origen': 'scraper'})
                    continue

                # Mismo expediente distinto dia -> guardar como repetido
                cur.execute("SELECT id FROM expedientes WHERE numero_expte=%s", (numero_expte,))
                es_repetido = cur.fetchone() is not None

                cur.execute("""
                    INSERT INTO expedientes
                        (numero_expte, anio, caratula, dependencia,
                         situacion_actual, fecha_ingreso, origen,
                         fuente, usuario_extraccion, es_repetido)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (numero_expte, fecha_ingreso) DO NOTHING
                    RETURNING id
                """, (
                    numero_expte, ano,
                    fila.get('causa', ''),
                    fila.get('juzgado', ''),
                    fila.get('estado', ''),
                    fecha_dt, 'scraper', 'deox', usuario, es_repetido,
                ))

                if cur.fetchone():
                    if es_repetido:
                        repetidos.append({'numero_expte': numero_expte, 'caratula': fila.get('causa', '')[:60], 'fecha': fecha_dt.strftime('%d/%m/%Y'), 'origen': 'scraper'})
                    else:
                        nuevos += 1
                    # Agregar a la lista de análisis (nuevos Y repetidos de otro día)
                    expedientes_para_analizar.append(fila)

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

# Fase 2: análisis IA de los expedientes guardados hoy
analizar_expedientes_nuevos(expedientes_para_analizar, openai_api, usuario, password, headless)
