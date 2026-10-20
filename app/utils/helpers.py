from datetime import datetime, date
from markupsafe import Markup, escape
from app.constants import Constants

def format_date(value, fmt='%Y-%m-%d'):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value[:10], '%Y-%m-%d')
        except Exception:
            return value
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return str(value)

def format_datetime(value, fmt='%Y-%m-%d %H:%M:%S'):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    if isinstance(value, datetime):
        return value.strftime(fmt)
    return str(value)

def time_ago(dt):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    now = datetime.utcnow()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds // 86400)
        return f"{days}d ago"

def status_badge(status_id):
    name = Constants.STATUS.get(status_id, 'Unknown')
    badge_classes = {
        Constants.STATUS_ENABLED: 'bg-success text-white',
        Constants.STATUS_DISABLED: 'bg-secondary text-white',
        Constants.STATUS_EXPIRED: 'bg-danger text-white',
        Constants.STATUS_PENDING_VERIFICATION: 'bg-warning text-dark',
        Constants.STATUS_UPDATED_IN_AL: 'bg-info text-dark',
        Constants.STATUS_NEW_TAG_SUBMITTED: 'bg-primary text-white',
        Constants.STATUS_NEW_RULE_SUBMITTED: 'bg-primary text-white',
        Constants.STATUS_ENDED: 'bg-dark text-white',
        Constants.STATUS_ON_HOLD: 'bg-warning text-dark',
        Constants.STATUS_INVALID: 'bg-secondary text-white',
    }
    css = badge_classes.get(status_id, 'bg-secondary text-white')
    return Markup(f'<span class="badge {css} rounded-pill px-2.5 py-1">{escape(name)}</span>')

def request_status_badge(status_id):
    name = Constants.STATUS_REQUESTS.get(status_id, 'Unknown')
    badge_classes = {
        Constants.STATUS_REQUEST_HQ_REVIEW: 'bg-info text-dark',
        Constants.STATUS_REQUEST_PENDING_ITEMS: 'bg-warning text-dark',
        Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED: 'bg-primary text-white',
        Constants.STATUS_REQUEST_APPROVED: 'bg-success text-white',
        Constants.STATUS_REQUEST_REJECTED: 'bg-danger text-white',
        Constants.STATUS_REQUEST_PUBLISHED: 'bg-dark text-white',
    }
    css = badge_classes.get(status_id, 'bg-secondary text-white')
    return Markup(f'<span class="badge {css} rounded-pill px-2.5 py-1">{escape(name)}</span>')

def task_status_badge(status_id):
    name = Constants.ACTIVITY_LOGS_STATUS.get(status_id, 'Unknown')
    badge_classes = {
        Constants.ACTIVITY_LOGS_STATUS_TO_DO: 'bg-secondary text-white',
        Constants.ACTIVITY_LOGS_STATUS_INVESTIGATION: 'bg-info text-dark',
        Constants.ACTIVITY_LOGS_STATUS_IMPLEMENTATION: 'bg-primary text-white',
        Constants.ACTIVITY_LOGS_STATUS_QA: 'bg-warning text-dark',
        Constants.ACTIVITY_LOGS_STATUS_REVIEW: 'bg-purple text-white' if False else 'bg-warning text-dark',
        Constants.ACTIVITY_LOGS_STATUS_COMPLETED: 'bg-success text-white',
        Constants.ACTIVITY_LOGS_STATUS_BLOCKED: 'bg-danger text-white',
    }
    css = badge_classes.get(status_id, 'bg-secondary text-white')
    return Markup(f'<span class="badge {css} rounded-pill px-2.5 py-1">{escape(name)}</span>')

def priority_badge(priority_id):
    name = Constants.PRIORITIES.get(priority_id, 'Default')
    colors = {
        Constants.PRIORITY_LOW: 'bg-secondary text-white',
        Constants.PRIORITY_MEDIUM: 'bg-primary text-white',
        Constants.PRIORITY_HIGH: 'bg-warning text-dark',
        Constants.PRIORITY_CRITICAL: 'bg-danger text-white',
        Constants.PRIORITY_BLOCKER: 'bg-dark text-danger border border-danger',
    }
    css = colors.get(priority_id, 'bg-secondary text-white')
    return Markup(f'<span class="badge {css} rounded-pill px-2.5 py-1">{escape(name)}</span>')

import hashlib
import time

def status_label(id):
    map_labels = {
        Constants.STATUS_ENABLED: 'Enabled',
        Constants.STATUS_DISABLED: 'Disabled',
        Constants.STATUS_EXPIRED: 'Expired',
        Constants.STATUS_PENDING_VERIFICATION: 'Pending Verification',
        Constants.STATUS_UPDATED_IN_AL: 'Updated in AL',
        Constants.STATUS_NEW_TAG_SUBMITTED: 'New Tag Request Submitted',
        Constants.STATUS_NEW_RULE_SUBMITTED: 'New Rule Request Submitted',
        Constants.STATUS_ON_HOLD: 'On-Hold / Blocked',
        Constants.STATUS_ENDED: 'Ended',
    }
    return map_labels.get(id, 'Unknown')

