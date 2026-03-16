# last deploy sync: 2026-03-15 15:35
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
    # Migrate database if needed
    try:
        from sqlalchemy import text
        is_postgres = 'postgresql' in str(db.engine.url).lower()
        print(f"DEBUG: Starting DB migration. Database type: {'PostgreSQL' if is_postgres else 'SQLite'}")
        
        with db.engine.connect() as conn:
            # 1. Postgres specific (hash type update)
            if is_postgres:
                try:
                    conn.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE TEXT'))
                    conn.commit()
                    print("DEBUG: Successfully updated password_hash type to TEXT")
                except Exception as e:
                    conn.rollback()
                    print(f"DEBUG: Skipping password_hash type update (likely already TEXT): {e}")

            # 2. Add missing columns safely — each in its own transaction
            columns = [
                ('security_question', 'VARCHAR(200)'),
                ('security_answer_hash', 'VARCHAR(128)'),
                ('phone_number', 'VARCHAR(20)')
            ]
            for column, col_type in columns:
                try:
                    print(f"DEBUG: Attempting to add column {column}...")
                    if is_postgres:
                        # PostgreSQL supports IF NOT EXISTS
                        conn.execute(text(f'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS {column} {col_type}'))
                    else:
                        # SQLite does not support IF NOT EXISTS for ALTER TABLE
                        conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {column} {col_type}'))
                    conn.commit()
                    print(f"DEBUG: Successfully ensured column {column} exists")
                except Exception as e:
                    conn.rollback()  # Must rollback so next statement can run
                    print(f"DEBUG: Skip adding {column} (likely already exists or error): {e}")
    except Exception as e:
        print(f"DEBUG: Migration error: {e}")
        pass
    
    # CRITICAL: Dispose of the engine to close startup connections
    # This prevents the "SSL error: decryption failed" error in workers
    db.engine.dispose()

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
    import sys
    port = 5000
    if '--port' in sys.argv:
        port = int(sys.argv[sys.argv.index('--port') + 1])
    app.run(debug=True, port=port)
