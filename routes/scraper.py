import threading
import queue
import uuid
import json
import subprocess
import sys
import os
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, request, Response, stream_with_context, jsonify
from database.db import get_db
import config

scraper_bp = Blueprint('scraper', __name__)

_tasks = {}
_tasks_lock = threading.Lock()


def _new_task():
    tid = str(uuid.uuid4())[:8]
    with _tasks_lock:
        _tasks[tid] = {'queue': queue.Queue(), 'status': 'running'}
    return tid


def _get_col(row, df_cols, names):
    for name in names:
        if name in df_cols:
            val = row.get(name, '')
            return str(val).strip() if pd.notna(val) else ''
    return ''


def _import_excel_to_db(excel_path, origen, fecha_buscada, q):
    results = {'nuevos': 0, 'repetidos': [], 'errores': 0}
    try:
        df = pd.read_excel(excel_path)
        cols = df.columns.tolist()

        with get_db() as conn:
            with conn.cursor() as cur:
                for _, row in df.iterrows():
                    try:
                        numero = _get_col(row, cols, ['Número', 'Numero', 'numero', 'NRO', 'Nro'])
                        anio   = _get_col(row, cols, ['Año', 'Anio', 'anio', 'AÑO', 'year'])
                        if not numero or not anio:
                            continue
                        numero_expte = f"{numero}/{anio}"

                        cur.execute("""
                            INSERT INTO expedientes
                                (numero_expte, anio, caratula, jurisdiccion, dependencia,
                                 situacion_actual, actor_nombre, letrado_apoderado,
                                 tomo_folio, cuit_cuil, fecha_ingreso, origen)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (numero_expte) DO NOTHING
                            RETURNING id
                        """, (
                            numero_expte,
                            anio,
                            _get_col(row, cols, ['Carátula', 'Caratula', 'caratula']),
                            _get_col(row, cols, ['Jurisdicción', 'Jurisdiccion', 'jurisdiccion']),
                            _get_col(row, cols, ['Dependencia', 'dependencia']),
                            _get_col(row, cols, ['Sit. Actual', 'Situacion Actual', 'situacion_actual']),
                            _get_col(row, cols, ['Actor/Nombre', 'Actor', 'actor_nombre']),
                            _get_col(row, cols, ['Letrado/Apoderado', 'Letrado', 'letrado_apoderado']),
                            _get_col(row, cols, ['Tomo/Folio', 'tomo_folio']),
                            _get_col(row, cols, ['CUIT/CUIL', 'CUIT', 'cuit_cuil']),
                            fecha_buscada,
                            origen,
                        ))

                        if cur.fetchone():
                            results['nuevos'] += 1
                        else:
                            cur.execute(
                                "SELECT caratula, created_at::date, origen FROM expedientes WHERE numero_expte=%s",
                                (numero_expte,)
                            )
                            ex = cur.fetchone()
                            results['repetidos'].append({
                                'numero_expte': numero_expte,
                                'caratula': (ex[0] or '')[:60] if ex else '',
                                'fecha': ex[1].strftime('%d/%m/%Y') if ex else '',
                                'origen': ex[2] if ex else '',
                            })
                    except Exception:
                        results['errores'] += 1
    except Exception as e:
        if q:
            q.put(f"❌ Error importando Excel: {e}\n")
    return results


def _log_run(fecha_buscada, paginas, filas_deox, usuario, resultado, nuevos, repetidos, error_msg=None):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO scraper_runs
                        (fecha_buscada, paginas, filas_deox, usuario, resultado, nuevos, repetidos, error_msg)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (fecha_buscada, paginas, filas_deox, usuario, resultado, nuevos, repetidos, error_msg))
    except Exception:
        pass


