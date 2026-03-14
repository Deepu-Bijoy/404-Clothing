from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import CartItem, Order, OrderItem
from extensions import db
import razorpay

checkout_bp = Blueprint('checkout', __name__)

@checkout_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop.index'))
        
    # Filter out invalid or inactive items
    valid_cart_items = [item for item in cart_items if item.product and item.product.is_active]
    
    if not valid_cart_items:
        flash('Your cart is empty or contains unavailable items.', 'warning')
        return redirect(url_for('shop.index'))
        
    subtotal = sum(item.product.price * item.quantity for item in valid_cart_items)
    shipping_fee = 50.0
    total_price = subtotal + shipping_fee
    
    # Stock Check
    for item in valid_cart_items:
        if item.quantity > item.product.stock:
            flash(f'Sorry, {item.product.name} is out of stock (Available: {item.product.stock})', 'danger')
            return redirect(url_for('cart.view_cart'))
    
    from forms import CheckoutForm
    from flask import session
    
    form = CheckoutForm()
    payment_ready = False
    razorpay_order_id = None
    
    if form.validate_on_submit():
        # Save address to session
        session['checkout_address'] = {
            'full_name': form.full_name.data,
            'phone_number': form.phone_number.data,
            'address_line1': form.address_line1.data,
            'address_line2': form.address_line2.data,
            'city': form.city.data,
            'state': form.state.data,
            'postal_code': form.postal_code.data,
            'country': form.country.data
        }
        
        try:
            # Check for keys first
            key_id = current_app.config.get('RAZORPAY_KEY_ID')
            key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
            
            if not key_id or not key_secret:
                raise ValueError("Razorpay API Keys are missing in server configuration.")

            # Create Razorpay Order
            client = razorpay.Client(auth=(key_id, key_secret))
            
            razorpay_order_data = {
                'amount': int(total_price * 100), # Amount in paise
                'currency': 'INR',
                'payment_capture': 1
            }
            
            razorpay_order = client.order.create(data=razorpay_order_data)
            razorpay_order_id = razorpay_order['id']
            payment_ready = True
            current_app.logger.info(f"Razorpay Order Created: {razorpay_order_id} for user {current_user.id}")
        except Exception as e:
            error_msg = str(e)
            current_app.logger.error(f"Razorpay Error: {error_msg}")
            if "Authentication failed" in error_msg or "API Keys" in error_msg:
                flash(f"Payment Gateway Error: Authentication failed. Please verify RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET on Render dashboard.", 'danger')
            else:
                flash(f"Payment Gateway Error: {error_msg}", 'danger')
            payment_ready = False
            razorpay_order_id = None
    
    # Pre-fill form if address exists in session (optional but good UX)
    if not payment_ready and 'checkout_address' in session:
        addr = session['checkout_address']
        form.full_name.data = addr.get('full_name')
        form.phone_number.data = addr.get('phone_number')
        form.address_line1.data = addr.get('address_line1')
        form.address_line2.data = addr.get('address_line2')
        form.city.data = addr.get('city')
        form.state.data = addr.get('state')
        form.postal_code.data = addr.get('postal_code')
        form.country.data = addr.get('country')

    return render_template('checkout/index.html', 
                           cart_items=valid_cart_items, 
                           subtotal=subtotal,
                           shipping_fee=shipping_fee,
                           total_price=total_price,
                           form=form,
                           payment_ready=payment_ready,
                           razorpay_order_id=razorpay_order_id,
                           razorpay_key_id=current_app.config['RAZORPAY_KEY_ID'])
