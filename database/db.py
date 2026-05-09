import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import config


@contextmanager
def get_db():
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql, params=None):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def query_one(sql, params=None):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql, params=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def init_db():
    with open('setup.sql') as f:
        sql = f.read()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("Base de datos inicializada correctamente")