def status_class(id):
    if id == Constants.STATUS_ENABLED:
        return 'bg-success text-white'
    elif id in [Constants.STATUS_DISABLED, Constants.STATUS_ON_HOLD]:
        return 'bg-danger text-white'
    elif id in [Constants.STATUS_EXPIRED, Constants.STATUS_ENDED, Constants.STATUS_NEW_RULE_SUBMITTED]:
        return 'bg-secondary text-white'
    elif id in [Constants.STATUS_PENDING_VERIFICATION, Constants.STATUS_NEW_TAG_SUBMITTED]:
        return 'bg-warning text-dark'
    elif id == Constants.STATUS_UPDATED_IN_AL:
        return 'bg-info text-dark'
    return 'bg-secondary text-dark'

def status_activity_logs_class(id):
    if id == Constants.ACTIVITY_LOGS_STATUS_TO_DO:
        return 'bg-secondary text-white'
    elif id in [Constants.ACTIVITY_LOGS_STATUS_INVESTIGATION, Constants.ACTIVITY_LOGS_STATUS_IMPLEMENTATION, Constants.ACTIVITY_LOGS_STATUS_REVIEW]:
        return 'bg-warning text-dark'
    elif id == Constants.ACTIVITY_LOGS_STATUS_QA:
        return 'bg-info text-dark'
    elif id == Constants.ACTIVITY_LOGS_STATUS_COMPLETED:
        return 'bg-success text-white'
    elif id == Constants.ACTIVITY_LOGS_STATUS_BLOCKED:
        return 'bg-danger text-white'
    return 'bg-secondary text-white'

def status_request_class(id):
    if id in [Constants.STATUS_REQUEST_HQ_REVIEW, Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED]:
        return 'bg-warning text-dark'
    elif id == Constants.STATUS_REQUEST_PENDING_ITEMS:
        return 'bg-info text-dark'
    elif id in [Constants.STATUS_REQUEST_APPROVED, Constants.STATUS_REQUEST_PUBLISHED]:
        return 'bg-success text-white'
    elif id == Constants.STATUS_REQUEST_REJECTED:
        return 'bg-danger text-white'
    return 'bg-secondary text-dark'

def assignee_class(id):
    if id in [Constants.USER_SYSTEM, Constants.USER_OTHER]:
        return 'bg-secondary text-white'
    elif id == Constants.USER_MARIE:
        return 'bg-purple text-white'
    elif id == Constants.USER_KHRISTINE:
        return 'bg-pink text-white'
    elif id == Constants.USER_LUCKY:
        return 'bg-green text-white'
    elif id == Constants.USER_JANITHA:
        return 'bg-blue text-dark'
    elif id == Constants.USER_GEORGE:
        return 'bg-orange text-dark'
    return 'bg-secondary text-white'

def priority_class(id):
    if id in [Constants.PRIORITY_LOW, Constants.PRIORITY_DEFAULT]:
        return 'bg-secondary text-white'
    elif id == Constants.PRIORITY_MEDIUM:
        return 'bg-warning text-dark'
    elif id in [Constants.PRIORITY_HIGH, Constants.PRIORITY_CRITICAL, Constants.PRIORITY_BLOCKER]:
        return 'bg-danger text-white'
    return 'bg-secondary text-white'

def size_class(id):
    if id == Constants.ACTIVITY_SIZE_S:
        return 'bg-secondary text-white'
    elif id == Constants.ACTIVITY_SIZE_M:
        return 'bg-warning text-dark'
    elif id in [Constants.ACTIVITY_SIZE_L, Constants.ACTIVITY_SIZE_XL, Constants.ACTIVITY_SIZE_SPRINT]:
        return 'bg-danger text-white'
    return 'bg-secondary text-white'

def size_description(id):
    if not id:
        return 'Unknown size'
    descriptions = {
        Constants.ACTIVITY_SIZE_S: 'S (Small): Minor tasks / quick fixes (effort < 2 hours)',
        Constants.ACTIVITY_SIZE_M: 'M (Medium): Standard tag setups / simple troubleshooting (effort: 2-5 hours)',
        Constants.ACTIVITY_SIZE_L: 'L (Large): New tag integrations / complex tracking rules (effort: 1-2 days)',
        Constants.ACTIVITY_SIZE_XL: 'XL (Extra Large): Major property setups / migrations / custom JS (effort: 3-5 days)',
        Constants.ACTIVITY_SIZE_SPRINT: 'Sprint: Massive undertakings / entire sprint effort (effort: 1-2 weeks)',
    }
    return descriptions.get(id, 'Unknown size')

