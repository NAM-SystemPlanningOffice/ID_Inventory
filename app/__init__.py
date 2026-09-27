from flask import Flask
import os

def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        from app.config import Config
        config_class = Config

    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 認証・認可（Azure App Service / Entra ID Easy Auth）
    from app.auth import init_auth
    init_auth(app)

    # ヘルスチェック（認証不要、App Service の死活監視用）
    @app.route('/healthz')
    def healthz():
        return {'status': 'ok'}, 200

    from app.blueprints.index import index_bp
    from app.blueprints.output import output_bp
    from app.blueprints.import_bp import import_bp
    from app.blueprints.system import system_bp
    from app.blueprints.organization import organization_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(output_bp, url_prefix='/output')
    app.register_blueprint(import_bp, url_prefix='/import')
    app.register_blueprint(system_bp, url_prefix='/system')
    app.register_blueprint(organization_bp, url_prefix='/organization')

    return app
