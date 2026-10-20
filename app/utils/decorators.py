from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_logged_in'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

from app.constants import Constants

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('is_logged_in'):
                return redirect(url_for('auth.login', next=request.url))
            
            # Superadmin / Admin accounts always have full access
            if session.get('account_type') == 1 or session.get('user_role') == Constants.USER_ROLE_ADMIN:
                return f(*args, **kwargs)

            permissions = session.get('permissions', {})
            has_perm = False
            if isinstance(permissions, dict):
                has_perm = bool(permissions.get(permission_name) or permissions.get('*'))
            elif isinstance(permissions, (list, tuple, set)):
                has_perm = (permission_name in permissions) or ('*' in permissions)

            # If permission is missing or False
            if not has_perm:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': f'Access denied: {permission_name}'}), 403
                flash(f'You do not have permission to access the {permission_name} section.', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