def size_tooltip(id):
    if not id:
        return 'T-Shirt Size'
    tooltips = {
        Constants.ACTIVITY_SIZE_S: 'S: Small task (effort < 2h)',
        Constants.ACTIVITY_SIZE_M: 'M: Medium task (effort 2-5h)',
        Constants.ACTIVITY_SIZE_L: 'L: Large task (effort 1-2d)',
        Constants.ACTIVITY_SIZE_XL: 'XL: Extra Large task (effort 3-5d)',
        Constants.ACTIVITY_SIZE_SPRINT: 'Sprint: Sprint-level effort (effort 1-2w)',
    }
    return tooltips.get(id, 'T-Shirt Size')

def bool_label(value):
    return 'Yes' if value == Constants.YES else 'No'

def bool_class(value):
    return 'bg-success text-white' if value == Constants.YES else 'bg-secondary text-white'

def date_class(dt, status=0):
    if not dt:
        return ''
    if isinstance(dt, str):
        try:
            ts = time.mktime(time.strptime(dt[:10], '%Y-%m-%d'))
        except Exception:
            return 'bg-secondary text-white'
    elif isinstance(dt, (datetime, date)):
        ts = time.mktime(dt.timetuple())
    else:
        return ''

    now = time.time()
    if status == Constants.STATUS_PENDING_VERIFICATION:
        return 'text-danger' if ts < now else 'text-warning'
    elif status == Constants.STATUS_EXPIRED:
        return 'text-muted'
    elif status == Constants.STATUS_DISABLED:
        return 'text-secondary'
    else:
        diff = ts - now
        if diff <= 11 * 86400:
            return 'text-danger'
        elif diff <= 16 * 86400:
            return 'text-warning'
        else:
            return 'text-success'
def diff_days(d):
    if not d:
        return None
    import math
    now = datetime.now()
    if isinstance(d, str):
        clean = d.split()[0]
        try:
            if '-' in clean:
                parts = clean.split('-')
                if len(parts[0]) == 4:
                    dt = datetime.strptime(clean, '%Y-%m-%d')
                else:
                    dt = datetime.strptime(clean, '%d-%m-%Y')
            else:
                return None
        except Exception:
            return None
    elif isinstance(d, date) and not isinstance(d, datetime):
        dt = datetime.combine(d, datetime.min.time())
    elif isinstance(d, datetime):
        dt = d
    else:
        return None
    return int(math.ceil((dt - now).total_seconds() / 86400))

def days_class(days):
    try:
        days = int(days)
    except Exception:
        return ''
    if days <= 11:
        return 'text-danger'
    elif days <= 16:
        return 'text-warning'
    else:
        return 'text-success'

def random_bg_style(value):
    val_str = str(value or '')
    hash_str = hashlib.md5(val_str.encode('utf-8')).hexdigest()
    color = hash_str[:6]
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    brightness = ((r * 299) + (g * 587) + (b * 114)) / 1000
    textColor = 'black' if brightness > 128 else 'white'
    return f"background-color:#{color}; color:{textColor};"

def random_text_style(value):
    val_str = str(value or '')
    hash_str = hashlib.md5(val_str.encode('utf-8')).hexdigest()
    color = hash_str[:6]
    return f"color:#{color};"

def date_ymd(dt=None):
    if not dt:
        return datetime.now().strftime('%Y-%m-%d')
    if isinstance(dt, (datetime, date)):
        return dt.strftime('%Y-%m-%d')
    return str(dt)[:10]

def format_comment_time(dt):
    return time_ago(dt)

def clean_html_comment(html_str):
    if not html_str:
        return ''
    import re
    # Strip script and style tags
    clean = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', str(html_str), flags=re.I)
    clean = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', clean, flags=re.I)
    
    # Format mentions for users
    users_dict = getattr(Constants, 'USERS', {})
    if isinstance(users_dict, dict):
        for user_label in users_dict.values():
            if user_label:
                pattern = re.compile(rf'(^|\s|>)(@{re.escape(str(user_label))})\b', re.IGNORECASE)
                clean = pattern.sub(
                    r'\1<span class="badge bg-primary-subtle text-primary fw-medium px-2 py-1 rounded-pill" style="font-size: 0.8rem;">\2</span>',
                    clean
                )
    return str(clean)

def time_elapsed_string(dt, full=False):
    return time_ago(dt)

def get_system_settings():
    import os
    import json
    from config import Config

    default = {
        'hide_assignee_weekly_reports': True,
        'hide_assignee_system_wide': False,
        'force_me_mode_system_wide': False,
        'flagship_page': '',
        'flagship_buy_page': '',
        'excel_title_c3': '',
        'excel_title_d3': ''
    }

    settings_file = getattr(Config, 'SYSTEM_SETTINGS_FILE', None)
    if settings_file and os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default.update(data)
        except Exception:
            pass

    return default

