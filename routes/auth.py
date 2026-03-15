from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from models import User
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
            security_question=form.security_question.data
        )
        new_user.set_password(form.password.data)
        new_user.set_security_answer(form.security_answer.data)
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
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if not user.security_question:
                flash('Your account does not have a security question set. Please contact support.', 'danger')
                return redirect(url_for('auth.login'))
            return redirect(url_for('auth.reset_verify', email=user.email))
        else:
            flash('There is no account with that email.', 'danger')
    return render_template('auth/reset_request.html', title='Reset Password', form=form)

@auth_bp.route("/reset_verify", methods=['GET', 'POST'])
def reset_verify():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    email = request.args.get('email')
    if not email:
        return redirect(url_for('auth.reset_request'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for('auth.reset_request'))
    
    form = SecurityAnswerForm()
    if form.validate_on_submit():
        if user.check_security_answer(form.answer.data):
            # Generate a temporary token for the reset page
            token = user.get_reset_token()
            return redirect(url_for('auth.reset_token', token=token))
        else:
            flash('Incorrect answer. Please try again.', 'danger')
            
    return render_template('auth/reset_verify.html', title='Verify Security Question', 
                           form=form, question=user.security_question)

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
