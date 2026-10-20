from datetime import datetime
import bcrypt
from flask_sqlalchemy import SQLAlchemy

# db will be imported from app.models
from .base import db

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    permissions = db.relationship('RolePermission', backref='role', cascade='all, delete-orphan', lazy='joined')
    users = db.relationship('User', backref='role', lazy='select')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    def __getitem__(self, item):
        return getattr(self, item, None)


class RolePermission(db.Model):
    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    permission_key = db.Column(db.String(50), nullable=False)
    permission_value = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    account_type = db.Column(db.Integer, default=2)  # 0=System, 1=Admin, 2=User
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def full_name(self):
        first = self.first_name or ''
        last = self.last_name or ''
        name = f"{first} {last}".strip()
        return name if name else self.username

    @property
    def name(self):
        return self.full_name


    def check_password(self, password_candidate: str) -> bool:
        if not self.password:
            return False
        try:
            # PHP password_hash uses $2y$ prefix. Python bcrypt expects $2b$
            hash_str = self.password.replace('$2y$', '$2b$')
            return bcrypt.checkpw(password_candidate.encode('utf-8'), hash_str.encode('utf-8'))
        except Exception:
            return False

    def set_password(self, new_password: str):
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt(rounds=10))
        self.password = hashed.decode('utf-8')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name or '',
            'last_name': self.last_name or '',
            'full_name': self.full_name,
            'account_type': self.account_type,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else 'Unknown',
            'profile_photo': self.profile_photo,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    def __getitem__(self, item):
        return getattr(self, item, None)
