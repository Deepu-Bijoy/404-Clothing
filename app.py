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
    # Migrate password_hash column from VARCHAR(128) to TEXT if needed
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE TEXT'))
            # Auto-promote your account to admin
            conn.execute(text('UPDATE "user" SET is_admin = true WHERE email = :email'), {"email": "deepubijoy@gmail.com"})
            
            # Auto-populate banners if empty
            banner_count = conn.execute(text('SELECT COUNT(*) FROM banner')).scalar()
            if banner_count == 0:
                banners = [
                    {
                        "image_path": "https://images.unsplash.com/photo-1516826957135-700ede19c6ce?q=80&w=2000&auto=format&fit=crop",
                        "title": "Urban Essentials",
                        "subtitle": "Define your street signature.",
                        "button_text": "Shop Now",
                        "button_link": "/#collection",
                        "display_order": 1
                    },
                    {
                        "image_path": "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?q=80&w=2000&auto=format&fit=crop",
                        "title": "Premium Quality",
                        "subtitle": "Streetwear redefined for comfort.",
                        "button_text": "View Collection",
                        "button_link": "/#collection",
                        "display_order": 2
                    },
                    {
                        "image_path": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?q=80&w=2000&auto=format&fit=crop",
                        "title": "New Arrivals",
                        "subtitle": "The latest drops of the season.",
                        "button_text": "Explore",
                        "button_link": "/#collection",
                        "display_order": 3
                    }
                ]
                for b in banners:
                    conn.execute(text("""
                        INSERT INTO banner (image_path, title, subtitle, button_text, button_link, display_order, is_active, created_at)
                        VALUES (:image_path, :title, :subtitle, :button_text, :button_link, :display_order, true, NOW())
                    """), b)
            
            conn.commit()
    except Exception as e:
        print(f"Migration error: {e}")
        pass  # Already updated or table doesn't exist yet

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
