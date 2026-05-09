from flask import Blueprint, render_template
from database.db import query

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    try:
        stats = query("""
            SELECT
                COUNT(*)                                              AS total,
                COUNT(*) FILTER (WHERE origen = 'scraper')           AS del_scraper,
                COUNT(*) FILTER (WHERE origen = 'manual')            AS manuales,
                COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) AS hoy
            FROM expedientes
        """)[0]

        ultimas_runs = query("""
            SELECT fecha_buscada, fecha_ejecucion, nuevos, repetidos, resultado
            FROM scraper_runs
            ORDER BY fecha_ejecucion DESC
            LIMIT 5
        """)

        proximos_vencimientos = query("""
            SELECT e.numero_expte, e.caratula, v.fecha_vencimiento, v.descripcion,
                   (v.fecha_vencimiento - CURRENT_DATE) AS dias_restantes
            FROM vencimientos v
            JOIN expedientes e ON e.id = v.expediente_id
            WHERE v.fecha_vencimiento >= CURRENT_DATE
            ORDER BY v.fecha_vencimiento ASC
            LIMIT 5
        """)
    except Exception:
        stats = {'total': 0, 'del_scraper': 0, 'manuales': 0, 'hoy': 0}
        ultimas_runs = []
        proximos_vencimientos = []

    return render_template(
        'index.html',
        stats=stats,
        ultimas_runs=ultimas_runs,
        proximos_vencimientos=proximos_vencimientos
    )
