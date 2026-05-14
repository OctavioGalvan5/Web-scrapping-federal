from database.db import get_db

def migrate():
    print("Iniciando migración de base de datos...")
    PROMPT_DEFAULT = (
        "Expediente: {numero_expte}\n"
        "Carátula: {causa}\n\n"
        "DOCUMENTOS DESCARGADOS:\n"
        "{pdfs_str}\n\n"
        "Hacé un resumen claro y conciso del contenido de los documentos."
    )

    commands = [
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS fuente VARCHAR(50);",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS usuario_extraccion VARCHAR(100);",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS es_repetido BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS jurisdiccion VARCHAR(255);",
        "ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS subido_a_tareas BOOLEAN DEFAULT FALSE;",
        """
        CREATE TABLE IF NOT EXISTS app_config (
            key   VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL
        );
        """,
        f"""
        INSERT INTO app_config (key, value)
        VALUES ('prompt_analisis', $${PROMPT_DEFAULT}$$)
        ON CONFLICT (key) DO NOTHING;
        """,
        """
        UPDATE expedientes
        SET numero_expte = (
            LPAD(
                TRIM(LEADING '0' FROM split_part(numero_expte, '/', 1)),
                1, '0'
            ) || '/' || split_part(numero_expte, '/', 2)
        )
        WHERE numero_expte ~ '^[0-9]+/[0-9]{4}$'
          AND split_part(numero_expte, '/', 1) ~ '^0+[1-9]';
        """,
        """
        CREATE TABLE IF NOT EXISTS pjn_credentials (
            id         SERIAL PRIMARY KEY,
            nombre     VARCHAR(100) NOT NULL,
            usuario    VARCHAR(150) NOT NULL,
            password   TEXT         NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
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
