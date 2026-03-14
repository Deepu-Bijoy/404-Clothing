# last deploy sync: 2026-03-14 21:03
import os
from flask import Flask, render_template
from config import Config
from extensions import db, login_manager, csrf
from models import User

app = Flask(__name__)
app.config.from_object(Config)

# Disable template caching for development
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
from extensions import mail
mail.init_app(app)

# Register Blueprints
from routes.auth import auth_bp
from routes.shop import shop_bp
from routes.cart import cart_bp
from routes.checkout import checkout_bp
from routes.payment import payment_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(shop_bp) # Main shop routes at root
app.register_blueprint(cart_bp, url_prefix='/cart')
app.register_blueprint(checkout_bp, url_prefix='/checkout')
app.register_blueprint(payment_bp, url_prefix='/payment')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Create Database Tables if not exist
with app.app_context():
    db.create_all()
    # Migrate database if needed
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            # PostgreSQL specific migration - strictly check if we are on Postgres
            if 'postgresql' in str(db.engine.url).lower():
                try:
                    conn.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE TEXT'))
                    conn.commit()
                except Exception:
                    pass
                
                # New Migration for is_active
                try:
                    conn.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE'))
                    conn.commit()
                except Exception:
                    pass
            
            conn.commit()
    except Exception as e:
        # Silencing startup errors for local SQLite dev
        pass

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_globals():
    from models import Category, CartItem, Wishlist
    from flask_login import current_user
    categories = Category.query.all()
    cart_count = 0
    wishlist_product_ids = []
    if current_user.is_authenticated:
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        wishlist_product_ids = [w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()]
    return dict(categories=categories, cart_count=cart_count, wishlist_product_ids=wishlist_product_ids)

if __name__ == '__main__':
    # Only enable debug if explicitly set or in development
    is_debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=is_debug)
