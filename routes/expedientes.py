import io
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file
from database.db import query, get_db

expedientes_bp = Blueprint('expedientes', __name__)


def _build_filters(args):
    conditions = []
    params = []

    if args.get('busqueda'):
        conditions.append(
            "(numero_expte ILIKE %s OR caratula ILIKE %s OR actor_nombre ILIKE %s)"
        )
        term = f"%{args['busqueda']}%"
        params += [term, term, term]

    if args.get('dependencia'):
        conditions.append("dependencia ILIKE %s")
        params.append(f"%{args['dependencia']}%")

    if args.get('jurisdiccion'):
        conditions.append("jurisdiccion ILIKE %s")
        params.append(f"%{args['jurisdiccion']}%")

    if args.get('origen') and args['origen'] != 'todos':
        conditions.append("origen = %s")
        params.append(args['origen'])

    if args.get('fecha_desde'):
        conditions.append("fecha_ingreso >= %s")
        params.append(args['fecha_desde'])

    if args.get('fecha_hasta'):
        conditions.append("fecha_ingreso <= %s")
        params.append(args['fecha_hasta'])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


@expedientes_bp.route('/')
def expedientes_page():
    return render_template('expedientes.html')


@expedientes_bp.route('/datos')
def datos():
    where, params = _build_filters(request.args)
    rows = query(
        f"""
        SELECT id, numero_expte, anio, caratula, dependencia, jurisdiccion,
               situacion_actual, actor_nombre, letrado_apoderado, cuit_cuil,
               fecha_ingreso::text, origen, fuente, usuario_extraccion, created_at
        FROM expedientes
        {where}
        ORDER BY created_at DESC
        LIMIT 1000
        """,
        params or None,
    )
    total = query(f"SELECT COUNT(*) AS n FROM expedientes {where}", params or None)[0]['n']
    return jsonify({'data': [dict(r) for r in rows], 'total': total})


@expedientes_bp.route('/exportar')
def exportar():
    where, params = _build_filters(request.args)
    rows = query(
        f"""
        SELECT numero_expte, anio, caratula, jurisdiccion, dependencia,
               situacion_actual, actor_nombre, letrado_apoderado,
               tomo_folio, cuit_cuil, fecha_ingreso, origen, created_at
        FROM expedientes
        {where}
        ORDER BY created_at DESC
        """,
        params or None,
    )

    df = pd.DataFrame([dict(r) for r in rows])
    df.columns = [
        'Expediente', 'Año', 'Carátula', 'Jurisdicción', 'Dependencia',
        'Sit. Actual', 'Actor/Nombre', 'Letrado/Apoderado',
        'Tomo/Folio', 'CUIT/CUIL', 'Fecha Ingreso', 'Origen', 'Fecha Carga'
    ]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Expedientes')
    buf.seek(0)

    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='expedientes_exportados.xlsx',
    )


@expedientes_bp.route('/plantilla')
def plantilla():
    df = pd.DataFrame(columns=[
        'Número', 'Año', 'Carátula', 'Jurisdicción', 'Dependencia',
        'Sit. Actual', 'Actor/Nombre', 'Letrado/Apoderado', 'Tomo/Folio', 'CUIT/CUIL'
    ])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Expedientes')
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='plantilla_expedientes.xlsx',
    )


@expedientes_bp.route('/importar', methods=['POST'])
def importar():
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    file = request.files['archivo']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'El archivo debe ser .xlsx o .xls'}), 400

    try:
        df = pd.read_excel(file)
        cols = df.columns.tolist()

        def get_col(row, names):
            for n in names:
                if n in cols:
                    v = row.get(n, '')
                    return str(v).strip() if pd.notna(v) else ''
            return ''

        nuevos = 0
        repetidos = []
        errores = 0

        with get_db() as conn:
            with conn.cursor() as cur:
                for _, row in df.iterrows():
                    try:
                        numero = get_col(row, ['Número', 'Numero', 'numero', 'NRO'])
                        anio   = get_col(row, ['Año', 'Anio', 'anio', 'AÑO'])
                        if not numero or not anio:
                            continue
                        numero_expte = f"{numero}/{anio}"

                        cur.execute("""
                            INSERT INTO expedientes
                                (numero_expte, anio, caratula, jurisdiccion, dependencia,
                                 situacion_actual, actor_nombre, letrado_apoderado,
                                 tomo_folio, cuit_cuil, origen)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'manual')
                            ON CONFLICT (numero_expte) DO NOTHING
                            RETURNING id
                        """, (
                            numero_expte,
                            anio,
                            get_col(row, ['Carátula', 'Caratula', 'caratula']),
                            get_col(row, ['Jurisdicción', 'Jurisdiccion', 'jurisdiccion']),
                            get_col(row, ['Dependencia', 'dependencia']),
                            get_col(row, ['Sit. Actual', 'Situacion Actual', 'situacion_actual']),
                            get_col(row, ['Actor/Nombre', 'Actor', 'actor_nombre']),
                            get_col(row, ['Letrado/Apoderado', 'Letrado', 'letrado_apoderado']),
                            get_col(row, ['Tomo/Folio', 'tomo_folio']),
                            get_col(row, ['CUIT/CUIL', 'CUIT', 'cuit_cuil']),
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
                    except Exception:
                        errores += 1

        return jsonify({'nuevos': nuevos, 'repetidos': repetidos, 'errores': errores})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
