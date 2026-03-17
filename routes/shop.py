from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
from models import Product, Category, Review, ReviewImage, Order, Banner, Wishlist
from forms import ReviewForm
from extensions import db

shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/')
def index():
    featured_products = Product.query.filter_by(is_active=True, is_featured=True).all()
    products = Product.query.filter_by(is_active=True).all()
    categories = Category.query.all()
    banners = Banner.query.filter_by(is_active=True).order_by(Banner.display_order).all()
    
    wishlist_product_ids = []
    if current_user.is_authenticated:
        wishlist_product_ids = [w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()]
        
    return render_template('shop/index.html', 
                           featured_products=featured_products,
                           products=products, 
                           categories=categories, 
                           banners=banners,
                           wishlist_product_ids=wishlist_product_ids)

@shop_bp.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    if not product.is_active:
        return render_template('errors/404.html'), 404
    
    form = ReviewForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('You must be logged in to post a review.', 'danger')
            return redirect(url_for('auth.login', next=request.url))
            
        review = Review(
            user_id=current_user.id,
            product_id=product.id,
            rating=int(form.rating.data),
            comment=form.comment.data
        )
        db.session.add(review)
        db.session.flush() # Get review.id
        
        # Handle Images (Supabase)
        files = request.files.getlist(form.photos.name)
        if files:
            from supabase_utils import upload_to_supabase
            for file in files:
                if file and file.filename:
                    supabase_url = upload_to_supabase(file, folder='reviews')
                    if supabase_url:
                        review_image = ReviewImage(
                            review_id=review.id,
                            image_url=supabase_url
                        )
                        db.session.add(review_image)
                    else:
                        flash(f"Failed to upload {file.filename} to Supabase.", 'warning')
        
        db.session.commit()
        flash('Review submitted successfully!', 'success')
        return redirect(url_for('shop.product_detail', product_id=product.id))

    # Calculate average rating
    reviews = product.reviews
    avg_rating = 0
    if reviews:
        avg_rating = sum([r.rating for r in reviews]) / len(reviews)
    
    wishlist_product_ids = []
    if current_user.is_authenticated:
        wishlist_product_ids = [w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()]
    
    return render_template('shop/product_detail.html', 
                           product=product, 
                           form=form, 
                           reviews=reviews, 
                           avg_rating=avg_rating,
                           wishlist_product_ids=wishlist_product_ids)

@shop_bp.route('/category/<string:slug>')
def category_products(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    # Price filtering
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    query = Product.query.filter_by(category_id=category.id, is_active=True)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    sort = request.args.get('sort', 'default')
    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'rating':
        query = query.outerjoin(Review).group_by(Product.id).order_by(db.func.avg(Review.rating).desc())
    
    products = query.all()
    categories = Category.query.all()
    
    wishlist_product_ids = []
    if current_user.is_authenticated:
        wishlist_product_ids = [w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()]
        
    return render_template('shop/category_products.html', 
                           category=category, 
                           products=products, 
                           categories=categories,
                           wishlist_product_ids=wishlist_product_ids)

@shop_bp.route('/size-guide')
def size_guide():
    return render_template('shop/size_guide.html')

@shop_bp.route('/my-orders')
@login_required
def my_orders():
    """Display user's order history"""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('shop/my_orders.html', orders=orders)

@shop_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Display detailed order tracking information"""
    order = db.get_or_404(Order, order_id)
    # Ensure user can only see their own orders
    if order.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('shop.index'))
    return render_template('shop/order_detail.html', order=order)

@shop_bp.route('/search')
def search():
    """Search products by name or description"""
    query = request.args.get('q', '').strip()
    
    if not query:
        flash('Please enter a search term.', 'warning')
        return redirect(url_for('shop.index'))
    
    # Search in product name, description, and category name
    keywords = query.split()
    search_filters = []
    
    for word in keywords:
        search_term = f"%{word}%"
        search_filters.append(db.or_(
            Product.name.ilike(search_term),
            Product.description.ilike(search_term),
            Category.name.ilike(search_term)
        ))
    
    # Price filtering
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    filter_query = Product.query.join(Category).filter(
        db.and_(*search_filters),
        Product.is_active == True
    )
    
    if min_price is not None:
        filter_query = filter_query.filter(Product.price >= min_price)
    if max_price is not None:
        filter_query = filter_query.filter(Product.price <= max_price)
    
    sort = request.args.get('sort', 'default')
    if sort == 'price_low':
        filter_query = filter_query.order_by(Product.price.asc())
    elif sort == 'price_high':
        filter_query = filter_query.order_by(Product.price.desc())
    elif sort == 'rating':
        filter_query = filter_query.outerjoin(Review).group_by(Product.id, Category.name).order_by(db.func.avg(Review.rating).desc())

    products = filter_query.all()
    
    categories = Category.query.all()
    
    wishlist_product_ids = []
    if current_user.is_authenticated:
        wishlist_product_ids = [w.product_id for w in Wishlist.query.filter_by(user_id=current_user.id).all()]
        
    return render_template('shop/search_results.html', 
                          products=products, 
                          query=query, 
                          categories=categories,
                          wishlist_product_ids=wishlist_product_ids)

@shop_bp.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
def toggle_wishlist(product_id):
    if not current_user.is_authenticated:
        return jsonify({'status': 'unauthorized', 'message': 'Please login to add to wishlist'}), 401
    
    product = db.get_or_404(Product, product_id)
    wishlist_item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()
        return jsonify({'status': 'removed', 'message': 'Removed from wishlist'})
    else:
        new_wishlist = Wishlist(user_id=current_user.id, product_id=product.id)
        db.session.add(new_wishlist)
        db.session.commit()
        return jsonify({'status': 'added', 'message': 'Added to wishlist'})

@shop_bp.route('/wishlist')
@login_required
def wishlist():
    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
    # Extract products from wishlist items
    products = [item.product for item in wishlist_items]
    categories = Category.query.all()
    
    wishlist_product_ids = [p.id for p in products]
    
    return render_template('shop/wishlist.html', 
                           products=products, 
                           categories=categories,
                           wishlist_product_ids=wishlist_product_ids)

@shop_bp.route('/review/delete/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    """Allow review owner or admin to delete a review."""
    from models import Review
    review = db.get_or_404(Review, review_id)
    product_id = review.product_id

    if review.user_id != current_user.id and not current_user.is_admin:
        flash('You are not authorized to delete this review.', 'danger')
        return redirect(url_for('shop.product_detail', product_id=product_id))

    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully.', 'success')
    return redirect(url_for('shop.product_detail', product_id=product_id))
