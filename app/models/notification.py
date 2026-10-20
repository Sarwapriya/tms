from datetime import datetime
from .base import db

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    sender_id = db.Column(db.Integer, default=0)
    task_id = db.Column(db.Integer, default=0, nullable=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
