from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import db, User, Role, RolePermission
from app.constants import Constants

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/auth/login', methods=['GET', 'POST'])
def login():
    if session.get('is_logged_in'):
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username, is_active=1).first()

        if user and user.check_password(password):
            # Determine role & permissions
            role_id = user.role_id
            if role_id is None:
                role_id = Constants.USER_ACCESS_LEVELS.get(user.id)
                if role_id is None:
                    role_id = Constants.USER_ROLE_ADMIN if user.account_type == 1 else Constants.USER_ROLE_MEDIA_TAGGING

            role = Role.query.get(role_id)
            role_name = role.name if role else Constants.USER_ROLES.get(role_id, 'User')

            # Fetch dynamic permissions from DB
            db_perms = RolePermission.query.filter_by(role_id=role_id).all()
            permissions = {}
            if db_perms:
                for p in db_perms:
                    permissions[p.permission_key] = bool(p.permission_value)
                if 'reports' not in permissions:
                    permissions['reports'] = (role_id in [1, 3, 4])
            else:
                permissions = Constants.USER_ROLES_ACCESS.get(role_id, {})

            # Save in session
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_name'] = user.full_name
            session['account_type'] = user.account_type
            session['user_role'] = role_id
            session['user_role_name'] = role_name
            session['permissions'] = permissions
            session['profile_photo'] = user.profile_photo
            session['is_logged_in'] = True

            flash(f"Welcome back, {user.first_name or user.username}!", 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard.index'))

        flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))
