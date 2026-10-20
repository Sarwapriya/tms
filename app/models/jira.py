from datetime import datetime
from .base import db

class JiraHistory(db.Model):
    __tablename__ = 'jira_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.String(150), nullable=True)
    type = db.Column(db.String(150), nullable=True)
    comments = db.Column(db.String(500), nullable=True)
    tag_id = db.Column(db.Integer, nullable=True)
    property_id = db.Column(db.Integer, default=0)
    subsidiary_id = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Integer, default=1)
    file_path = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_related_tags(cls, tag_id):
        from sqlalchemy import func
        from app.constants import Constants
        str_id = str(tag_id)
        valid_types = [
            str(Constants.JIRA_TYPE_DATE_EXTENSION_RULE),
            str(Constants.JIRA_TYPE_NEW_TAG),
            str(Constants.JIRA_TYPE_NEW_RULE),
            str(Constants.JIRA_TYPE_UPDATE_RULE),
            Constants.JIRA_TYPE_DATE_EXTENSION_RULE,
            Constants.JIRA_TYPE_NEW_TAG,
            Constants.JIRA_TYPE_NEW_RULE,
            Constants.JIRA_TYPE_UPDATE_RULE,
        ]
        return cls.query.filter(
            db.or_(
                cls.tag_id == tag_id,
                db.and_(
                    cls.type.in_(valid_types),
                    func.find_in_set(str_id, cls.comments) > 0
                )
            )
        ).order_by(cls.created_at.desc()).all()


class JiraApiLog(db.Model):
    __tablename__ = 'mt_jira_api_log'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, nullable=True)
    request_type = db.Column(db.String(50), nullable=False)
    endpoint_url = db.Column(db.String(255), nullable=False)
    payload = db.Column(db.Text, nullable=True)
    response_body = db.Column(db.Text, nullable=True)
    status_code = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='PENDING_RETRY')
    retry_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'request_type': self.request_type,
            'endpoint_url': self.endpoint_url,
            'payload': self.payload,
            'response_body': self.response_body,
            'status_code': self.status_code,
            'error_message': self.error_message,
            'status': self.status,
            'retry_count': self.retry_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else ''
        }
