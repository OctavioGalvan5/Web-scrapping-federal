from flask import Blueprint, render_template, request, jsonify
from database.db import query, get_db

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
def admin_page():
    licencias = query("SELECT * FROM licenses ORDER BY created_at DESC")
    return render_template('admin.html', licencias=licencias)


@admin_bp.route('/licencias', methods=['POST'])
def crear_licencia():
    d = request.json
    machine_id  = (d.get('machine_id') or '').strip()
    user_email  = (d.get('user_email') or '').strip()

    if not machine_id or not user_email:
        return jsonify({'error': 'machine_id y user_email son requeridos'}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO licenses (machine_id, user_email, active)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT (machine_id) DO UPDATE SET user_email=%s, active=TRUE
                    RETURNING id
                """, (machine_id, user_email, user_email))
                lid = cur.fetchone()[0]
        return jsonify({'ok': True, 'id': lid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/licencias/<int:lid>/toggle', methods=['POST'])
def toggle_licencia(lid):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE licenses SET active = NOT active WHERE id=%s RETURNING active",
                    (lid,)
                )
                new_state = cur.fetchone()[0]
        return jsonify({'ok': True, 'active': new_state})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/licencias/<int:lid>', methods=['DELETE'])
def eliminar_licencia(lid):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM licenses WHERE id=%s", (lid,))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
