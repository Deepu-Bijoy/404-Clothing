from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import Product, Category, Order, User, Review, OrderItem, Banner
from extensions import db
from sqlalchemy import func
import os
from werkzeug.utils import secure_filename
from supabase_utils import upload_to_supabase, delete_from_supabase

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('shop.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    products_count = Product.query.filter_by(is_active=True).count()
    orders_count = Order.query.count()
    users_count = User.query.count()
    
    # Analytics Data
    products = Product.query.filter_by(is_active=True).all()
    
    product_names = []
    product_sales = []
    product_ratings = []
    
    top_seller = None
    max_sales = 0
    top_seller_revenue = 0
    
    for product in products:
        product_names.append(product.name)
        
        # Calculate total units and revenue
        query_results = db.session.query(
            func.sum(OrderItem.quantity),
            func.sum(OrderItem.quantity * OrderItem.price)
        ).join(Order).filter(
            OrderItem.product_id == product.id,
            Order.status.in_(['Paid', 'Processing', 'Dispatched', 'Out for Delivery', 'Delivered'])
        ).first()
        
        sales = query_results[0] or 0
        revenue = query_results[1] or 0
        product_sales.append(sales)
        
        # Identify top seller
        if sales > max_sales:
            max_sales = sales
            top_seller = product
            top_seller_revenue = revenue
        
        # Calculate average rating
        avg_rating = db.session.query(func.avg(Review.rating)).filter(
            Review.product_id == product.id
        ).scalar() or 0
        product_ratings.append(round(float(avg_rating), 1))
    
    top_seller_rating = 0
    if top_seller:
        top_seller_rating = db.session.query(func.avg(Review.rating)).filter(
            Review.product_id == top_seller.id
        ).scalar() or 0
        top_seller_rating = round(float(top_seller_rating), 1)

    return render_template('admin/dashboard.html', 
                           products_count=products_count, 
                           orders_count=orders_count, 
                           users_count=users_count,
                           product_names=product_names,
                           product_sales=product_sales,
                           product_ratings=product_ratings,
                           top_seller=top_seller,
                           top_sales_count=max_sales,
                           top_seller_revenue=top_seller_revenue,
                           top_seller_rating=top_seller_rating)

@admin_bp.route('/products')
@login_required
@admin_required
def products():
    products = Product.query.filter_by(is_active=True).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@admin_bp.route('/product/add', methods=['POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))
        category_id = int(request.form.get('category_id'))
        is_featured = 'is_featured' in request.form
        
        image_urls = []
        
        # 2. Handle File Uploads
        if 'image_files' in request.files:
            files = request.files.getlist('image_files')
            for file in files:
                if file and file.filename:
                    # Enforce Supabase Upload
                    supabase_url = upload_to_supabase(file, folder='products')
                    
                    if supabase_url:
                        image_urls.append(supabase_url)
                    else:
                        flash(f"Failed to upload {file.filename} to Supabase. Product creation aborted.", 'danger')
                        return redirect(url_for('admin.products'))
        
        # First URL is the main image
        main_image_url = image_urls[0] if image_urls else None
        
        product = Product(name=name, description=description, price=price, stock=stock, category_id=category_id, image_url=main_image_url, is_featured=is_featured)
        db.session.add(product)
        db.session.flush() # Get ID
        
        # Add all images to ProductImage table
        from models import ProductImage # Lazy import to avoid circular dep if any
        for url in image_urls:
            p_img = ProductImage(product_id=product.id, image_url=url)
            db.session.add(p_img)
            
        db.session.commit()
        flash('Product added.', 'success')
        return redirect(url_for('admin.products'))

@admin_bp.route('/category/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    name = request.form.get('name')
    slug = name.lower().replace(' ', '-')
    
    if Category.query.filter_by(slug=slug).first():
       flash('Category exists', 'warning')
    else:
        image_url = None
        if 'category_image' in request.files:
            file = request.files['category_image']
            if file and file.filename:
                # Enforce Supabase
                supabase_url = upload_to_supabase(file, folder='categories')
                if supabase_url:
                    image_url = supabase_url
                else:
                    flash("Failed to upload category image to Supabase.", 'danger')
                    return redirect(url_for('admin.products'))

        category = Category(name=name, slug=slug, image_url=image_url)
        db.session.add(category)
        db.session.commit()
        flash('Category added', 'success')
        
    return redirect(url_for('admin.products'))

@admin_bp.route('/category/edit/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def edit_category(category_id):
    category = db.get_or_404(Category, category_id)
    name = request.form.get('name')
    category.name = name
    category.slug = name.lower().replace(' ', '-')
    
    if 'category_image' in request.files:
        file = request.files['category_image']
        if file and file.filename:
            # Delete old image if it exists
            if category.image_url:
                if 'supabase.co' in category.image_url:
                    delete_from_supabase(category.image_url)
                else:
                    old_filename = category.image_url.split('/')[-1]
                    old_path = os.path.join(current_app.root_path, 'static', 'uploads', 'categories', old_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
            
            # Enforce Supabase
            supabase_url = upload_to_supabase(file, folder='categories')
            if supabase_url:
                category.image_url = supabase_url
            else:
                flash("Failed to upload new category image to Supabase.", 'danger')
                return redirect(url_for('admin.products'))
    
    db.session.commit()
    flash('Category updated', 'success')
    return redirect(url_for('admin.products'))

@admin_bp.route('/category/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = db.get_or_404(Category, category_id)
    
    try:
        # 1. DELETE PRODUCT IMAGES
        for product in category.products:
            if product.image_url:
                if 'supabase.co' in product.image_url:
                    delete_from_supabase(product.image_url)
                else:
                    filename = product.image_url.split('/')[-1]
                    file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'products', filename)
                    if os.path.exists(file_path):
                        try: os.remove(file_path)
                        except Exception: pass
            
            for p_img in product.images:
                if p_img.image_url:
                    if 'supabase.co' in p_img.image_url:
                        delete_from_supabase(p_img.image_url)
                    else:
                        filename = p_img.image_url.split('/')[-1]
                        file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'products', filename)
                        if os.path.exists(file_path):
                            try: os.remove(file_path)
                            except Exception: pass
        
        # 2. DELETE CATEGORY IMAGE
        if category.image_url:
            if 'supabase.co' in category.image_url:
                delete_from_supabase(category.image_url)
            else:
                filename = category.image_url.split('/')[-1]
                file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'categories', filename)
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except Exception: pass
                
        db.session.delete(category)
        db.session.commit()
        flash('Category and all associated products and assets deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')
        
    return redirect(url_for('admin.products'))

@admin_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
         flash('Product not found.', 'danger')
         return redirect(url_for('admin.products'))
    
    try:
        if product.image_url:
            if 'supabase.co' in product.image_url:
                delete_from_supabase(product.image_url)
            else:
                filename = product.image_url.split('/')[-1]
                file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'products', filename)
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except Exception: pass
        
        for p_img in product.images:
            if p_img.image_url:
                if 'supabase.co' in p_img.image_url:
                    delete_from_supabase(p_img.image_url)
                else:
                    filename = p_img.image_url.split('/')[-1]
                    file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'products', filename)
                    if os.path.exists(file_path):
                        try: os.remove(file_path)
                        except Exception: pass
        
        db.session.delete(product)
        db.session.commit()
        flash('Product and associated assets permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product.', 'danger')
    
    return redirect(url_for('admin.products'))

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/order/print/<int:order_id>')
@login_required
@admin_required
def print_order(order_id):
    order = db.get_or_404(Order, order_id)
    return render_template('admin/print_order.html', order=order)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/user/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'Admin status for {user.name} updated.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Check if user has orders
    if user.orders:
        flash('Cannot delete user with existing orders. Consider deactivating instead (feature coming soon).', 'warning')
        return redirect(url_for('admin.users'))
        
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} deleted.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/banners')
@login_required
@admin_required
def banners():
    banners = Banner.query.order_by(Banner.display_order).all()
    return render_template('admin/banners.html', banners=banners)

@admin_bp.route('/banner/add', methods=['POST'])
@login_required
@admin_required
def add_banner():
    title = request.form.get('title')
    subtitle = request.form.get('subtitle')
    button_text = request.form.get('button_text')
    button_link = request.form.get('button_link')
    display_order = int(request.form.get('display_order', 0))
    
    image_path = None
    if 'banner_image' in request.files:
        file = request.files['banner_image']
        if file and file.filename:
            # Enforce Supabase
            supabase_url = upload_to_supabase(file, folder='banners')
            if supabase_url:
                image_path = supabase_url
            else:
                flash("Failed to upload banner to Supabase.", 'danger')
                return redirect(url_for('admin.banners'))
    
    if image_path:
        banner = Banner(
            title=title,
            subtitle=subtitle,
            button_text=button_text,
            button_link=button_link,
            image_path=image_path,
            display_order=display_order
        )
        db.session.add(banner)
        db.session.commit()
        flash('Banner added.', 'success')
    else:
        flash('Banner image is required.', 'danger')
        
    return redirect(url_for('admin.banners'))

@admin_bp.route('/banner/edit/<int:banner_id>', methods=['POST'])
@login_required
@admin_required
def edit_banner(banner_id):
    banner = db.get_or_404(Banner, banner_id)
    banner.title = request.form.get('title')
    banner.subtitle = request.form.get('subtitle')
    banner.button_text = request.form.get('button_text')
    banner.button_link = request.form.get('button_link')
    banner.display_order = int(request.form.get('display_order', 0))
    banner.is_active = 'is_active' in request.form
    
    if 'banner_image' in request.files:
        file = request.files['banner_image']
        if file and file.filename:
            # Delete old image if it exists
            if banner.image_path:
                if 'supabase.co' in banner.image_path:
                    delete_from_supabase(banner.image_path)
                else:
                    old_filename = banner.image_path.split('/')[-1]
                    old_path = os.path.join(current_app.root_path, 'static', 'uploads', 'banners', old_filename)
                    if os.path.exists(old_path):
                        try: os.remove(old_path)
                        except Exception: pass
            
            # Enforce Supabase
            supabase_url = upload_to_supabase(file, folder='banners')
            if supabase_url:
                banner.image_path = supabase_url
            else:
                flash("Failed to upload new banner image to Supabase.", 'danger')
                return redirect(url_for('admin.banners'))
            
    db.session.commit()
    flash('Banner updated.', 'success')
    return redirect(url_for('admin.banners'))

@admin_bp.route('/banner/delete/<int:banner_id>', methods=['POST'])
@login_required
@admin_required
def delete_banner(banner_id):
    banner = db.get_or_404(Banner, banner_id)
    
    # Delete image file
    if banner.image_path:
        if 'supabase.co' in banner.image_path:
            delete_from_supabase(banner.image_path)
        else:
            filename = banner.image_path.split('/')[-1]
            file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'banners', filename)
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except Exception: pass
                
    db.session.delete(banner)
    db.session.commit()
    flash('Banner deleted.', 'success')
    return redirect(url_for('admin.banners'))

