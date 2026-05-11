import threading
import queue
import uuid
import json
import subprocess
import sys
import os
from flask import Blueprint, render_template, request, Response, stream_with_context, jsonify
import config

scraper_bp = Blueprint('scraper', __name__)

_tasks = {}
_tasks_lock = threading.Lock()


def _new_task():
    tid = str(uuid.uuid4())[:8]
    with _tasks_lock:
        _tasks[tid] = {'queue': queue.Queue(), 'status': 'running'}
    return tid


def _run_thread(task_id, script_name, args):
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

        with _tasks_lock:
            _tasks[task_id]['status'] = 'done'

    except Exception as e:
        q.put(f"\n❌ ERROR: {e}\n")
        with _tasks_lock:
            _tasks[task_id]['status'] = 'error'
    finally:
        q.put(None)


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
