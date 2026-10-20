from datetime import datetime
from .base import db

class TagRequest(db.Model):
    __tablename__ = 'tag_requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    new_tag_ticket = db.Column(db.String(150), nullable=True)
    tags = db.Column(db.String(200), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    status = db.Column(db.Integer, default=1)
    type = db.Column(db.Integer, nullable=False)  # 2=New Tag, 3=New Rule, 5=Update Rule
    new_rule_ticket = db.Column(db.String(150), nullable=True)
    update_rule_ticket = db.Column(db.String(150), nullable=True)
    requester_name = db.Column(db.String(200), nullable=True)
    requester_email = db.Column(db.String(200), nullable=True)
    requester_organization = db.Column(db.Integer, nullable=True)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    property = db.relationship('Property', backref='tag_requests', lazy='joined')
    vendor = db.relationship('Vendor', backref='tag_requests', lazy='joined')
    files = db.relationship('TagRequestFile', backref='request', lazy='select', cascade='all, delete-orphan')


class TagRequestFile(db.Model):
    __tablename__ = 'tag_request_files'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    type = db.Column(db.Integer, nullable=False)  # 1=Approval, 2=Email, 3=Form, 4=Doc, 5=Other
    request_id = db.Column(db.Integer, db.ForeignKey('tag_requests.id'), nullable=False)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
