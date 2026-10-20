from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, session, jsonify
from sqlalchemy import func, or_, and_, desc
from app.models import db, Tag, TagRequest, ActivityLog, Property, Vendor, User, JiraHistory
from app.constants import Constants
from app.utils.decorators import login_required, permission_required
from app.utils.helpers import status_class, status_activity_logs_class, priority_class

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
@permission_required('dashboard')
def index():
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    date_range = request.args.get('date_range', '30d')
    start_date_param = request.args.get('start_date')
    end_date_param = request.args.get('end_date')

    if date_range == '7d':
        start_date = today - timedelta(days=6)
        end_date = today
    elif date_range == '3m':
        start_date = today - timedelta(days=90)
        end_date = today
    elif date_range == '1y':
        start_date = today - timedelta(days=365)
        end_date = today
    elif date_range == 'custom' and start_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date() if end_date_param else today
        except Exception:
            date_range = '30d'
            start_date = today - timedelta(days=29)
            end_date = today
    else:
        date_range = '30d'
        start_date = today - timedelta(days=29)
        end_date = today

    if end_date > today:
        end_date = today
    if start_date > end_date:
        start_date = end_date

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # User Theme Color
    user_id = session.get('user_id', 0)
    user_color = Constants.get_user_color(user_id)
    hex_color = user_color.lstrip('#')
    user_color_r = int(hex_color[0:2], 16) if len(hex_color) == 6 else 0
    user_color_g = int(hex_color[2:4], 16) if len(hex_color) == 6 else 113
    user_color_b = int(hex_color[4:6], 16) if len(hex_color) == 6 else 227

    # 1. Metric Counts
    active_tags = Tag.countActiveTags()
    expiring_tags = Tag.countExpiringTags()
    pending_verification = Tag.countPendingVerificationTags()
    total_tags = Tag.countAllTags()

    pending_requests = TagRequest.query.filter(
        ~TagRequest.status.in_([
            Constants.STATUS_REQUEST_PUBLISHED,
            Constants.STATUS_REQUEST_REJECTED
        ]),
        TagRequest.deleted_at.is_(None)
    ).count()

    total_requests = TagRequest.query.filter(
        TagRequest.created_at >= start_dt,
        TagRequest.created_at <= end_dt,
        TagRequest.deleted_at.is_(None)
    ).count()

    # System Health Index Calculation
    active_tags_list = Tag.query.filter(
        Tag.status.in_([
            Constants.STATUS_ENABLED,
            Constants.STATUS_UPDATED_IN_AL,
            Constants.STATUS_PENDING_VERIFICATION
        ]),
        Tag.deleted_at.is_(None)
    ).all()

    critical_active = 0
    critical_pending = 0
    attention_active = 0
    attention_pending = 0
    normal_renewal = 0
    safe_tags = 0
    total_penalty = 0.0
    active_tags_count = len(active_tags_list)

    for t in active_tags_list:
        end_d = t.al_end_date
        status = int(t.status or 0)
        if not end_d:
            days_rem = 999
        else:
            if isinstance(end_d, datetime):
                end_d = end_d.date()
            days_rem = (end_d - today).days

        is_pending = (status == Constants.STATUS_PENDING_VERIFICATION)
        if days_rem < 7:
            if is_pending:
                critical_pending += 1
                total_penalty += 0.6 if days_rem < 0 else 0.4
            else:
                critical_active += 1
                total_penalty += 1.0 if days_rem < 0 else 0.8
        elif days_rem < 10:
            if is_pending:
                attention_pending += 1
                total_penalty += 0.15
            else:
                attention_active += 1
                total_penalty += 0.3
        elif days_rem <= 15:
            normal_renewal += 1
        else:
            safe_tags += 1

    if active_tags_count > 0:
        penalty_ratio = total_penalty / active_tags_count
        health_score = int(round(100 * (1 - (penalty_ratio * 10.0))))
        health_score = max(0, min(100, health_score))
    else:
        health_score = 100

    # Dynamic date buckets for line chart
    dates = []
    dates_full = []
    tags_data = {}
    requests_data = {}
    activities_data = {}
    new_rules_data = {}
    pending_data = {}

    cur_dt = start_date
    while cur_dt <= end_date:
        d_str = cur_dt.strftime('%Y-%m-%d')
        dates.append(cur_dt.strftime('%d %b %y'))
        dates_full.append(d_str)
        tags_data[d_str] = 0
        requests_data[d_str] = 0
        activities_data[d_str] = 0
        new_rules_data[d_str] = 0
        pending_data[d_str] = 0
        cur_dt += timedelta(days=1)

    # Ingestion trends queries
    # New Requests: tag_requests where new_tag_ticket is set
    tr_new_tag = TagRequest.query.filter(
        TagRequest.new_tag_ticket.isnot(None),
        TagRequest.new_tag_ticket != '',
        TagRequest.tags.isnot(None),
        TagRequest.tags != '',
        TagRequest.created_at >= start_dt,
        TagRequest.created_at <= end_dt,
        TagRequest.deleted_at.is_(None)
    ).all()
    for tr in tr_new_tag:
        dt_str = tr.created_at.strftime('%Y-%m-%d') if tr.created_at else None
        if dt_str in tags_data:
            tag_count = len([x for x in (tr.tags or '').split(',') if x.strip()])
            tags_data[dt_str] += tag_count

    # New Implementations: tag_requests where new_rule_ticket is set
    tr_new_rule = TagRequest.query.filter(
        TagRequest.new_rule_ticket.isnot(None),
        TagRequest.new_rule_ticket != '',
        TagRequest.tags.isnot(None),
        TagRequest.tags != '',
        TagRequest.created_at >= start_dt,
        TagRequest.created_at <= end_dt,
        TagRequest.deleted_at.is_(None)
    ).all()
    for tr in tr_new_rule:
        dt_str = tr.created_at.strftime('%Y-%m-%d') if tr.created_at else None
        if dt_str in new_rules_data:
            tag_count = len([x for x in (tr.tags or '').split(',') if x.strip()])
            new_rules_data[dt_str] += tag_count

    # Pending Requests: tag_requests where new_tag_ticket is set and new_rule_ticket is empty
    tr_pending = TagRequest.query.filter(
        TagRequest.new_tag_ticket.isnot(None),
        TagRequest.new_tag_ticket != '',
        or_(TagRequest.new_rule_ticket.is_(None), TagRequest.new_rule_ticket == ''),
        TagRequest.tags.isnot(None),
        TagRequest.tags != '',
        TagRequest.created_at >= start_dt,
        TagRequest.created_at <= end_dt,
        TagRequest.deleted_at.is_(None)
    ).all()
    for tr in tr_pending:
        dt_str = tr.created_at.strftime('%Y-%m-%d') if tr.created_at else None
        if dt_str in pending_data:
            tag_count = len([x for x in (tr.tags or '').split(',') if x.strip()])
            pending_data[dt_str] += tag_count

    # Date Extensions: jira_history with type = JIRA_TYPE_DATE_EXTENSION_RULE
    jh_extensions = db.session.query(
        func.date(JiraHistory.created_at).label('d'),
        func.count(JiraHistory.id).label('cnt')
    ).join(Tag, Tag.id == JiraHistory.tag_id).filter(
        JiraHistory.type == Constants.JIRA_TYPE_DATE_EXTENSION_RULE,
        JiraHistory.created_at >= start_dt,
        JiraHistory.created_at <= end_dt,
        Tag.deleted_at.is_(None)
    ).group_by(func.date(JiraHistory.created_at)).all()
    for row in jh_extensions:
        d_str = row.d.strftime('%Y-%m-%d') if isinstance(row.d, date) else str(row.d)
        if d_str in requests_data:
            requests_data[d_str] = int(row.cnt)

    # Activities: activity_logs
    act_counts = db.session.query(
        func.date(ActivityLog.created_at).label('d'),
        func.count(ActivityLog.id).label('cnt')
    ).filter(
        ActivityLog.created_at >= start_dt,
        ActivityLog.created_at <= end_dt,
        ActivityLog.deleted_at.is_(None)
    ).group_by(func.date(ActivityLog.created_at)).all()
    for row in act_counts:
        d_str = row.d.strftime('%Y-%m-%d') if isinstance(row.d, date) else str(row.d)
        if d_str in activities_data:
            activities_data[d_str] = int(row.cnt)

    chart_labels = dates
    chart_labels_full = dates_full
    chart_tags = [tags_data[d] for d in dates_full]
    chart_requests = [requests_data[d] for d in dates_full]
    chart_activities = [activities_data[d] for d in dates_full]
    chart_new_rules = [new_rules_data[d] for d in dates_full]
    chart_pending = [pending_data[d] for d in dates_full]

    # Operations Queue Counts
    blocked_renewal_requests = ActivityLog.query.filter(
        ActivityLog.type == Constants.ACTIVITY_TYPE_RENEWAL,
        ActivityLog.status == Constants.ACTIVITY_LOGS_STATUS_BLOCKED,
        ActivityLog.created_at >= start_dt,
        ActivityLog.created_at <= end_dt,
        ActivityLog.deleted_at.is_(None)
    ).count()

    pending_review_renewals = Tag.query.filter(
        Tag.status == Constants.STATUS_PENDING_VERIFICATION,
        Tag.updated_at >= start_dt,
        Tag.updated_at <= end_dt,
        Tag.deleted_at.is_(None)
    ).count()

    pending_new_tag_requests = TagRequest.query.filter(
        TagRequest.type == Constants.JIRA_TYPE_NEW_TAG,
        ~TagRequest.status.in_([
            Constants.STATUS_REQUEST_PUBLISHED,
            Constants.STATUS_REQUEST_REJECTED,
            Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED
        ]),
        TagRequest.created_at >= start_dt,
        TagRequest.created_at <= end_dt,
        TagRequest.deleted_at.is_(None)
    ).count()

    pending_new_rule_requests = TagRequest.query.filter(
        or_(
            and_(
                TagRequest.type == Constants.JIRA_TYPE_NEW_RULE,
                ~TagRequest.status.in_([
                    Constants.STATUS_REQUEST_PUBLISHED,
                    Constants.STATUS_REQUEST_REJECTED
                ])
            ),
            and_(
                TagRequest.type == Constants.JIRA_TYPE_NEW_TAG,
                TagRequest.status == Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED
            )
        ),
        TagRequest.created_at >= start_dt,
        TagRequest.created_at <= end_dt,
        TagRequest.deleted_at.is_(None)
    ).count()

    # Subsidiary Distribution
    sub_counts = db.session.query(
        Property.subsidiary_id,
        func.count(Tag.id).label('cnt')
    ).join(Property, Property.id == Tag.property_id).filter(
        Tag.deleted_at.is_(None),
        ~Tag.status.in_([
            Constants.STATUS_DISABLED,
            Constants.STATUS_ENDED,
            Constants.STATUS_EXPIRED
        ])
    ).group_by(Property.subsidiary_id).all()

    sub_counts_dict = {row.subsidiary_id: int(row.cnt) for row in sub_counts}
    subsidiary_order = ['SGE', 'SESAR', 'SETK', 'SEIL', 'SEILPS', 'SELV', 'SEEG', 'SEMAG', 'SEPAK']
    for val, label in Constants.SUBSIDIARIES.items():
        if label not in subsidiary_order:
            subsidiary_order.append(label)

    sub_id_by_name = {label: val for val, label in Constants.SUBSIDIARIES.items()}
    subsidiary_labels = []
    subsidiary_data = []
    subsidiary_distribution = {}
    subsidiary_ids = {}
    for label in subsidiary_order:
        val = sub_id_by_name.get(label)
        cnt = sub_counts_dict.get(val, 0)
        subsidiary_labels.append(label)
        subsidiary_data.append(cnt)
        subsidiary_distribution[label] = cnt
        if val is not None:
            subsidiary_ids[label] = val

    # Vendor Distribution (Top 10 highest first)
    vendor_counts = db.session.query(
        Tag.vendor_id,
        Vendor.name.label('vendor_name'),
        func.count(Tag.id).label('cnt')
    ).join(Vendor, Vendor.id == Tag.vendor_id).filter(
        Tag.deleted_at.is_(None),
        ~Tag.status.in_([
            Constants.STATUS_DISABLED,
            Constants.STATUS_ENDED,
            Constants.STATUS_EXPIRED
        ])
    ).group_by(Tag.vendor_id, Vendor.name).order_by(desc('cnt')).limit(10).all()

    vendor_labels = []
    vendor_data = []
    vendor_distribution = {}
    vendor_ids = {}
    for row in vendor_counts:
        v_name = row.vendor_name or 'Unknown'
        cnt = int(row.cnt)
        vendor_labels.append(v_name)
        vendor_data.append(cnt)
        vendor_distribution[v_name] = cnt
        vendor_ids[v_name] = row.vendor_id

    # Expiration Forecast (Next 45 Days)
    forecast_dates = []
    forecast_dates_full = []
    forecast_expiring_data = {}
    forecast_pending_data = {}
    for i in range(45):
        f_date = today + timedelta(days=i)
        f_str = f_date.strftime('%Y-%m-%d')
        forecast_dates.append(f_date.strftime('%d %b'))
        forecast_dates_full.append(f_str)
        forecast_expiring_data[f_str] = 0
        forecast_pending_data[f_str] = 0

    end_forecast = today + timedelta(days=44)
    forecast_query = db.session.query(
        Tag.al_end_date,
        Tag.status,
        func.count(Tag.id).label('cnt')
    ).filter(
        Tag.status.in_([
            Constants.STATUS_ENABLED,
            Constants.STATUS_PENDING_VERIFICATION,
            Constants.STATUS_UPDATED_IN_AL
        ]),
        Tag.al_end_date >= today,
        Tag.al_end_date <= end_forecast,
        Tag.deleted_at.is_(None)
    ).group_by(Tag.al_end_date, Tag.status).all()

    for row in forecast_query:
        if row.al_end_date:
            d_str = row.al_end_date.strftime('%Y-%m-%d') if isinstance(row.al_end_date, (date, datetime)) else str(row.al_end_date)
            if d_str in forecast_expiring_data:
                if int(row.status) == Constants.STATUS_PENDING_VERIFICATION:
                    forecast_pending_data[d_str] += int(row.cnt)
                else:
                    forecast_expiring_data[d_str] += int(row.cnt)

    forecast_data_expiring = [forecast_expiring_data[d] for d in forecast_dates_full]
    forecast_data_pending = [forecast_pending_data[d] for d in forecast_dates_full]

    # Activity Logs Analytics (Status, Priority, Team)
    act_status_counts = db.session.query(
        ActivityLog.status,
        func.count(ActivityLog.id).label('cnt')
    ).filter(
        ActivityLog.created_at >= start_dt,
        ActivityLog.created_at <= end_dt,
        ActivityLog.deleted_at.is_(None)
    ).group_by(ActivityLog.status).all()

    activity_status_distribution = {label: 0 for val, label in Constants.ACTIVITY_LOGS_STATUS.items()}
    for row in act_status_counts:
        label = Constants.ACTIVITY_LOGS_STATUS.get(row.status)
        if label in activity_status_distribution:
            activity_status_distribution[label] += int(row.cnt)

    act_priority_counts = db.session.query(
        ActivityLog.priority,
        func.count(ActivityLog.id).label('cnt')
    ).filter(
        ActivityLog.created_at >= start_dt,
        ActivityLog.created_at <= end_dt,
        ActivityLog.deleted_at.is_(None)
    ).group_by(ActivityLog.priority).all()

    activity_priority_distribution = {label: 0 for val, label in Constants.PRIORITIES.items() if val != Constants.PRIORITY_DEFAULT}
    for row in act_priority_counts:
        label = Constants.PRIORITIES.get(row.priority)
        if label in activity_priority_distribution:
            activity_priority_distribution[label] += int(row.cnt)

    act_team_counts = db.session.query(
        ActivityLog.team_id,
        func.count(ActivityLog.id).label('cnt')
    ).filter(
        ActivityLog.created_at >= start_dt,
        ActivityLog.created_at <= end_dt,
        ActivityLog.deleted_at.is_(None)
    ).group_by(ActivityLog.team_id).all()

    activity_team_distribution = {label: 0 for val, label in Constants.TEAMS.items()}
    for row in act_team_counts:
        label = Constants.TEAMS.get(row.team_id)
        if label in activity_team_distribution:
            activity_team_distribution[label] += int(row.cnt)

    return render_template(
        'dashboard/index.html',
        start_date=start_date_str,
        end_date=end_date_str,
        date_range=date_range,
        active_tags=active_tags,
        expiring_tags=expiring_tags,
        pending_verification=pending_verification,
        total_tags=total_tags,
        pending_requests=pending_requests,
        total_requests=total_requests,
        health_score=health_score,
        critical_active=critical_active,
        critical_pending=critical_pending,
        attention_active=attention_active,
        attention_pending=attention_pending,
        normal_renewal=normal_renewal,
        safe_tags=safe_tags,
        blocked_renewal_requests=blocked_renewal_requests,
        pending_review_renewals=pending_review_renewals,
        pending_new_tag_requests=pending_new_tag_requests,
        pending_new_rule_requests=pending_new_rule_requests,
        chart_labels=chart_labels,
        chart_labels_full=chart_labels_full,
        chart_tags=chart_tags,
        chart_requests=chart_requests,
        chart_activities=chart_activities,
        chart_new_rules=chart_new_rules,
        chart_pending=chart_pending,
        subsidiary_labels=subsidiary_labels,
        subsidiary_data=subsidiary_data,
        subsidiary_distribution=subsidiary_distribution,
        subsidiary_ids=subsidiary_ids,
        vendor_labels=vendor_labels,
        vendor_data=vendor_data,
        vendor_distribution=vendor_distribution,
        vendor_ids=vendor_ids,
        forecast_labels=forecast_dates,
        forecast_labels_full=forecast_dates_full,
        forecast_data_expiring=forecast_data_expiring,
        forecast_data_pending=forecast_data_pending,
        activity_status_distribution=activity_status_distribution,
        activity_priority_distribution=activity_priority_distribution,
        activity_team_distribution=activity_team_distribution,
        user_color=user_color,
        user_color_r=user_color_r,
        user_color_g=user_color_g,
        user_color_b=user_color_b
    )

