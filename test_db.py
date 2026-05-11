import sys
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL no encontrada en", env_path)
    sys.exit(1)

print("Conectando a:", db_url)

import psycopg2

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT version()")
    version = cur.fetchone()
    print("Conexion exitosa")
    print("PostgreSQL:", version[0])
    conn.close()
except Exception as e:
    print("Error de conexion:", e)
    sys.exit(1)
