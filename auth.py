from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Team

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            if not user.approved:
                flash('Your account is pending approval by admin.')
                return redirect(url_for('auth.login'))
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        team_name = request.form['team']
        team = Team.query.filter_by(name=team_name).first()
        new_user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=hashed_pw,
            role=request.form['role'],
            team=team,
            approved=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please wait for admin approval.')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
