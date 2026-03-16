from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from models import User
from extensions import db
from itsdangerous import URLSafeTimedSerializer as Serializer

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data, 
            email=form.email.data,
            phone_number=form.phone_number.data
        )
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

import time

from forms import SecurityAnswerForm

@auth_bp.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()
        if user:
            # Triple check: Email, Name, and Phone Number must match
            if user.name.strip().lower() == form.name.data.strip().lower() and \
               user.phone_number.strip() == form.phone_number.data.strip():
                token = user.get_reset_token()
                # In a real app we'd send email, here we just redirect with token for demo/simplicity or follow previous flow
                flash('Verification successful. Please set your new password.', 'success')
                return redirect(url_for('auth.reset_token', token=token))
            else:
                flash('Verification failed. Name or Phone Number does not match our records.', 'danger')
        else:
            flash('There is no account with that email.', 'danger')
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
