from flask import Flask
from database.db import init_db
from routes.main import main_bp
from routes.scraper import scraper_bp
from routes.expedientes import expedientes_bp
from routes.admin import admin_bp
from migrate_db import migrate
import config


def create_app():
    # Inicializar/Actualizar base de datos al arrancar
    try:
        migrate()
        init_db()
    except Exception as e:
        print(f"Advertencia al inicializar BD: {e}")

    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY

    app.register_blueprint(main_bp)
    app.register_blueprint(scraper_bp,     url_prefix='/scraper')
    app.register_blueprint(expedientes_bp, url_prefix='/expedientes')
    app.register_blueprint(admin_bp,       url_prefix='/admin')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
