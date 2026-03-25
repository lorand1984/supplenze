from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registrazione blueprint
    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    from app.routes.upload import upload_bp
    app.register_blueprint(upload_bp)

    from app.routes.assegnazioni import assegnazioni_bp
    app.register_blueprint(assegnazioni_bp)

    # Variabile globale per memorizzare le ultime assegnazioni
    app.config['ULTIME_ASSEGNAZIONI'] = []
    
    print(app.url_map)


    return app