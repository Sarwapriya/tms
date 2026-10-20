import os
import re
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from app.models import db, User, Role, RolePermission, JiraApiLog
from app.constants import Constants
from app.utils.decorators import login_required, permission_required
from app.services.backup_service import BackupService
from app.services.jira_service import JiraService
from config import Config

settings_bp = Blueprint('settings', __name__)
backup_service = BackupService()

def get_env_file_path():
    return os.path.join(Config.BASE_DIR, '.env')

def get_env_variables():
    env_file = get_env_file_path()
    vars_dict = {}
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        vars_dict[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass
    return vars_dict

def update_env_variables(updates):
    env_file = get_env_file_path()
    if not os.path.exists(env_file):
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write('')
        except Exception:
            return False

    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()

        for key, value in updates.items():
            val_str = '' if value is None else str(value).strip()
            # Wrap string in quotes if non-empty
            safe_value = f"'{val_str}'" if val_str != '' else "''"
            pattern = re.compile(rf'^\s*{re.escape(key)}\s*=.*$', re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(f"{key}={safe_value}", content)
            else:
                content += f"\n{key}={safe_value}\n"

        content = re.sub(r'\n{3,}', '\n\n', content)
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # Update in-memory runtime environment and Config object
        for k, v in updates.items():
            if v is not None:
                os.environ[k] = str(v)
                if hasattr(Config, k):
                    setattr(Config, k, str(v))

        return True
    except Exception:
        return False

def get_system_settings():
    default = {
        'hide_assignee_weekly_reports': True,
        'hide_assignee_system_wide': False,
        'force_me_mode_system_wide': False,
        'flagship_page': '/smartphones/galaxy-s26',
        'flagship_buy_page': '/smartphones/galaxy-s26/buy',
        'excel_title_c3': 'S26',
        'excel_title_d3': 'S26 Buy',
    }
    if os.path.exists(Config.SYSTEM_SETTINGS_FILE):
        try:
            with open(Config.SYSTEM_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**default, **data}
        except Exception:
            pass
    return default

def get_app_environment():
    env_vars = get_env_variables()
    return env_vars.get('CI_ENVIRONMENT', env_vars.get('FLASK_ENV', 'production')).lower()


@settings_bp.route('/')
@login_required
@permission_required('settings')
def index():
    users = User.query.order_by(User.id.desc()).all()
    roles = Role.query.all()

    # Build permission matrix: role_permissions[role_id][module] = True/False
    role_perms_raw = RolePermission.query.all()
    role_permissions = {}
    for rp in role_perms_raw:
        if rp.role_id not in role_permissions:
            role_permissions[rp.role_id] = {}
        role_permissions[rp.role_id][rp.permission_key] = bool(rp.permission_value)

    backups = backup_service.list_backups()
    auto_backup_settings = backup_service.get_settings()
    sys_settings = get_system_settings()
    env_vars = get_env_variables()
    ci_env = get_app_environment()

    # API Logs pagination & filtering
    api_page = request.args.get('api_page', type=int) or request.args.get('page_apilogs', type=int) or 1
    api_status = request.args.get('api_status', 'all').strip()

    api_query = JiraApiLog.query
    if api_status in ('SUCCESS', 'FAILED'):
        api_query = api_query.filter_by(status=api_status)

    api_logs_pagination = api_query.order_by(JiraApiLog.id.desc()).paginate(page=api_page, per_page=20, error_out=False)

    roles_map = {r.id: r.name for r in roles}

    # Active tab selection (persisted across redirects via session or query string)
    active_tab = session.pop('active_tab', None)
    if not active_tab:
        if 'api_page' in request.args or 'page_apilogs' in request.args or 'api_status' in request.args:
            active_tab = 'api-logs'
        else:
            active_tab = None

    return render_template(
        'settings/index.html',
        users=users,
        roles=roles,
        rolesMap=roles_map,
        rolePermissions=role_permissions,
        backups=backups,
        autoBackupSettings=auto_backup_settings,
        systemSettings=sys_settings,
        ci_environment=ci_env,
        envVars=env_vars,
        apiLogs=api_logs_pagination.items,
        apiLogsPager=api_logs_pagination,
        api_status=api_status,
        active_tab=active_tab
    )


@settings_bp.route('/user/create', methods=['POST'])
@login_required
@permission_required('settings')
def create_user():
    session['active_tab'] = 'users'
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role_id = request.form.get('role_id', type=int)
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()

    if not username or not password:
        flash('Username and Password are required.', 'error')
        return redirect(url_for('settings.index'))

    if User.query.filter_by(username=username).first():
        flash('Username is already taken.', 'error')
        return redirect(url_for('settings.index'))

    account_type = 1 if role_id == Constants.USER_ROLE_ADMIN else 2
    is_active_val = request.form.get('is_active', '1')
    is_active = 1 if str(is_active_val).strip() in ('1', 'true', 'active') else 0

    user = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        role_id=role_id,
        account_type=account_type,
        is_active=is_active
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"User '{username}' created successfully.", 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/user/update/<int:id>', methods=['POST'])
@login_required
@permission_required('settings')
def update_user(id):
    session['active_tab'] = 'users'
    user = User.query.get_or_404(id)

    new_username = request.form.get('username', '').strip()
    if not new_username:
        flash('Username is required.', 'error')
        return redirect(url_for('settings.index'))

    if new_username != user.username:
        existing = User.query.filter(User.username == new_username, User.id != id).first()
        if existing:
            flash(f"Username '{new_username}' is already taken.", 'error')
            return redirect(url_for('settings.index'))
        user.username = new_username

    user.first_name = request.form.get('first_name', '').strip()
    user.last_name = request.form.get('last_name', '').strip()

    role_id = request.form.get('role_id', type=int)
    if role_id:
        user.role_id = role_id
        user.account_type = 1 if role_id == Constants.USER_ROLE_ADMIN else 2

    is_active_val = request.form.get('is_active')
    if is_active_val is not None:
        user.is_active = 1 if str(is_active_val).strip() in ('1', 'true', 'active') else 0

    new_pwd = request.form.get('password', '').strip()
    if new_pwd:
        user.set_password(new_pwd)

    db.session.commit()
    flash(f"User '{user.username}' updated successfully.", 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/user/delete/<int:id>', methods=['POST'])
@login_required
@permission_required('settings')
def delete_user(id):
    session['active_tab'] = 'users'
    user = User.query.get_or_404(id)

    # Prevent self deletion
    if user.id == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('settings.index'))

    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{username}' deleted successfully.", 'success')
    except Exception:
        db.session.rollback()
        user = User.query.get(id)
        if user:
            user.is_active = 0
            db.session.commit()
            flash(f"User '{user.username}' is referenced by tasks/logs and was deactivated instead of permanently deleted.", 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/roles/create', methods=['POST'])
@login_required
@permission_required('settings')
def create_role():
    session['active_tab'] = 'permissions'
    name = request.form.get('role_name', request.form.get('name', '')).strip()
    if not name:
        flash('Role name is required.', 'error')
        return redirect(url_for('settings.index'))

    if Role.query.filter_by(name=name).first():
        flash('Role name already exists.', 'error')
        return redirect(url_for('settings.index'))

    role = Role(name=name)
    db.session.add(role)
    db.session.commit()

    # Initialize default permissions (dashboard enabled, others disabled)
    sections = ['dashboard', 'tags', 'tag-requests', 'properties', 'vendors', 'jira', 'tasks', 'settings', 'reports']
    for sec in sections:
        db.session.add(RolePermission(role_id=role.id, permission_key=sec, permission_value=1 if sec == 'dashboard' else 0))
    db.session.commit()

    flash(f'Role "{name}" created successfully.', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/roles/update/<int:id>', methods=['POST'])
@login_required
@permission_required('settings')
def update_role(id):
    session['active_tab'] = 'permissions'
    role = Role.query.get_or_404(id)
    name = request.form.get('role_name', request.form.get('name', '')).strip()
    if not name:
        flash('Role name is required.', 'error')
        return redirect(url_for('settings.index'))

    existing = Role.query.filter(Role.name == name, Role.id != id).first()
    if existing:
        flash('Role name already exists.', 'error')
        return redirect(url_for('settings.index'))

    role.name = name
    db.session.commit()
    flash(f'Role name updated to "{name}" successfully.', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/permissions/save', methods=['POST'])
@login_required
@permission_required('settings')
def save_permissions():
    perms_data = request.form.to_dict()
    roles = Role.query.all()
    sections = ['dashboard', 'tags', 'tag-requests', 'properties', 'vendors', 'jira', 'tasks', 'settings', 'reports']

    for role in roles:
        for sec in sections:
            key_nested = f"permissions[{role.id}][{sec}]"
            key_flat = f"perm_{role.id}_{sec}"

            is_checked = (
                perms_data.get(key_nested) in ('1', 'on', 'true', True)
                or perms_data.get(key_flat) in ('1', 'on', 'true', True)
                or key_nested in request.form
                or key_flat in request.form
            )
            val = 1 if is_checked else 0

            # Superadmin / Admin must always retain settings and dashboard access
            if role.id == Constants.USER_ROLE_ADMIN and sec in ['settings', 'dashboard']:
                val = 1

            p = RolePermission.query.filter_by(role_id=role.id, permission_key=sec).first()
            if not p:
                p = RolePermission(role_id=role.id, permission_key=sec, permission_value=val)
                db.session.add(p)
            else:
                p.permission_value = val

    db.session.commit()

    # Immediately refresh active user's permissions in session
    curr_role = session.get('user_role')
    if curr_role:
        db_perms = RolePermission.query.filter_by(role_id=curr_role).all()
        session['permissions'] = {p.permission_key: bool(p.permission_value) for p in db_perms}

    session['active_tab'] = 'permissions'
    flash('Permissions updated successfully.', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/backup/create', methods=['POST'])
@login_required
@permission_required('settings')
def create_backup():
    session['active_tab'] = 'backups'
    res = backup_service.create_backup(force=True)
    if res['success']:
        flash(res['message'], 'success')
    else:
        flash(res['message'], 'error')
    return redirect(url_for('settings.index'))


@settings_bp.route('/backup/settings', methods=['POST'])
@login_required
@permission_required('settings')
def save_backup_settings():
    session['active_tab'] = 'backups'
    enabled = request.form.get('enabled') == '1' or request.form.get('auto_backup_enabled') == '1'
    retention_count = request.form.get('retention_count', 10, type=int)

    if retention_count < 1:
        flash('Retention count must be at least 1.', 'error')
        return redirect(url_for('settings.index'))

    backup_service.save_settings({'enabled': enabled, 'retention_count': retention_count})
    flash('Daily auto backup settings saved successfully.', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/backup/download/<path:filename>')
@login_required
@permission_required('settings')
def download_backup(filename):
    safe_name = os.path.basename(filename)
    fp = os.path.join(Config.BACKUP_DIR, safe_name)
    if os.path.exists(fp):
        return send_file(fp, as_attachment=True)
    flash('Backup file not found.', 'error')
    return redirect(url_for('settings.index'))


@settings_bp.route('/backup/delete/<path:filename>', methods=['POST'])
@login_required
@permission_required('settings')
def delete_backup(filename):
    session['active_tab'] = 'backups'
    if backup_service.delete_backup(filename):
        flash('Backup file deleted.', 'success')
    else:
        flash('Backup file not found.', 'error')
    return redirect(url_for('settings.index'))


@settings_bp.route('/backup/restore/<path:filename>', methods=['POST'])
@login_required
@permission_required('settings')
def restore_backup(filename):
    session['active_tab'] = 'backups'
    res = backup_service.restore_backup(filename)
    if res['success']:
        flash(res['message'], 'success')
    else:
        flash(res['message'], 'error')
    return redirect(url_for('settings.index'))


@settings_bp.route('/save-system-settings', methods=['POST'])
@login_required
@permission_required('settings')
def save_system_settings():
    session['active_tab'] = 'general'

    settings = {
        'hide_assignee_weekly_reports': request.form.get('hide_assignee_weekly_reports') == '1',
        'hide_assignee_system_wide': request.form.get('hide_assignee_system_wide') == '1',
        'force_me_mode_system_wide': request.form.get('force_me_mode_system_wide') == '1',
        'flagship_page': request.form.get('flagship_page', '').strip(),
        'flagship_buy_page': request.form.get('flagship_buy_page', '').strip(),
        'excel_title_c3': request.form.get('excel_title_c3', '').strip(),
        'excel_title_d3': request.form.get('excel_title_d3', '').strip(),
    }

    dir_path = os.path.dirname(Config.SYSTEM_SETTINGS_FILE)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    with open(Config.SYSTEM_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)

    ci_env = request.form.get('ci_environment')
    if ci_env in ('development', 'production'):
        update_env_variables({'CI_ENVIRONMENT': ci_env, 'FLASK_ENV': ci_env})

    flash('General system settings saved successfully.', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/save-jira-settings', methods=['POST'])
@login_required
@permission_required('settings')
def save_jira_settings():
    session['active_tab'] = 'jira'

    updates = {
        'MT_JIRA_CREATE_ISSUE': request.form.get('mt_jira_create_issue', '').strip(),
        'MT_JIRA_EDIT_ISSUE': request.form.get('mt_jira_edit_issue', '').strip(),
        'MT_JIRA_UPDATE_STATUS': request.form.get('mt_jira_update_status', '').strip(),
        'MT_JIRA_UPLOAD_ATTACHMENT': request.form.get('mt_jira_upload_attachment', '').strip(),
        'MT_JIRA_ADD_COMMENT': request.form.get('mt_jira_add_comment', '').strip(),
        'MT_JIRA_UPDATE_COMMENT': request.form.get('mt_jira_update_comment', '').strip(),
        'MT_JIRA_AUTH_TOKEN': request.form.get('mt_jira_auth_token', '').strip(),
        'MT_JIRA_PROJECT_KEY': request.form.get('mt_jira_project_key', '').strip(),
    }

    if update_env_variables(updates):
        flash('Jira settings successfully updated in .env.', 'success')
    else:
        flash('Failed to update Jira settings.', 'error')

    return redirect(url_for('settings.index'))


@settings_bp.route('/retry-api-log/<int:id>', methods=['POST'])
@login_required
@permission_required('settings')
def retry_api_log(id):
    session['active_tab'] = 'api-logs'
    body_data = request.get_json(silent=True) or {}
    endpoint = body_data.get('endpoint')
    payload = body_data.get('payload')

    res = JiraService.retry_log(id, custom_endpoint=endpoint, custom_payload=payload)
    return jsonify(res)
