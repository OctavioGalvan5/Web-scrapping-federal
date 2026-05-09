import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
SECRET_KEY   = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# En Docker apunta a scraper_core/ dentro del contenedor
# En local puede configurarse con SCRAPER_PATH en .env
SCRAPER_PATH = os.environ.get(
    'SCRAPER_PATH',
    os.path.join(os.path.dirname(__file__), 'scraper_core')
)
