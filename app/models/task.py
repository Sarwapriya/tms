from datetime import datetime
from .base import db

class ActivityLog(db.Model):
    """Corresponds to Tasks / Activity Logs in the application."""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subsidiary_id = db.Column(db.Integer, nullable=True)
    department_id = db.Column(db.String(255), nullable=True)
    team_id = db.Column(db.Integer, nullable=True)
    project = db.Column(db.String(255), nullable=True)
    ticket_id = db.Column(db.String(100), nullable=True)
    mt_jira_ticket = db.Column(db.String(50), nullable=True)
    assignee = db.Column(db.Integer, nullable=True)
    requested_by = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Integer, default=1)
    type = db.Column(db.Integer, default=1)
    size = db.Column(db.Integer, default=1)
    priority = db.Column(db.Integer, default=2)
    requested_date = db.Column(db.DateTime, nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)
    finished_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, default=0)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, nullable=True)
    campaign_status = db.Column(db.Integer, nullable=True)
    campaign_id = db.Column(db.String(200), nullable=True)
    labels = db.Column(db.String(500), nullable=True)

    # Relationships
    comments = db.relationship('ActivityLogComment', backref='task', lazy='select', cascade='all, delete-orphan')
    files = db.relationship('ActivityLogFile', backref='task', lazy='select', cascade='all, delete-orphan')

    @classmethod
    def apply_role_filters(cls, query):
        from flask import session
        from app.constants import Constants
        user_id = session.get('user_id')
        if user_id is not None:
            user_role = Constants.USER_ACCESS_LEVELS.get(user_id)
            if user_role not in [Constants.USER_ROLE_ADMIN, Constants.USER_ROLE_MEDIA_TAGGING]:
                user_team = Constants.USER_TEAMS.get(user_id)
                if user_team is not None:
                    query = query.filter(cls.team_id == user_team)
        return query

    @classmethod
    def build_query(cls, filters=None, ignore_status=False):
        from sqlalchemy import or_, and_, func
        from flask import session
        from app.constants import Constants
        filters = filters or {}
        query = cls.query.filter(cls.deleted_at.is_(None))
        query = cls.apply_role_filters(query)

        keyword = filters.get('keyword')
        if keyword:
            kw = f"%{keyword}%"
            query = query.filter(
                or_(
                    cls.title.ilike(kw),
                    cls.description.ilike(kw),
                    cls.ticket_id.ilike(kw),
                    cls.mt_jira_ticket.ilike(kw)
                )
            )

        if filters.get('subsidiary_id'):
            query = query.filter(cls.subsidiary_id == int(filters['subsidiary_id']))
        if filters.get('team_id'):
            query = query.filter(cls.team_id == int(filters['team_id']))
        if filters.get('project'):
            query = query.filter(cls.project == filters['project'])
        if filters.get('type'):
            query = query.filter(cls.type == int(filters['type']))
        if filters.get('priority'):
            query = query.filter(cls.priority == int(filters['priority']))
        if filters.get('campaign_status'):
            query = query.filter(cls.campaign_status == int(filters['campaign_status']))

        if filters.get('created_from'):
            query = query.filter(func.date(cls.created_at) >= filters['created_from'])
        if filters.get('created_to'):
            query = query.filter(func.date(cls.created_at) <= filters['created_to'])
        if filters.get('started_from'):
            query = query.filter(func.date(cls.start_date) >= filters['started_from'])
        if filters.get('started_to'):
            query = query.filter(func.date(cls.start_date) <= filters['started_to'])
        if filters.get('finished_from'):
            query = query.filter(func.date(cls.finished_date) >= filters['finished_from'])
        if filters.get('finished_to'):
            query = query.filter(func.date(cls.finished_date) <= filters['finished_to'])

        if filters.get('me_mode') in [1, '1', True]:
            uid = session.get('user_id')
            if uid:
                query = query.filter(cls.assignee == uid)
        elif filters.get('assignee'):
            query = query.filter(cls.assignee == int(filters['assignee']))

        if not ignore_status:
            status_group = filters.get('status_group')
            if status_group == 'pending':
                query = query.filter(cls.status.in_([1, 5]))
            elif status_group == 'in_progress':
                query = query.filter(cls.status.in_([2, 3, 4]))
            elif status_group == 'blocked':
                query = query.filter(cls.status.in_([7]))
            elif status_group == 'completed':
                query = query.filter(cls.status.in_([6]))
            elif status_group == 'needs_attention':
                from datetime import timedelta
                four_days_ago = datetime.utcnow() - timedelta(days=4)
                query = query.filter(
                    cls.status != Constants.ACTIVITY_LOGS_STATUS_COMPLETED,
                    cls.start_date.isnot(None),
                    cls.start_date < four_days_ago
                )
            elif filters.get('status'):
                query = query.filter(cls.status == int(filters['status']))

            show_completed = str(filters.get('show_completed', ''))
            if show_completed != '1' and status_group != 'completed':
                if str(filters.get('status')) != str(Constants.ACTIVITY_LOGS_STATUS_COMPLETED):
                    query = query.filter(cls.status != Constants.ACTIVITY_LOGS_STATUS_COMPLETED)

        labels = filters.get('labels')
        if labels:
            if isinstance(labels, str):
                labels = [labels]
            label_filters = [cls.labels.ilike(f"%{lbl.strip()}%") for lbl in labels if lbl.strip()]
            if label_filters:
                query = query.filter(or_(*label_filters))

        return query

    @classmethod
    def filter_logs(cls, filters=None, paginate=25, page=1):
        from sqlalchemy import desc, asc
        filters = filters or {}
        query = cls.build_query(filters)

        sort_by = filters.get('sort_by') or 'created_at'
        sort_dir = filters.get('sort_dir') or 'desc'
        allowed = [
            'id', 'subsidiary_id', 'team_id', 'project', 'title', 'ticket_id',
            'assignee', 'status', 'priority', 'type', 'size', 'created_at',
            'requested_date', 'start_date', 'requested_by', 'campaign_status'
        ]
        if sort_by not in allowed:
            sort_by = 'created_at'

        col = getattr(cls, sort_by, cls.created_at)
        if sort_dir.lower() == 'asc':
            query = query.order_by(asc(col))
        else:
            query = query.order_by(desc(col))

        if sort_by != 'id':
            query = query.order_by(desc(cls.id))

        if paginate > 0:
            return query.paginate(page=page, per_page=paginate, error_out=False)
        return query.all()

    @classmethod
    def get_status_counts(cls, filters=None):
        from sqlalchemy import func
        query = cls.build_query(filters, ignore_status=True)
        results = query.with_entities(cls.status, func.count(cls.id)).group_by(cls.status).all()
        counts = {i: 0 for i in range(1, 8)}
        for st, cnt in results:
            if st is not None:
                counts[int(st)] = cnt
        return counts

    @classmethod
    def get_needs_attention_count(cls, filters=None):
        from datetime import timedelta
        from app.constants import Constants
        query = cls.build_query(filters, ignore_status=True)
        four_days_ago = datetime.utcnow() - timedelta(days=4)
        return query.filter(
            cls.status != Constants.ACTIVITY_LOGS_STATUS_COMPLETED,
            cls.start_date.isnot(None),
            cls.start_date < four_days_ago
        ).count()

    @classmethod
    def get_distinct_projects(cls):
        rows = db.session.query(cls.project).filter(cls.project.isnot(None), cls.project != '', cls.deleted_at.is_(None)).distinct().order_by(cls.project).all()
        return [r[0] for r in rows if r[0]]

    @classmethod
    def get_all_labels(cls):
        rows = db.session.query(cls.labels).filter(cls.labels.isnot(None), cls.labels != '', cls.deleted_at.is_(None)).all()
        all_labels = set()
        for r in rows:
            if r[0]:
                for lbl in r[0].split(','):
                    lbl = lbl.strip()
                    if lbl:
                        all_labels.add(lbl)
        return sorted(list(all_labels))

    @classmethod
    def get_project_logs(cls, project_name, limit=None, me_mode=False, show_completed=False):
        from app.constants import Constants
        from flask import session
        query = cls.query.filter(cls.project == project_name, cls.deleted_at.is_(None))
        query = cls.apply_role_filters(query)
        if me_mode:
            uid = session.get('user_id')
            if uid:
                query = query.filter(cls.assignee == uid)
        if not show_completed:
            query = query.filter(cls.status != Constants.ACTIVITY_LOGS_STATUS_COMPLETED)
        query = query.order_by(cls.id.desc())
        if limit:
            query = query.limit(limit)
        return query.all()


class ActivityLogComment(db.Model):
    __tablename__ = 'activity_log_comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    log_id = db.Column(db.Integer, db.ForeignKey('activity_logs.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    type = db.Column(db.Integer, default=1)  # 1=User comment, 2=Auto generated status/assignee update
    commented_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityLogFile(db.Model):
    __tablename__ = 'activity_log_files'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    log_id = db.Column(db.Integer, db.ForeignKey('activity_logs.id'), nullable=False)
    created_by = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectComment(db.Model):
    __tablename__ = 'project_comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_name = db.Column(db.String(255), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    commented_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
