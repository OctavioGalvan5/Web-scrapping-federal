#!/usr/bin/env python3
import sys
import os

sys.stdout.reconfigure(line_buffering=True)

if os.environ.get('DOCKER_ENV'):
    from webdriver_manager.chrome import ChromeDriverManager
    ChromeDriverManager.install = lambda self: os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

from expediente_vencimientos_analyzer import analizar_vencimientos_expedientes

gemini_api  = sys.argv[1]
captcha_api = sys.argv[2]
headless    = sys.argv[3].lower() == 'true'

analizar_vencimientos_expedientes(gemini_api, captcha_api, headless)
