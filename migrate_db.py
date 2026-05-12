from database.db import get_db

def migrate():
    print("Iniciando migración de base de datos...")
    commands = [
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS fuente VARCHAR(50);",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS usuario_extraccion VARCHAR(100);",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS es_repetido BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS jurisdiccion VARCHAR(255);",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS subido_a_tareas BOOLEAN DEFAULT FALSE;"
    ]
    
    with get_db() as conn:
        with conn.cursor() as cur:
            for cmd in commands:
                try:
                    cur.execute(cmd)
                    print(f"Ejecutado: {cmd}")
                except Exception as e:
                    print(f"Error en {cmd}: {e}")
    print("Migración finalizada.")

if __name__ == "__main__":
    migrate()
