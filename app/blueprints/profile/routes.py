import os
import time
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from app.models import db, User, Role
from app.constants import Constants
from app.utils.decorators import login_required
from config import Config

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/', methods=['GET'])
@login_required
def index():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)

    # Determine dynamic role name matching PHP ProfileController::index
    role_id = user.role_id
    if role_id is None:
        role_id = Constants.USER_ACCESS_LEVELS.get(user_id)
        if role_id is None:
            if user.account_type == 1:
                role_id = Constants.USER_ROLE_ADMIN
            else:
                role_id = Constants.USER_ROLE_MEDIA_TAGGING

    role_row = Role.query.get(role_id) if role_id else None
    role_name = role_row.name if role_row else Constants.USER_ROLES.get(role_id, 'Unknown')
    badge_class = 'bg-primary-subtle text-primary' if (user.account_type == 1 or role_name == 'Admin') else 'bg-secondary-subtle text-secondary'

    return render_template(
        'profile/index.html',
        user=user,
        roleName=role_name,
        badgeClass=badge_class
    )

@profile_bp.route('/update', methods=['POST'])
@login_required
def update():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)

    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    username = (request.form.get('username') or '').strip()

    # Validation
    if not first_name or not last_name or not username:
        flash('First name, last name, and username are required.', 'error')
        return redirect(url_for('profile.index'))

    # Check unique username across other users
    existing = User.query.filter(User.username == username, User.id != user_id).first()
    if existing:
        flash('Username is already taken by another user.', 'error')
        return redirect(url_for('profile.index'))

    user.first_name = first_name
    user.last_name = last_name
    user.username = username

    remove_photo_flag = request.form.get('remove_photo')

    # Profile photo upload handling
    photo_file = request.files.get('profile_photo')
    upload_path = Config.PROFILE_UPLOAD_DIR
    os.makedirs(upload_path, exist_ok=True)

    if photo_file and photo_file.filename:
        allowed_mimes = ['image/jpg', 'image/jpeg', 'image/png', 'image/gif', 'image/webp']
        mime_type = photo_file.mimetype or ''

        if mime_type.lower() not in allowed_mimes:
            flash('Invalid photo file format. Allowed formats: JPG, JPEG, PNG, GIF, WEBP.', 'error')
            return redirect(url_for('profile.index'))

        # Check file size (2MB limit)
        photo_file.seek(0, os.SEEK_END)
        size = photo_file.tell()
        photo_file.seek(0)
        if size > 2 * 1024 * 1024:
            flash('The profile photo file size exceeds the 2MB limit.', 'error')
            return redirect(url_for('profile.index'))

        # Delete old photo if exists
        if user.profile_photo:
            old_file = os.path.join(upload_path, os.path.basename(user.profile_photo))
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except Exception:
                    pass

        # Generate unique safe filename
        ext = os.path.splitext(secure_filename(photo_file.filename))[1]
        new_name = f"user_{user.id}_{int(time.time())}{ext}"
        save_dest = os.path.join(upload_path, new_name)
        photo_file.save(save_dest)
        user.profile_photo = new_name
        session['profile_photo'] = new_name

    elif remove_photo_flag == '1':
        if user.profile_photo:
            old_file = os.path.join(upload_path, os.path.basename(user.profile_photo))
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except Exception:
                    pass
        user.profile_photo = None
        session.pop('profile_photo', None)

    # Password update check
    current_pwd = request.form.get('current_password', '')
    new_pwd = request.form.get('new_password', '')
    confirm_pwd = request.form.get('confirm_password', '')

    if current_pwd or new_pwd or confirm_pwd:
        if not current_pwd:
            flash('Please enter your current password to set a new password.', 'error')
            return redirect(url_for('profile.index'))

        if not new_pwd or not confirm_pwd:
            flash('Please enter and confirm your new password.', 'error')
            return redirect(url_for('profile.index'))

        if not user.check_password(current_pwd):
            flash('Incorrect current password.', 'error')
            return redirect(url_for('profile.index'))

        if new_pwd != confirm_pwd:
            flash('New password and confirm password do not match.', 'error')
            return redirect(url_for('profile.index'))

        user.set_password(new_pwd)

    db.session.commit()

    # Synchronize session data
    session['username'] = user.username
    session['user_name'] = f"{user.first_name} {user.last_name}"
    if user.profile_photo:
        session['profile_photo'] = user.profile_photo

    flash('Profile updated successfully.', 'success')
    return redirect(url_for('profile.index'))
