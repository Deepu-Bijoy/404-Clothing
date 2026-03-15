from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from models import User
from extensions import db, mail
from flask_mail import Message

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(name=form.name.data, email=form.email.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Registration successful!', 'success')
        return redirect(url_for('shop.index'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('shop.index'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('shop.index'))

def send_reset_email(user):
    print(f"DEBUG: Preparing email for {user.email}")
    token = user.get_reset_token()
    reset_url = url_for('auth.reset_token', token=token, _external=True)
    msg = Message('Password Reset Request',
                  sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@404clothing.com'),
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    print(f"DEBUG: Attempting to send via {current_app.config.get('MAIL_SERVER')}:{current_app.config.get('MAIL_PORT')}")
    try:
        mail.send(msg)
        print("DEBUG: mail.send(msg) finished successfully")
        return True
    except Exception as e:
        print(f"DEBUG: mail.send(msg) FAILED: {e}")
        print(f"RESET LINK (FOR DEBUGGING): {reset_url}")
        return False

@auth_bp.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        print(f"DEBUG: Processing reset request for {form.email.data}")
        try:
            user = User.query.filter_by(email=form.email.data).first()
            print(f"DEBUG: User lookup finished. Found user: {user is not None}")
            if user:
                token = user.get_reset_token()
                print("DEBUG: Token generated.")
                if send_reset_email(user):
                    print("DEBUG: send_reset_email returned True")
                    flash('Password reset link sent to your email', 'info')
                else:
                    print("DEBUG: send_reset_email returned False")
                    flash('Password reset link sent to your email', 'info')
                return redirect(url_for('auth.login'))
            else:
                print("DEBUG: No user found, redirecting...")
                flash('Password reset link sent to your email', 'info')
                return redirect(url_for('auth.login'))
        except Exception as e:
            print(f"DEBUG: CRASH in reset_request: {e}")
            raise e
    return render_template('auth/reset_request.html', title='Reset Password', form=form)

@auth_bp.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid or expired reset link', 'warning')
        return redirect(url_for('auth.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Password successfully updated', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', title='Reset Password', form=form)
