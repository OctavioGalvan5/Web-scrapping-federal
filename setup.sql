CREATE TABLE IF NOT EXISTS licenses (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) UNIQUE NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expedientes (
    id SERIAL PRIMARY KEY,
    numero_expte VARCHAR(100) UNIQUE NOT NULL,
    anio VARCHAR(10),
    caratula TEXT,
    jurisdiccion VARCHAR(255),
    dependencia VARCHAR(255),
    situacion_actual VARCHAR(255),
    actor_nombre TEXT,
    letrado_apoderado TEXT,
    tomo_folio VARCHAR(100),
    cuit_cuil VARCHAR(50),
    fecha_ingreso DATE,
    origen VARCHAR(20) DEFAULT 'scraper',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS fuente VARCHAR(50);
ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS usuario_extraccion VARCHAR(100);
ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS es_repetido BOOLEAN DEFAULT FALSE;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'expedientes_numero_expte_key') THEN
    ALTER TABLE expedientes DROP CONSTRAINT expedientes_numero_expte_key;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_expedientes_expte_fecha') THEN
    ALTER TABLE expedientes ADD CONSTRAINT uq_expedientes_expte_fecha UNIQUE (numero_expte, fecha_ingreso);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS scraper_runs (
    id SERIAL PRIMARY KEY,
    fecha_buscada DATE NOT NULL,
    fecha_ejecucion TIMESTAMP DEFAULT NOW(),
    paginas INTEGER,
    filas_deox INTEGER,
    usuario VARCHAR(100),
    resultado VARCHAR(20),
    nuevos INTEGER DEFAULT 0,
    repetidos INTEGER DEFAULT 0,
    error_msg TEXT
);

CREATE TABLE IF NOT EXISTS analisis_ia (
    id SERIAL PRIMARY KEY,
    expediente_id INTEGER REFERENCES expedientes(id) ON DELETE CASCADE,
    analisis_texto TEXT,
    fecha_analisis TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vencimientos (
    id SERIAL PRIMARY KEY,
    expediente_id INTEGER REFERENCES expedientes(id) ON DELETE CASCADE,
    fecha_vencimiento DATE,
    descripcion TEXT,
    dias_plazo INTEGER,
    tipo_dias VARCHAR(20),
    fecha_documento DATE,
    texto_relevante TEXT,
    fecha_analisis TIMESTAMP DEFAULT NOW()
);