@admin_bp.route('/product/edit/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = db.get_or_404(Product, product_id)
    
    product.name = request.form.get('name')
    product.description = request.form.get('description')
    product.price = float(request.form.get('price'))
    product.stock = int(request.form.get('stock'))
    product.category_id = int(request.form.get('category_id'))
    product.is_featured = 'is_featured' in request.form
    
    # Handle new image uploads
    if 'image_files' in request.files:
        files = request.files.getlist('image_files')
        new_images = []
        for file in files:
            if file and file.filename:
                # 1. Try Supabase
                supabase_url = upload_to_supabase(file, folder='products')
                if supabase_url:
                    new_images.append(supabase_url)
                else:
                    # 2. Fallback
                    filename = secure_filename(file.filename)
                    import uuid
                    filename = f"{uuid.uuid4().hex[:8]}_{filename}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
                    os.makedirs(upload_dir, exist_ok=True)
                    file.save(os.path.join(upload_dir, filename))
                    image_url = url_for('static', filename=f'uploads/products/{filename}')
                    new_images.append(image_url)
        
        if new_images:
            from models import ProductImage
            for url in new_images:
                p_img = ProductImage(product_id=product.id, image_url=url)
                db.session.add(p_img)
            
            # If product had no main image, set the first new one as main
            if not product.image_url:
                product.image_url = new_images[0]
                
    db.session.commit()
    flash('Product updated.', 'success')
    return redirect(url_for('admin.products'))

@admin_bp.route('/product/image/delete/<int:image_id>', methods=['POST'])
@login_required
@admin_required
def delete_product_image(image_id):
    from models import ProductImage
    image = db.get_or_404(ProductImage, image_id)
    product_id = image.product_id
    
    # Delete file from filesystem or Supabase
    if image.image_url:
        if 'supabase.co' in image.image_url:
            delete_from_supabase(image.image_url)
        else:
            filename = image.image_url.split('/')[-1]
            file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'products', filename)
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except Exception: pass
            
    # If this was the product's main image, update Product.image_url
    product = Product.query.get(product_id)
    if product and product.image_url == image.image_url:
        # Try to find another image to be the main one
        other_image = ProductImage.query.filter(ProductImage.product_id == product_id, ProductImage.id != image_id).first()
        product.image_url = other_image.image_url if other_image else None
        
    db.session.delete(image)
    db.session.commit()
    flash('Image removed from gallery.', 'success')
    return redirect(url_for('admin.products'))
