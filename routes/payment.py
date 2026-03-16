from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import razorpay
from datetime import datetime, timedelta
from models import Order, OrderItem, Payment, CartItem
from extensions import db
import time

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/verify', methods=['POST'])
@login_required
def create_order_after_payment(user_id, total_price, payment_id, razorpay_order_id, shipping_fee=50.0, gateway='Razorpay'):
    """Helper to handle database operations after payment success"""
    from flask import session
    address_data = session.get('checkout_address')
    
    if not address_data:
        return None, "Address details missing from session."

    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    if not cart_items:
        return None, "Your cart is empty."

    # Stock Check
    for item in cart_items:
        if item.quantity > item.product.stock:
            return None, f"{item.product.name} went out of stock."

    estimated_delivery = datetime.utcnow() + timedelta(days=5)
    
    new_order = Order(
        user_id=user_id,
        total_price=total_price,
        shipping_fee=shipping_fee,
        status='Processing',
        payment_status='Paid',
        full_name=address_data.get('full_name'),
        phone_number=address_data.get('phone_number'),
        address_line1=address_data.get('address_line1'),
        address_line2=address_data.get('address_line2'),
        city=address_data.get('city'),
        state=address_data.get('state'),
        postal_code=address_data.get('postal_code'),
        country=address_data.get('country'),
        estimated_delivery_date=estimated_delivery
    )
    db.session.add(new_order)
    db.session.flush()
    
    tracking_num = f"TRK{new_order.id}{int(time.time() % 100000)}"
    new_order.tracking_number = tracking_num
    
    for item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.product.price,
            size=item.size
        )
        db.session.add(order_item)
        item.product.stock -= item.quantity
        
    payment = Payment(
        order_id=new_order.id,
        payment_gateway=gateway,
        payment_id=payment_id,
        razorpay_order_id=razorpay_order_id,
        amount=total_price,
        status='Success'
    )
    db.session.add(payment)
    
    for item in cart_items:
        db.session.delete(item)
        
    db.session.commit()
    session.pop('checkout_address', None)
    current_app.logger.info(f"Order created successfully: ID {new_order.id} for user {user_id}")
    return new_order, None

@payment_bp.route('/verify', methods=['POST'])
@login_required
def verify():
    try:
        payment_id = request.form.get('razorpay_payment_id')
        razorpay_order_id = request.form.get('razorpay_order_id')
        signature = request.form.get('razorpay_signature')
        
        client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        client.utility.verify_payment_signature(params_dict)
        
        # Idempotency Check
        existing_payment = Payment.query.filter_by(payment_id=payment_id).first()
        if existing_payment:
            flash('Payment already processed.', 'info')
            return redirect(url_for('payment.success', order_id=existing_payment.order_id))

        # Calculate total price for verification
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        shipping_fee = 50.0
        total_price = subtotal + shipping_fee

        order, error = create_order_after_payment(current_user.id, total_price, payment_id, razorpay_order_id, shipping_fee=shipping_fee)
        if error:
            flash(error, 'danger')
            return redirect(url_for('checkout.index'))
            
        flash('Payment Successful! Order Placed.', 'success')
        return redirect(url_for('payment.success', order_id=order.id))
        
    except razorpay.errors.SignatureVerificationError as e:
        current_app.logger.error(f"Razorpay Signature Verification Failed: {str(e)}")
        flash('Payment Verification Failed: Invalid Signature.', 'danger')
        return redirect(url_for('checkout.index'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Payment Error: {str(e)}", exc_info=True)
        flash(f'An error occurred during payment processing: {str(e)}', 'danger')
        return redirect(url_for('checkout.index'))

@payment_bp.route('/success/<int:order_id>')
@login_required
def success(order_id):
    order = db.get_or_404(Order, order_id)
    if order.user_id != current_user.id:
        return redirect(url_for('shop.index'))
    return render_template('payment/success.html', order=order)

@payment_bp.route('/demo-otp')
@login_required
def demo_otp():
    """Show the simulated Netbanking/OTP page"""
    from flask import session
    if 'checkout_address' not in session:
        flash('Please complete checkout first.', 'warning')
        return redirect(url_for('checkout.index'))
    
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping_fee = 50.0
    total_price = subtotal + shipping_fee
    return render_template('payment/demo_otp.html', total_price=total_price)

@payment_bp.route('/verify-demo-otp', methods=['POST'])
@login_required
def verify_demo_otp():
    """Verify the simulated OTP and place order"""
    otp = request.form.get('otp')
    if otp != '123456':
        flash('Invalid OTP. Please enter 123456 for demo.', 'danger')
        return redirect(url_for('payment.demo_otp'))
    
    # Process order
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping_fee = 50.0
    total_price = subtotal + shipping_fee
    
    import uuid
    payment_id = f"pay_demo_{uuid.uuid4().hex[:8]}"
    
    order, error = create_order_after_payment(current_user.id, total_price, payment_id, "demo_order", shipping_fee=shipping_fee, gateway='Demo-Netbanking')
    if error:
        flash(error, 'danger')
        return redirect(url_for('checkout.index'))
        
    flash('Demo Payment Successful! Order Placed.', 'success')
    return redirect(url_for('payment.success', order_id=order.id))
