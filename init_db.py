from app import create_app
from extensions import db
from models import User, Category, Product

app = create_app()

with app.app_context():
    # Drop all and create to ensure schema is fresh
    db.drop_all()
    db.create_all()
    print("Database tables created.")

    # Create Admin User
    admin = User(name='Admin User', email='admin@example.com', is_admin=True)
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Create Regular User
    user = User(name='Test User', email='user@example.com', is_admin=False)
    user.set_password('user123')
    db.session.add(user)

    # Create Categories
    cat_men = Category(name='Men', slug='men')
    cat_women = Category(name='Women', slug='women')
    cat_kids = Category(name='Kids', slug='kids')
    
    db.session.add_all([cat_men, cat_women, cat_kids])
    db.session.commit()
    
    # Create Sample Products
    p1 = Product(name='Men T-Shirt', description='Cotton T-Shirt for Men', price=499.0, stock=50, category_id=cat_men.id, image_url='https://via.placeholder.com/400x400?text=Men+T-Shirt')
    p2 = Product(name='Women Dress', description='Floral Summer Dress', price=1499.0, stock=30, category_id=cat_women.id, image_url='https://via.placeholder.com/400x400?text=Women+Dress')
    p3 = Product(name='Kids Denim', description='Denim Jeans for Kids', price=899.0, stock=40, category_id=cat_kids.id, image_url='https://via.placeholder.com/400x400?text=Kids+Denim')
    
    db.session.add_all([p1, p2, p3])
    db.session.commit()
    
    print("Database initialized with sample data.")
    print("Admin: admin@example.com / admin123")
    print("User: user@example.com / user123")
