import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import models and database
from src.models.user import db, User, UserRole
from src.models.product import Product, Category
from src.models.cart import Cart, CartItem, Order, OrderItem

# Import routes
from src.routes.auth import auth_bp
from src.routes.products import products_bp
from src.routes.cart import cart_bp
from src.routes.orders import orders_bp
from src.routes.payments import payments_bp
from src.routes.admin import admin_bp

# Import configuration
from src.config import config

def create_app(config_name='default'):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Configure CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    
    # Configure rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
        default_limits=["1000 per hour"]
    )
    
    # Rate limit for auth endpoints
    limiter.limit("5 per minute")(auth_bp)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(cart_bp, url_prefix='/api/cart')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(role=UserRole.ADMIN).first()
        if not admin_user:
            admin = User.create_admin_user(
                email='admin@ecommerce.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            db.session.add(admin)
            
            # Create default categories
            categories = [
                Category(name='Automação Industrial', description='Produtos para automação industrial'),
                Category(name='Elétrica Residencial', description='Produtos elétricos residenciais'),
                Category(name='Iluminação', description='Produtos de iluminação'),
                Category(name='Motores', description='Motores elétricos'),
                Category(name='Sensores', description='Sensores e detectores'),
                Category(name='Controladores', description='Controladores e PLCs')
            ]
            
            for category in categories:
                db.session.add(category)
            
            try:
                db.session.commit()
                print("Default admin user and categories created successfully!")
                print("Admin credentials: admin@ecommerce.com / admin123")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating default data: {e}")

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has expired'}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid token'}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'error': 'Authorization token is required'}, 401

    # Frontend serving routes
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "E-commerce API is running! Check /api endpoints for API documentation.", 200

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'E-commerce API is running'}, 200

    return app

# Create app instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

