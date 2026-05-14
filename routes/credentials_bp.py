import base64
import hashlib
from flask import Blueprint, jsonify, request, render_template
from cryptography.fernet import Fernet
from database.db import get_db
import config

credentials_bp = Blueprint('credentials', __name__)


def _fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256(config.SECRET_KEY.encode()).digest())
    return Fernet(key)


def _encrypt(texto):
    return _fernet().encrypt(texto.encode()).decode()


def _decrypt(token):
    return _fernet().decrypt(token.encode()).decode()


@credentials_bp.route('/')
def index():
    return render_template('credentials.html')


@credentials_bp.route('/api/list')
def api_list():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, usuario FROM pjn_credentials ORDER BY nombre")
            rows = cur.fetchall()
    return jsonify([{'id': r[0], 'nombre': r[1], 'usuario': r[2]} for r in rows])


@credentials_bp.route('/api/guardar', methods=['POST'])
def api_guardar():
    d = request.json
    nombre   = (d.get('nombre') or '').strip()
    usuario  = (d.get('usuario') or '').strip()
    password = (d.get('password') or '').strip()
    cred_id  = d.get('id')

    if not nombre or not usuario or not password:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    password_enc = _encrypt(password)

    with get_db() as conn:
        with conn.cursor() as cur:
            if cred_id:
                cur.execute(
                    "UPDATE pjn_credentials SET nombre=%s, usuario=%s, password=%s WHERE id=%s",
                    (nombre, usuario, password_enc, cred_id)
                )
            else:
                cur.execute(
                    "INSERT INTO pjn_credentials (nombre, usuario, password) VALUES (%s, %s, %s)",
                    (nombre, usuario, password_enc)
                )
    return jsonify({'ok': True})


@credentials_bp.route('/api/<int:cred_id>', methods=['DELETE'])
def api_eliminar(cred_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pjn_credentials WHERE id=%s", (cred_id,))
    return jsonify({'ok': True})


@credentials_bp.route('/api/<int:cred_id>/password')
def api_password(cred_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT usuario, password FROM pjn_credentials WHERE id=%s", (cred_id,))
            row = cur.fetchone()
    if not row:
        return jsonify({'error': 'No encontrado'}), 404
    return jsonify({'usuario': row[0], 'password': _decrypt(row[1])})
