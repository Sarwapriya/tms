from flask import Blueprint, jsonify, request, session, redirect, url_for
from app.models import db, Notification, User
from app.constants import Constants
from app.utils.decorators import login_required
from app.utils.helpers import time_elapsed_string

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/')
@notifications_bp.route('/unread')
@notifications_bp.route('/get-unread')
@login_required
def get_unread():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not logged in.'})

    req_limit = request.args.get('limit')
    limit = None if req_limit == 'all' else int(req_limit or 15)

    q = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc())
    if limit:
        notifications = q.limit(limit).all()
    else:
        notifications = q.all()

    users_map = {u.id: u.name for u in User.query.all()}
    enriched = []
    unread_count = 0

    for n in notifications:
        if n.is_read == 0:
            unread_count += 1
        sender_name = users_map.get(n.sender_id, Constants.USERS.get(n.sender_id, 'System'))
        enriched.append({
            'id': n.id,
            'user_id': n.user_id,
            'sender_id': n.sender_id,
            'sender_name': sender_name,
            'task_id': n.task_id,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S') if n.created_at else '',
            'time_ago': time_elapsed_string(n.created_at)
        })

    return jsonify({
        'success': True,
        'count': unread_count,
        'notifications': enriched,
        'items': enriched
    })

@notifications_bp.route('/mark-read/<int:id>', methods=['POST'])
@login_required
def mark_as_read(id):
    user_id = session.get('user_id')
    notif = Notification.query.get_or_404(id)
    if notif.user_id == user_id:
        notif.is_read = 1
        db.session.commit()
    return jsonify({'success': True, 'csrf_hash': 'token'})

@notifications_bp.route('/toggle-read/<int:id>', methods=['POST'])
@login_required
def toggle_read(id):
    user_id = session.get('user_id')
    notif = Notification.query.get_or_404(id)
    if notif.user_id == user_id:
        notif.is_read = 0 if notif.is_read == 1 else 1
        db.session.commit()
        return jsonify({'success': True, 'is_read': notif.is_read, 'csrf_hash': 'token'})
    return jsonify({'success': False, 'csrf_hash': 'token'})

@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    user_id = session.get('user_id')
    Notification.query.filter_by(user_id=user_id).update({'is_read': 1})
    db.session.commit()
    return jsonify({'success': True, 'csrf_hash': 'token'})

@notifications_bp.route('/mark-all-unread', methods=['POST'])
@login_required
def mark_all_unread():
    user_id = session.get('user_id')
    Notification.query.filter_by(user_id=user_id).update({'is_read': 0})
    db.session.commit()
    return jsonify({'success': True, 'csrf_hash': 'token'})
