from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Product, CartItem
from extensions import db

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    # Filter out orphaned cart items (where product was deleted)
    valid_cart_items = [item for item in cart_items if item.product and item.product.is_active]
    subtotal = sum(item.product.price * item.quantity for item in valid_cart_items)
    shipping_fee = 50.0 if valid_cart_items else 0.0
    total = subtotal + shipping_fee
    return render_template('cart/view_cart.html', cart_items=valid_cart_items, subtotal=subtotal, shipping_fee=shipping_fee, total=total)

@cart_bp.route('/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = db.get_or_404(Product, product_id)
    quantity = int(request.form.get('quantity', 1))
    
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
        
    db.session.commit()
    flash(f'{product.name} added to cart.', 'success')
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = db.get_or_404(CartItem, item_id)
    if cart_item.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('cart.view_cart'))
        
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/update/<int:item_id>', methods=['POST'])
@login_required
def update_quantity(item_id):
    cart_item = db.get_or_404(CartItem, item_id)
    if cart_item.user_id != current_user.id:
        return redirect(url_for('cart.view_cart'))
        
    quantity = int(request.form.get('quantity', 1))
    if quantity > 0:
        cart_item.quantity = quantity
        db.session.commit()
    else:
        db.session.delete(cart_item)
        db.session.commit()
        
    return redirect(url_for('cart.view_cart'))
