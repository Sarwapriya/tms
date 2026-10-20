from datetime import datetime, date
from .base import db

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(500), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=True)
    conditions = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Integer, default=1)
    al_end_date = db.Column(db.Date, nullable=True)
    requested_date = db.Column(db.Date, nullable=True)
    requested_name = db.Column(db.String(500), nullable=True)
    ref_link = db.Column(db.String(500), default='', nullable=True)
    requester_name = db.Column(db.String(150), nullable=True)
    requester_email = db.Column(db.String(150), nullable=True)
    requester_organization = db.Column(db.Integer, nullable=True)
    new_tag_request = db.Column(db.Integer, nullable=True)
    new_rule_request = db.Column(db.Integer, nullable=True)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    js_code = db.Column(db.Text, nullable=True)

    # Relationships
    justifications = db.relationship('RenewalJustification', backref='tag', lazy='select', cascade='all, delete-orphan')

    @classmethod
    def count_all_tags(cls):
        return cls.query.filter(cls.deleted_at.is_(None)).count()

    @classmethod
    def count_active_tags(cls):
        from app.constants import Constants
        return cls.query.filter(
            cls.deleted_at.is_(None),
            cls.status.in_([Constants.STATUS_ENABLED, Constants.STATUS_PENDING_VERIFICATION, Constants.STATUS_UPDATED_IN_AL])
        ).count()

    @classmethod
    def count_pending_verification_tags(cls):
        from app.constants import Constants
        return cls.query.filter(
            cls.deleted_at.is_(None),
            cls.status == Constants.STATUS_PENDING_VERIFICATION
        ).count()

    @classmethod
    def count_expiring_tags(cls):
        from app.constants import Constants
        from datetime import date, timedelta
        today = date.today()
        base = today - timedelta(days=10)
        expiring = today + timedelta(days=15)
        return cls.query.filter(
            cls.deleted_at.is_(None),
            cls.status.in_([Constants.STATUS_ENABLED, Constants.STATUS_UPDATED_IN_AL]),
            cls.al_end_date >= base,
            cls.al_end_date <= expiring
        ).count()

    countAllTags = count_all_tags
    countActiveTags = count_active_tags
    countPendingVerificationTags = count_pending_verification_tags
    countExpiringTags = count_expiring_tags

    @property
    def days_remaining(self):
        if not self.al_end_date:
            return None
        import math
        d = self.al_end_date
        now = datetime.now()
        dt = (datetime.strptime(str(d)[:10], '%Y-%m-%d') if isinstance(d, str)
              else (datetime.combine(d, datetime.min.time()) if isinstance(d, date) and not isinstance(d, datetime) else d))
        return int(math.ceil((dt - now).total_seconds() / 86400))


class RenewalLog(db.Model):
    __tablename__ = 'renewal_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.String(150), nullable=True)
    property_id = db.Column(db.Integer, nullable=True)
    library_name = db.Column(db.String(150), nullable=True)
    vendor = db.Column(db.String(500), nullable=True)
    al_end_date = db.Column(db.Date, nullable=True)
    user = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RenewalJustification(db.Model):
    __tablename__ = 'renewal_justification'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)
    renew = db.Column(db.String(10), nullable=True)  # 'yes', 'no', 'Y', 'N'
    justification = db.Column(db.String(500), nullable=True)
    duration = db.Column(db.String(150), nullable=True)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
