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
        df_raw = pd.read_excel(file, header=None)

        COLS_CONOCIDAS = {'número', 'numero', 'nro', 'año', 'anio', 'carátula',
                          'caratula', 'dependencia', 'expediente'}

        primera_fila = [str(v).strip().lower() for v in df_raw.iloc[0].tolist()]
        tiene_cabecera = any(c in COLS_CONOCIDAS for c in primera_fila)

        if tiene_cabecera:
            df = pd.read_excel(file)
            modo = 'plantilla'
        else:
            df = df_raw.copy()
            df.columns = range(len(df.columns))
            modo = 'raw'

        def _str(v):
            if pd.isna(v):
                return ''
            s = str(v).strip()
            return '' if s.lower() in ('nan', 'none') else s

        def parsear_expte_raw(expte_str):
            """FSA 007039/2026 → numero_expte='FSA 007039/2026', anio='2026'"""
            expte_str = expte_str.strip()
            import re
            m = re.search(r'/(\d{4})(?:/|$)', expte_str)
            anio = m.group(1) if m else ''
            return expte_str, anio

        cols = df.columns.tolist() if modo == 'plantilla' else []

        def get_col(row, names):
            for n in names:
                if n in cols:
                    v = row.get(n, '')
                    return _str(v)
            return ''

        nuevos = 0
        repetidos = []
        errores = 0

        with get_db() as conn:
            with conn.cursor() as cur:
                for _, row in df.iterrows():
                    try:
                        if modo == 'raw':
                            numero_expte = _str(row[0])
                            if not numero_expte:
                                continue
                            numero_expte, anio = parsear_expte_raw(numero_expte)
                            dependencia      = _str(row[1]) if len(row) > 1 else ''
                            caratula         = _str(row[2]) if len(row) > 2 else ''
                            situacion_actual = _str(row[3]) if len(row) > 3 else ''
                            fecha_raw        = row[4] if len(row) > 4 else None
                            fecha_ingreso    = pd.to_datetime(fecha_raw, errors='coerce')
                            fecha_ingreso    = fecha_ingreso.date() if pd.notna(fecha_ingreso) else None
                        else:
                            numero = get_col(row, ['Número', 'Numero', 'numero', 'NRO'])
                            anio   = get_col(row, ['Año', 'Anio', 'anio', 'AÑO'])
                            if not numero or not anio:
                                continue
                            numero_expte     = f"{numero}/{anio}"
                            dependencia      = get_col(row, ['Dependencia', 'dependencia'])
                            caratula         = get_col(row, ['Carátula', 'Caratula', 'caratula'])
                            situacion_actual = get_col(row, ['Sit. Actual', 'Situacion Actual', 'situacion_actual'])
                            fecha_ingreso    = None

                        cur.execute("""
                            INSERT INTO expedientes
                                (numero_expte, anio, caratula, dependencia,
                                 situacion_actual, fecha_ingreso, origen,
                                 jurisdiccion, actor_nombre, letrado_apoderado,
                                 tomo_folio, cuit_cuil)
                            VALUES (%s,%s,%s,%s,%s,%s,'manual',%s,%s,%s,%s,%s)
                            ON CONFLICT (numero_expte) DO NOTHING
                            RETURNING id
                        """, (
                            numero_expte, anio, caratula, dependencia,
                            situacion_actual, fecha_ingreso,
                            get_col(row, ['Jurisdicción', 'Jurisdiccion', 'jurisdiccion']) if modo == 'plantilla' else '',
                            get_col(row, ['Actor/Nombre', 'Actor', 'actor_nombre'])        if modo == 'plantilla' else '',
                            get_col(row, ['Letrado/Apoderado', 'Letrado', 'letrado_apoderado']) if modo == 'plantilla' else '',
                            get_col(row, ['Tomo/Folio', 'tomo_folio'])                    if modo == 'plantilla' else '',
                            get_col(row, ['CUIT/CUIL', 'CUIT', 'cuit_cuil'])              if modo == 'plantilla' else '',
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
