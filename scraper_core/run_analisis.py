#!/usr/bin/env python3
import sys
import os

sys.stdout.reconfigure(line_buffering=True)

if os.environ.get('DOCKER_ENV'):
    from webdriver_manager.chrome import ChromeDriverManager
    ChromeDriverManager.install = lambda self: os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

from codigo_con_deox_ia import analizar_expedientes_individuales

usuario     = sys.argv[1]
password    = sys.argv[2]
headless    = sys.argv[3].lower() == 'true'
gemini_api  = sys.argv[4]
captcha_api = sys.argv[5]

analizar_expedientes_individuales(usuario, password, headless, gemini_api, captcha_api)
