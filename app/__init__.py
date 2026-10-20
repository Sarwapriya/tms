import os
import re
from urllib.parse import urlencode, quote
from datetime import datetime, date, timedelta

from flask import Flask, session, redirect, url_for, request, jsonify
from config import Config
from app.models import db, Notification, Role, RolePermission, User
from app.constants import Constants
from app.utils.helpers import (
    format_date, format_datetime, time_ago,
    status_badge, request_status_badge, task_status_badge, priority_badge
)

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.url_map.strict_slashes = False
    app.config.from_object(config_class)

    # Initialize Database
    db.init_app(app)

    with app.app_context():
        try:
            from sqlalchemy import text
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS `mt_jira_api_log` (
                  `id` int(11) NOT NULL AUTO_INCREMENT,
                  `task_id` int(11) DEFAULT NULL,
                  `request_type` varchar(50) NOT NULL,
                  `endpoint_url` varchar(255) NOT NULL,
                  `payload` text,
                  `response_body` text,
                  `status_code` int(11) DEFAULT NULL,
                  `error_message` varchar(255) DEFAULT NULL,
                  `status` enum('SUCCESS','FAILED','PENDING_RETRY') NOT NULL DEFAULT 'FAILED',
                  `retry_count` int(11) NOT NULL DEFAULT 0,
                  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `idx_task_id` (`task_id`),
                  KEY `idx_status` (`status`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """))
            db.session.commit()
        except Exception:
            pass

    # Add CodeIgniter Pager compatibility methods to Flask-SQLAlchemy QueryPagination
    from flask_sqlalchemy.pagination import QueryPagination

    QueryPagination.getPageCount = lambda self, *args, **kwargs: self.pages
    QueryPagination.getCurrentPage = lambda self, *args, **kwargs: self.page
    QueryPagination.getTotal = lambda self, *args, **kwargs: self.total
    QueryPagination.links = lambda self, *args, **kwargs: ''


    # Register Template Filters & Globals

    import app.utils.helpers as h
    for fn_name in [
        'status_label', 'status_class', 'status_activity_logs_class',
        'status_request_class', 'assignee_class', 'priority_class',
        'size_class', 'size_description', 'size_tooltip',
        'bool_label', 'bool_class', 'date_class', 'days_class', 'diff_days',
        'random_bg_style', 'random_text_style', 'date_ymd',
        'format_comment_time', 'format_date', 'format_datetime', 'time_ago',
        'status_badge', 'request_status_badge', 'task_status_badge', 'priority_badge'
    ]:
        fn = getattr(h, fn_name, None)
        if fn:
            app.jinja_env.globals[fn_name] = fn
            app.jinja_env.filters[fn_name] = fn

    # Register Global Template Context
    @app.context_processor
    def inject_globals():
        from markupsafe import Markup, escape
        from urllib.parse import urlencode


        unread_count = 0
        user_id = session.get('user_id')
        if user_id:
            try:
                unread_count = Notification.query.filter_by(user_id=user_id, is_read=0).count()
            except Exception:
                unread_count = 0

        version = "2.3"
        version_file = os.path.join(app.root_path, '..', 'version.txt')
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    version = f.read().strip()
            except Exception:
                pass

        class UriHelper:
            def __init__(self, path):
                self.parts = [p for p in path.strip('/').split('/') if p]

            def getSegment(self, idx):
                if 1 <= idx <= len(self.parts):
                    return self.parts[idx - 1]
                return ''

            def getTotalSegments(self):
                return len(self.parts)

        uri_obj = UriHelper(request.path)
        first_segment = uri_obj.getSegment(1)

        def site_url(path=''):
            if not path or path == '/':
                return '/'
            path = str(path).lstrip('/')
            return f"/{path}"

        def base_url(path=''):
            if not path:
                return '/static/'
            clean = str(path).lstrip('/')
            if clean.startswith('assets/'):
                return f"/static/{clean[7:]}"
            elif clean.startswith('uploads/'):
                return f"/download?file={clean[8:]}"
            return f"/static/{clean}"

        def old(key, default=''):
            val = request.form.get(key)
            if val is not None and str(val).strip() not in ('', 'None'):
                return val
            val = request.args.get(key)
            if val is not None and str(val).strip() not in ('', 'None'):
                return val
            if default is None or str(default).strip() in ('', 'None'):
                return ''
            return default

        def esc(val, context='html'):
            if val is None or val == 'None':
                return ''
            s = str(val)
            if context == 'js':
                return s.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
            return s


        def csrf_field():
            return Markup('<input type="hidden" name="csrf_test_name" value="token" />')

        def getSortUrl(field, currentSortBy, currentSortDir):
            args = request.args.to_dict()
            args['sort_by'] = field
            if currentSortBy == field:
                args['sort_dir'] = 'desc' if currentSortDir == 'asc' else 'asc'
            else:
                args['sort_dir'] = 'asc'
            return request.path + '?' + urlencode(args)

        def getGroupFilterUrl(group):
            args = request.args.to_dict()
            if args.get('status_group') == group:
                args.pop('status_group', None)
            else:
                args['status_group'] = group
                args.pop('status', None)
            args.pop('page', None)
            return request.path + '?' + urlencode(args)

        def getMeModeUrl():
            args = request.args.to_dict()
            me_mode_session = (session.get('al_me_mode') == 1)
            is_me_mode_active = (args.get('me_mode') == '1') if 'me_mode' in args else me_mode_session
            if is_me_mode_active:
                args['me_mode'] = '0'
            else:
                args['me_mode'] = '1'
                args.pop('assignee', None)
            args.pop('page', None)
            return request.path + '?' + urlencode(args)

        def url_for_page(page_num):
            args = request.args.to_dict()
            args['page'] = page_num
            return request.path + '?' + urlencode(args)

        def getSortIcon(field, currentSortBy, currentSortDir):
            if currentSortBy == field:
                icon = 'bi bi-arrow-up text-primary' if currentSortDir == 'asc' else 'bi bi-arrow-down text-primary'
                return Markup(f' <i class="{icon}"></i>')
            return Markup(' <i class="bi bi-arrow-down-up text-muted" style="font-size: 0.75rem; opacity: 0.4;"></i>')

        def remove_filter_url(key):
            args = request.args.to_dict()
            args.pop(key, None)
            args.pop('page', None)
            qs = urlencode(args)
            return request.path + ('?' + qs if qs else '')

        def http_build_query(params):
            if isinstance(params, dict):
                return urlencode({k: v for k, v in params.items() if v is not None and v != ''})
            return ''

        def buildProjectUrl(project_name, extra_params=None):
            args = request.args.to_dict()
            if extra_params:
                args.update(extra_params)
            if str(args.get('show_completed', '')) in ['0', '']:
                args.pop('show_completed', None)
            query_str = ('?' + urlencode(args)) if args else ''
            return f"/tasks/project/{quote(str(project_name))}{query_str}"

        def robust_strtotime(s):

            if not s:
                return 0
            s_str = str(s).strip()
            if s_str == '+2 months' or s_str == '+61 days':
                return int((datetime.now() + timedelta(days=61)).timestamp())
            if s_str.startswith('+') and 'month' in s_str:
                num = int(''.join(filter(str.isdigit, s_str)) or 1)
                return int((datetime.now() + timedelta(days=30 * num)).timestamp())
            if s_str.startswith('+') and 'day' in s_str:
                num = int(''.join(filter(str.isdigit, s_str)) or 1)
                return int((datetime.now() + timedelta(days=num)).timestamp())
            if s_str.startswith('-') and 'day' in s_str:
                num = int(''.join(filter(str.isdigit, s_str)) or 1)
                return int((datetime.now() - timedelta(days=num)).timestamp())
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S'):
                try:
                    return int(datetime.strptime(s_str[:19], fmt).timestamp())
                except Exception:
                    pass
            try:
                return int(datetime.fromisoformat(s_str).timestamp())
            except Exception:
                return int(datetime.now().timestamp())

        def service(name):
            if name == 'request':
                class ReqWrapper:
                    def getGet(self, k, default=''):
                        return request.args.get(k, default)
                    def getPost(self, k, default=''):
                        return request.form.get(k, default)
                return ReqWrapper()
            return None

        class SessionWrapper:
            def __init__(self, s):
                self._s = s
            def __getitem__(self, k):
                return self._s.get(k)
            def get(self, k, d=None):
                return self._s.get(k, d)
            def getFlashdata(self, k, d=''):
                return self._s.pop(k, d)
            def __contains__(self, k):
                return k in self._s
            def __getattr__(self, name):
                return getattr(self._s, name)

        def format_date(fmt='Y-m-d', ts=None):
            if ts is None or ts == '':
                dt = datetime.now()
            elif isinstance(ts, (datetime, date)):
                dt = ts
            elif isinstance(ts, (int, float)):
                try:
                    dt = datetime.fromtimestamp(ts)
                except Exception:
                    dt = datetime.now()
            elif isinstance(ts, str):
                try:
                    parsed_ts = robust_strtotime(ts)
                    dt = datetime.fromtimestamp(parsed_ts)
                except Exception:
                    dt = datetime.now()
            else:
                dt = datetime.now()

            php_to_python = {
                'Y': '%Y', 'y': '%y', 'm': '%m', 'd': '%d',
                'M': '%b', 'F': '%B', 'H': '%H', 'h': '%I',
                'i': '%M', 's': '%S', 'A': '%p', 'a': '%p',
                'D': '%a', 'l': '%A'
            }
            out_fmt = ''
            for ch in fmt:
                out_fmt += php_to_python.get(ch, ch)
            try:
                return dt.strftime(out_fmt)
            except Exception:
                return dt.strftime('%Y-%m-%d')

        return {
            'Constants': Constants,
            'current_user': {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'name': session.get('user_name', 'Guest'),
                'account_type': session.get('account_type', 2),
                'role_id': session.get('user_role'),
                'role_name': session.get('user_role_name', 'User'),
                'profile_photo': session.get('profile_photo'),
                'is_logged_in': session.get('is_logged_in', False),
            },
            'session': SessionWrapper(session),


            'permissions': (lambda p: {x: True for x in p} if isinstance(p, (list, tuple, set)) else (p if isinstance(p, dict) else {}))(session.get('permissions', {})),
            'unread_notifications_count': unread_count,
            'app_version': version,
            'current_path': request.path,
            'segment': first_segment,
            'uri': uri_obj,
            'site_url': site_url,
            'base_url': base_url,
            'hasattr': hasattr,
            'old': old,
            'esc': esc,
            'csrf_field': csrf_field,
            'getSortUrl': getSortUrl,
            'getSortIcon': getSortIcon,
            'getGroupFilterUrl': getGroupFilterUrl,
            'getMeModeUrl': getMeModeUrl,
            'url_for_page': url_for_page,
            'remove_filter_url': remove_filter_url,
            'http_build_query': http_build_query,
            'buildProjectUrl': buildProjectUrl,
            'in_array': lambda val, arr: val in arr if arr else False,
            'strip_tags': lambda s: re.sub(r'<[^>]*>', '', str(s)) if s else '',
            'rawurlencode': quote,
            'date': format_date,
            'strtotime': robust_strtotime,
            'clean_html_comment': h.clean_html_comment,
            'array_values': lambda d: list(d.values()) if isinstance(d, dict) else list(d),
            'current_year': datetime.now().year,
            'count': len,
            'empty': lambda x: not x,
            'timeElapsedString': time_ago,
            'diff_days': lambda d: (
                int(__import__('math').ceil((
                    (datetime.strptime(str(d)[:10], '%Y-%m-%d') if isinstance(d, str)
                     else (datetime.combine(d, datetime.min.time()) if isinstance(d, date) and not isinstance(d, datetime) else d))
                    - datetime.now()
                ).total_seconds() / 86400)) if d else 0
            ),
            'request': request,
            '_GET': request.args,
            '_POST': request.form,
            '_SERVER': request.environ,
            'htmlspecialchars': lambda s, *args, **kwargs: Markup(escape(str(s))),
            'json_encode': lambda obj, *args, **kwargs: Markup(
                __import__('json').dumps(
                    obj,
                    default=lambda o: o.to_dict() if hasattr(o, 'to_dict') and callable(o.to_dict)
                    else (o.strftime('%Y-%m-%d %H:%M:%S') if isinstance(o, (datetime, date)) else str(o))
                ).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
            ),

            'strtolower': lambda s: str(s).lower() if s else '',
            'strtoupper': lambda s: str(s).upper() if s else '',
            'substr': lambda s, start, length=None: (str(s)[start:start+length] if length is not None else str(s)[start:]) if s else '',
            'isset': lambda x=None: x is not None,
            'null': None,
            'STATUS_ALL': 'all',
            'number_format': lambda val, dec=0, dec_sep='.', th_sep=',': f"{float(val or 0):,.{dec}f}",
            'addslashes': lambda s: str(s).replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'") if s else '',
            'urlencode': quote,
            'ENT_QUOTES': 3,
            'csrf_token': lambda: 'csrf_test_name',
            'csrf_hash': lambda: 'token',
            'ci_environment': os.getenv('CI_ENVIRONMENT', os.getenv('FLASK_ENV', 'production')).lower(),
            'listErrors': lambda: '',
            'validation': None,
            'error': None,
            'tag': None,
            'links': lambda *args, **kwargs: '',
            'clearUrl': lambda *args, **kwargs: request.path,
            'getGet': lambda k=None, d='': request.args.get(k, d) if k is not None else request.args,

            'service': service,
            'aiModels': [
                {'id': 'gpt-4o', 'name': 'GPT-4o', 'description': 'Most capable multimodal model for complex reasoning'},
                {'id': 'gpt-4o-mini', 'name': 'GPT-4o mini', 'description': 'Fast and lightweight model'}
            ],
            'request_type_label': lambda t, s=None: (
                'New Rule' if (int(t or 0) == Constants.JIRA_TYPE_NEW_TAG and int(s or 0) == Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED)
                else Constants.REQUEST_TYPES.get(int(t or 0), Constants.JIRA_TICKET_TYPES.get(int(t or 0), 'Unknown'))
            ),
            'request_type_field': lambda t, s=None: (
                'new-rule-request' if (int(t or 0) == Constants.JIRA_TYPE_NEW_TAG and int(s or 0) == Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED)
                else Constants.REQUEST_TYPE_FIELD.get(int(t or 0), 'view')
            ),
            'status_label': h.status_label,
            'status_class': h.status_class,
            'status_request_class': h.status_request_class,
            'status_activity_logs_class': h.status_activity_logs_class,
            'priority_class': h.priority_class,
            'date_class': h.date_class,
            'days_class': h.days_class,
            'diff_days': h.diff_days,
            'random_bg_style': h.random_bg_style,
            'random_text_style': h.random_text_style,
            'prioClass': h.priority_class,
            'statusClass': h.status_class,
        }

    # Daily auto-backup check on non-static incoming requests
    @app.before_request
    def check_auto_backup():
        if request.endpoint and not request.endpoint.startswith('static'):
            try:
                from app.services.backup_service import BackupService
                BackupService().check_and_run_auto_backup()
            except Exception:
                pass

    # Root redirect to /dashboard
    @app.route('/')
    def root():
        if session.get('is_logged_in'):
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    # Register Blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.dashboard.routes import dashboard_bp
    from app.blueprints.tags.routes import tags_bp
    from app.blueprints.tag_requests.routes import tag_requests_bp
    from app.blueprints.properties.routes import properties_bp
    from app.blueprints.vendors.routes import vendors_bp
    from app.blueprints.jira.routes import jira_bp
    from app.blueprints.tasks.routes import tasks_bp
    from app.blueprints.reports.routes import reports_bp
    from app.blueprints.settings.routes import settings_bp
    from app.blueprints.profile.routes import profile_bp
    from app.blueprints.notifications.routes import notifications_bp

    app.register_blueprint(auth_bp, url_prefix='')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(tags_bp, url_prefix='/tags')
    app.register_blueprint(tag_requests_bp, url_prefix='/tag-requests')
    app.register_blueprint(properties_bp, url_prefix='/properties')
    app.register_blueprint(vendors_bp, url_prefix='/vendors')
    app.register_blueprint(jira_bp, url_prefix='/jira')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')

    # Register Secure Storage Download Route
    from flask import send_from_directory, abort
    @app.route('/download')
    @app.route('/download.php')
    def download_file():
        rel_path = request.args.get('file')
        if not rel_path:
            abort(400, "Missing file parameter")
        safe_path = os.path.normpath(rel_path).lstrip('\\/')
        full_dir = Config.UPLOAD_DIR
        file_path = os.path.join(full_dir, safe_path)
        if not os.path.exists(file_path):
            abort(404, "File not found")
        import mimetypes
        mimetype, _ = mimetypes.guess_type(file_path)
        is_image = mimetype and (mimetype.startswith('image/') or mimetype in ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml'])
        as_attachment = (request.args.get('download') == '1') or (not is_image and request.args.get('inline') != '1')
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), as_attachment=as_attachment)

    @app.route('/testdb')
    def test_db():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({'status': 'success', 'database': 'connected', 'engine': 'MySQL'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'database': 'failed', 'message': str(e)}), 500

    return app
