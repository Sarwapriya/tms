from datetime import datetime
from .base import db

class Subsidiary(db.Model):
    __tablename__ = 'subsidiaries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Integer, default=1)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    properties = db.relationship('Property', backref='subsidiary', lazy='select')

    @classmethod
    def options(cls):
        return {s.id: s.name for s in cls.query.filter_by(deleted_at=None).order_by(cls.name).all()}

    Options = options


class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)


    @classmethod
    def options(cls):
        return {o.id: o.name for o in cls.query.filter_by(deleted_at=None).order_by(cls.name).all()}

    Options = options


class Country(db.Model):
    __tablename__ = 'countries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def options(cls):
        return {c.id: c.name for c in cls.query.filter_by(deleted_at=None).order_by(cls.name).all()}

    Options = options


class Language(db.Model):
    __tablename__ = 'languages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(10), nullable=False)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def options(cls):
        return {l.id: l.name for l in cls.query.filter_by(deleted_at=None).order_by(cls.name).all()}

    Options = options



class Vendor(db.Model):
    __tablename__ = 'vendors'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    about = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    tag_purpose = db.Column(db.Text, nullable=True)
    collected_data = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Integer, default=1)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    tags = db.relationship('Tag', backref='vendor', lazy='select')

    @classmethod
    def options(cls):
        return {v.id: v.name for v in cls.query.filter_by(deleted_at=None).order_by(cls.name).all()}

    Options = options


class Property(db.Model):
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Integer, default=1)
    is_epp = db.Column(db.Integer, default=0)
    is_shop = db.Column(db.Integer, default=0)
    subsidiary_id = db.Column(db.Integer, db.ForeignKey('subsidiaries.id'), nullable=True)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id'), nullable=True)
    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    ref_link = db.Column(db.String(500), nullable=True)
    updated_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_by = db.Column(db.Integer, default=0, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    tags = db.relationship('Tag', backref='property', lazy='select')
    country = db.relationship('Country', backref='properties', lazy='joined')
    language = db.relationship('Language', backref='properties', lazy='joined')

    @classmethod
    def options(cls):
        return {p.id: p.name for p in cls.query.filter_by(deleted_at=None).order_by(cls.name).all()}

    @classmethod
    def website_links(cls):
        return {p.id: p.website or p.name for p in cls.query.filter_by(deleted_at=None).all()}

    @classmethod
    def get_site_code(cls, property_id):
        if not property_id:
            return ''
        p = cls.query.get(property_id) if isinstance(property_id, int) else property_id
        if not p:
            return ''
        import re
        m = re.search(r'_(?:Hybris_)?([A-Za-z0-9_]+)-', p.name or '')
        if m:
            return m.group(1)
        if p.country and p.country.code:
            return p.country.code
        return p.name or ''

    @classmethod
    def is_shop_property(cls, property_id):
        if not property_id:
            return 'AEM'
        p = cls.query.get(property_id) if isinstance(property_id, int) else property_id
        if not p:
            return 'AEM'
        return 'Shop' if p.is_shop == 1 else 'AEM'

    Options = options
    WebsiteLinks = website_links
    getSiteCode = get_site_code
    isShop = is_shop_property

