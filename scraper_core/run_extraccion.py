#!/usr/bin/env python3
import sys
import os

# Forzar line-buffering para que los logs lleguen al frontend en tiempo real
sys.stdout.reconfigure(line_buffering=True)

# En Docker, usar el chromedriver del sistema en lugar de descargarlo
if os.environ.get('DOCKER_ENV'):
    from webdriver_manager.chrome import ChromeDriverManager
    ChromeDriverManager.install = lambda self: os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

from codigo_con_deox_ia import filtrar_por_fecha

fecha      = sys.argv[1]
paginas    = int(sys.argv[2])
usuario    = sys.argv[3]
password   = sys.argv[4]
headless   = sys.argv[5].lower() == 'true'
filas_deox = int(sys.argv[6])

filtrar_por_fecha(fecha, paginas, usuario, password, headless, filas_deox)
