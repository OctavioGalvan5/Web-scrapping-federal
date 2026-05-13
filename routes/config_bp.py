from flask import Blueprint, render_template, request, jsonify
from database.db import query_one, execute

config_bp = Blueprint('config', __name__)


def get_prompt():
    row = query_one("SELECT value FROM app_config WHERE key = 'prompt_analisis'")
    return row['value'] if row else ''


@config_bp.route('/')
def config_page():
    prompt = get_prompt()
    return render_template('config.html', prompt=prompt)


@config_bp.route('/guardar', methods=['POST'])
def guardar():
    data = request.json
    nuevo_prompt = data.get('prompt', '').strip()
    if not nuevo_prompt:
        return jsonify({'error': 'El prompt no puede estar vacío'}), 400
    execute(
        "INSERT INTO app_config (key, value) VALUES ('prompt_analisis', %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (nuevo_prompt,)
    )
    return jsonify({'ok': True})