def _run_thread(task_id, script_name, args, post_import=None):
    q = _tasks[task_id]['queue']
    scraper_dir = os.path.abspath(config.SCRAPER_PATH)
    script = os.path.join(scraper_dir, script_name)

    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        proc = subprocess.Popen(
            [sys.executable, '-u', script] + [str(a) for a in args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=scraper_dir,
            text=True,
            encoding='utf-8',
            bufsize=1,
            env=env,
        )
        for line in iter(proc.stdout.readline, ''):
            q.put(line)
        proc.stdout.close()
        proc.wait()

        if post_import:
            post_import(q)

        with _tasks_lock:
            _tasks[task_id]['status'] = 'done'

    except Exception as e:
        q.put(f"\n❌ ERROR: {e}\n")
        with _tasks_lock:
            _tasks[task_id]['status'] = 'error'
    finally:
        q.put(None)


def _post_import_extraccion(fecha, paginas, filas_deox, usuario):
    def _inner(q):
        scraper_dir = os.path.abspath(config.SCRAPER_PATH)
        excel_path  = os.path.join(scraper_dir, 'expedientes.xlsx')
        if not os.path.exists(excel_path):
            q.put("⚠️  No se encontró expedientes.xlsx para importar\n")
            return

        q.put("\n" + "=" * 60 + "\n")
        q.put("📥 Importando resultados a la base de datos...\n")

        fecha_dt = datetime.strptime(fecha, '%d/%m/%Y').date()
        results  = _import_excel_to_db(excel_path, 'scraper', fecha_dt, q)

        q.put(f"\n📊 RESULTADO DE IMPORTACIÓN:\n")
        q.put(f"✅ {results['nuevos']} expedientes nuevos guardados\n")

        if results['repetidos']:
            q.put(f"⚠️  {len(results['repetidos'])} ya existían (ignorados):\n")
            for rep in results['repetidos']:
                q.put(f"   - {rep['numero_expte']} | {rep['caratula']}\n")
                q.put(f"     (ingresado el {rep['fecha']} - origen: {rep['origen']})\n")

        if results['errores']:
            q.put(f"❌ {results['errores']} errores al importar\n")

        q.put("=" * 60 + "\n")

        _log_run(
            fecha_dt, paginas, filas_deox, usuario,
            'ok', results['nuevos'], len(results['repetidos'])
        )
    return _inner


@scraper_bp.route('/')
def scraper_page():
    return render_template('scraper.html')


@scraper_bp.route('/iniciar_extraccion', methods=['POST'])
def iniciar_extraccion():
    d = request.json
    task_id = _new_task()
    threading.Thread(
        target=_run_thread,
        args=(
            task_id,
            'run_extraccion.py',
            [d['fecha'], d['paginas'], d['usuario'], d['password'],
             str(d['headless']).lower(), d['filas_deox']],
            _post_import_extraccion(d['fecha'], int(d['paginas']), int(d['filas_deox']), d['usuario']),
        ),
        daemon=True,
    ).start()
    return jsonify({'task_id': task_id})


@scraper_bp.route('/iniciar_analisis', methods=['POST'])
def iniciar_analisis():
    d = request.json
    task_id = _new_task()
    threading.Thread(
        target=_run_thread,
        args=(
            task_id,
            'run_analisis.py',
            [d['usuario'], d['password'], str(d['headless']).lower(),
             d['gemini_api'], d['captcha_api']],
        ),
        daemon=True,
    ).start()
    return jsonify({'task_id': task_id})


@scraper_bp.route('/iniciar_vencimientos', methods=['POST'])
def iniciar_vencimientos():
    d = request.json
    task_id = _new_task()
    threading.Thread(
        target=_run_thread,
        args=(
            task_id,
            'run_vencimientos.py',
            [d['gemini_api'], d['captcha_api'], str(d['headless']).lower()],
        ),
        daemon=True,
    ).start()
    return jsonify({'task_id': task_id})


@scraper_bp.route('/stream/<task_id>')
def stream(task_id):
    def generate():
        task = _tasks.get(task_id)
        if not task:
            yield f"data: {json.dumps({'error': 'Tarea no encontrada'})}\n\n"
            return
        q = task['queue']
        while True:
            try:
                msg = q.get(timeout=30)
                if msg is None:
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break
                yield f"data: {json.dumps({'text': msg})}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'ping': True})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