@dashboard_bp.route('/task-tags')
@login_required
def get_task_tags():
    date_val = request.args.get('date')
    category = request.args.get('category')

    if not date_val or not category:
        return jsonify({'success': False, 'message': 'Missing date or category parameter.'})

    tags = []
    activities = []
    tag_ids = []
    ticket_map = {}

    if category == 'new_requests':
        trs = TagRequest.query.filter(
            TagRequest.new_tag_ticket.isnot(None),
            TagRequest.new_tag_ticket != '',
            TagRequest.tags.isnot(None),
            TagRequest.tags != '',
            func.date(TagRequest.created_at) == date_val,
            TagRequest.deleted_at.is_(None)
        ).all()
        for tr in trs:
            for tid in (tr.tags or '').split(','):
                tid = tid.strip()
                if tid.isdigit():
                    tag_ids.append(int(tid))
                    if tr.new_tag_ticket:
                        ticket_map[int(tid)] = tr.new_tag_ticket

    elif category == 'new_implementations':
        trs = TagRequest.query.filter(
            TagRequest.new_rule_ticket.isnot(None),
            TagRequest.new_rule_ticket != '',
            TagRequest.tags.isnot(None),
            TagRequest.tags != '',
            func.date(TagRequest.created_at) == date_val,
            TagRequest.deleted_at.is_(None)
        ).all()
        for tr in trs:
            for tid in (tr.tags or '').split(','):
                tid = tid.strip()
                if tid.isdigit():
                    tag_ids.append(int(tid))
                    if tr.new_rule_ticket:
                        ticket_map[int(tid)] = tr.new_rule_ticket

    elif category == 'pending_requests':
        trs = TagRequest.query.filter(
            TagRequest.new_tag_ticket.isnot(None),
            TagRequest.new_tag_ticket != '',
            or_(TagRequest.new_rule_ticket.is_(None), TagRequest.new_rule_ticket == ''),
            TagRequest.tags.isnot(None),
            TagRequest.tags != '',
            func.date(TagRequest.created_at) == date_val,
            TagRequest.deleted_at.is_(None)
        ).all()
        for tr in trs:
            for tid in (tr.tags or '').split(','):
                tid = tid.strip()
                if tid.isdigit():
                    tag_ids.append(int(tid))
                    if tr.new_tag_ticket:
                        ticket_map[int(tid)] = tr.new_tag_ticket

    elif category == 'date_extensions':
        jhs = db.session.query(JiraHistory).join(Tag, Tag.id == JiraHistory.tag_id).filter(
            JiraHistory.type == Constants.JIRA_TYPE_DATE_EXTENSION_RULE,
            func.date(JiraHistory.created_at) == date_val,
            Tag.deleted_at.is_(None)
        ).all()
        for jh in jhs:
            if jh.tag_id:
                tag_ids.append(int(jh.tag_id))
                ticket_map[int(jh.tag_id)] = jh.ticket_id

    elif category == 'expiring_tags':
        tg_list = Tag.query.filter(
            Tag.status.in_([Constants.STATUS_ENABLED, Constants.STATUS_UPDATED_IN_AL]),
            func.date(Tag.al_end_date) == date_val,
            Tag.deleted_at.is_(None)
        ).all()
        for tg in tg_list:
            tag_ids.append(tg.id)

    elif category == 'pending_verification_tags':
        tg_list = Tag.query.filter(
            Tag.status == Constants.STATUS_PENDING_VERIFICATION,
            func.date(Tag.al_end_date) == date_val,
            Tag.deleted_at.is_(None)
        ).all()
        for tg in tg_list:
            tag_ids.append(tg.id)

    elif category == 'activities':
        logs = ActivityLog.query.filter(
            func.date(ActivityLog.created_at) == date_val,
            ActivityLog.deleted_at.is_(None)
        ).all()

        ticket_ids = [l.ticket_id for l in logs if l.ticket_id]
        ticket_to_tags = {}

        if ticket_ids:
            tr_matches = TagRequest.query.filter(
                or_(
                    TagRequest.new_tag_ticket.in_(ticket_ids),
                    TagRequest.new_rule_ticket.in_(ticket_ids)
                ),
                TagRequest.deleted_at.is_(None)
            ).all()

            for tr in tr_matches:
                for tid in (tr.tags or '').split(','):
                    tid = tid.strip()
                    if tid.isdigit():
                        tid_int = int(tid)
                        tag_ids.append(tid_int)
                        if tr.new_tag_ticket:
                            ticket_to_tags.setdefault(tr.new_tag_ticket, []).append(tid_int)
                        if tr.new_rule_ticket:
                            ticket_to_tags.setdefault(tr.new_rule_ticket, []).append(tid_int)

        tag_ids = list(set(tag_ids))
        tags_detail = {}
        if tag_ids:
            tg_recs = Tag.query.filter(Tag.id.in_(tag_ids), Tag.deleted_at.is_(None)).all()
            for tg in tg_recs:
                prop = Property.query.get(tg.property_id) if tg.property_id else None
                vend = Vendor.query.get(tg.vendor_id) if tg.vendor_id else None
                sub_label = Constants.SUBSIDIARIES.get(prop.subsidiary_id) if prop else 'Unknown'
                tags_detail[tg.id] = {
                    'id': tg.id,
                    'name': tg.name,
                    'al_end_date': tg.al_end_date.strftime('%Y-%m-%d') if tg.al_end_date else None,
                    'status': tg.status,
                    'status_label': Constants.STATUS.get(tg.status, 'Unknown'),
                    'status_class': status_class(tg.status),
                    'property_name': prop.name if prop else 'N/A',
                    'vendor_name': vend.name if vend else 'N/A',
                    'subsidiary': sub_label,
                    'jira_link': None
                }

        for l in logs:
            log_tags = []
            if l.ticket_id and l.ticket_id in ticket_to_tags:
                for tId in set(ticket_to_tags[l.ticket_id]):
                    if tId in tags_detail:
                        info = dict(tags_detail[tId])
                        info['ticket_id'] = l.ticket_id
                        info['jira_link'] = f"{Constants.JIRA_LINK}{l.ticket_id}"
                        log_tags.append(info)

            activities.append({
                'id': l.id,
                'title': l.title,
                'ticket_id': l.ticket_id,
                'jira_link': f"{Constants.JIRA_LINK}{l.ticket_id}" if l.ticket_id else None,
                'status': Constants.ACTIVITY_LOGS_STATUS.get(l.status, 'Unknown'),
                'status_class': status_activity_logs_class(l.status),
                'priority': Constants.PRIORITIES.get(l.priority, 'Unknown'),
                'priority_class': priority_class(l.priority),
                'tags': log_tags
            })

    tag_ids = list(set(tag_ids))
    if category != 'activities' and tag_ids:
        tg_records = Tag.query.filter(Tag.id.in_(tag_ids), Tag.deleted_at.is_(None)).all()
        for tg in tg_records:
            prop = Property.query.get(tg.property_id) if tg.property_id else None
            vend = Vendor.query.get(tg.vendor_id) if tg.vendor_id else None
            sub_label = Constants.SUBSIDIARIES.get(prop.subsidiary_id) if prop else 'Unknown'
            t_ticket = ticket_map.get(tg.id)
            tags.append({
                'id': tg.id,
                'name': tg.name,
                'al_end_date': tg.al_end_date.strftime('%Y-%m-%d') if tg.al_end_date else None,
                'status': tg.status,
                'status_label': Constants.STATUS.get(tg.status, 'Unknown'),
                'status_class': status_class(tg.status),
                'property_name': prop.name if prop else 'N/A',
                'vendor_name': vend.name if vend else 'N/A',
                'subsidiary': sub_label,
                'ticket_id': t_ticket,
                'jira_link': f"{Constants.JIRA_LINK}{t_ticket}" if t_ticket else None
            })

    try:
        parsed_d = datetime.strptime(date_val, '%Y-%m-%d')
        formatted_date = parsed_d.strftime('%d %b %Y')
    except Exception:
        formatted_date = date_val

    return jsonify({
        'success': True,
        'date': formatted_date,
        'category': category,
        'tags': tags,
        'activities': activities
    })

