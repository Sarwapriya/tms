from datetime import datetime
from .base import db

class AiConversation(db.Model):
    __tablename__ = 'ai_conversations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    tag_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(255), nullable=True)
    messages = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