@dashboard_bp.route('/welcome-message')
@login_required
def get_welcome_message():
    user_name = session.get('user_name') or session.get('name') or 'User'
    user_id = session.get('user_id', 0)
    user_role = session.get('user_role', 1)
    team_name = Constants.TEAMS.get(Constants.USER_TEAMS.get(user_id), 'Media Tagging')

    in_progress_tasks = ActivityLog.query.filter(
        ActivityLog.assignee == user_id,
        ActivityLog.status.in_([
            Constants.ACTIVITY_LOGS_STATUS_INVESTIGATION,
            Constants.ACTIVITY_LOGS_STATUS_IMPLEMENTATION,
            Constants.ACTIVITY_LOGS_STATUS_QA,
            Constants.ACTIVITY_LOGS_STATUS_REVIEW
        ]),
        ActivityLog.deleted_at.is_(None)
    ).count()

    blocked_tasks = ActivityLog.query.filter(
        ActivityLog.assignee == user_id,
        ActivityLog.status == Constants.ACTIVITY_LOGS_STATUS_BLOCKED,
        ActivityLog.deleted_at.is_(None)
    ).count()

    todo_tasks = ActivityLog.query.filter(
        ActivityLog.assignee == user_id,
        ActivityLog.status == Constants.ACTIVITY_LOGS_STATUS_TO_DO,
        ActivityLog.deleted_at.is_(None)
    ).count()

    today = date.today()
    expiring_tags = Tag.query.filter(
        Tag.status.in_([
            Constants.STATUS_ENABLED,
            Constants.STATUS_UPDATED_IN_AL,
            Constants.STATUS_PENDING_VERIFICATION
        ]),
        Tag.al_end_date <= (today + timedelta(days=15)),
        Tag.deleted_at.is_(None)
    ).count()

    now = datetime.now()
    if now.hour < 12:
        greeting = 'Good morning'
    elif now.hour < 17:
        greeting = 'Good afternoon'
    else:
        greeting = 'Good evening'

    day_name = now.strftime('%A')
    fallback_message = f"{greeting}, {user_name}! Happy {day_name}! You have {in_progress_tasks} task(s) in progress, {blocked_tasks} blocked, and {todo_tasks} to do. \"Believe you can and you're halfway there.\" - Theodore Roosevelt 🌟 Let's tackle today's goals with energy!"
    if expiring_tags > 0:
        fallback_message += f" Please be reminded that there are {expiring_tags} tags expiring in the next 15 days."

    user_color = Constants.get_user_color(user_id)
    return jsonify({
        'success': True,
        'message': fallback_message,
        'user_color': user_color
    })
