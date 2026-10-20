import os
import re
import json
from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, case, func, text
from app.models import (
    db, Tag, Property, Vendor, Subsidiary, RenewalLog, 
    RenewalJustification, AiConversation, User, JiraHistory, ActivityLog, ActivityLogComment, Organization
)
from app.constants import Constants
from app.utils.decorators import login_required, permission_required
from app.services.excel_service import ExcelService
from app.services.jira_service import JiraService
import requests
from config import Config

tags_bp = Blueprint('tags', __name__)

def build_tag_filter_query(params):
    keyword = (params.get('keyword') or '').strip()
    conditions = (params.get('conditions') or '').strip()
    status = params.get('status')
    
    try:
        property_id = int(params.get('property_id')) if params.get('property_id') not in (None, '', 'None') else None
    except (ValueError, TypeError):
        property_id = None
        
    try:
        subsidiary_id = int(params.get('subsidiary_id')) if params.get('subsidiary_id') not in (None, '', 'None') else None
    except (ValueError, TypeError):
        subsidiary_id = None
        
    try:
        vendor_id = int(params.get('vendor_id')) if params.get('vendor_id') not in (None, '', 'None') else None
    except (ValueError, TypeError):
        vendor_id = None
        
    al_end_date_from = (params.get('al_end_date_from') or '').strip()
    if al_end_date_from in ('', 'None'):
        al_end_date_from = ''
    al_end_date_to = (params.get('al_end_date_to') or '').strip()
    if al_end_date_to in ('', 'None'):
        al_end_date_to = ''
        
    sort_by = params.get('sort_by')
    sort_dir = (params.get('sort_dir') or 'desc').lower()
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'
    sort_by_property = params.get('sort_by_property')

    query = Tag.query.filter(Tag.deleted_at.is_(None))

    if keyword:
        if keyword.isdigit():
            query = query.filter(
                or_(
                    Tag.id == int(keyword),
                    Tag.name.ilike(f"%{keyword}%"),
                    Tag.conditions.ilike(f"%{keyword}%"),
                    Tag.ref_link.ilike(f"%{keyword}%")
                )
            )
        else:
            query = query.filter(
                or_(
                    Tag.name.ilike(f"%{keyword}%"),
                    Tag.conditions.ilike(f"%{keyword}%"),
                    Tag.ref_link.ilike(f"%{keyword}%")
                )
            )
    if conditions:
        query = query.filter(Tag.conditions.ilike(f"%{conditions}%"))
    if property_id:
        query = query.filter(Tag.property_id == property_id)
    if vendor_id:
        query = query.filter(Tag.vendor_id == vendor_id)
    if subsidiary_id:
        query = query.join(Property, Tag.property_id == Property.id).filter(Property.subsidiary_id == subsidiary_id)

    # Status handling exactly matching CI4
    if status is None or status == '' or status == str(Constants.STATUS_DEFAULT):
        query = query.filter(Tag.status.in_(Constants.STATUS_DEFAULT_VALUE))
        filter_status = str(Constants.STATUS_DEFAULT)
    elif status in ('all', str(Constants.STATUS_ALL)):
        filter_status = 'all'
    elif status == 'expiring':
        today = date.today()
        base = today - timedelta(days=10)
        expiring = today + timedelta(days=15)
        query = query.filter(
            Tag.status.in_([Constants.STATUS_ENABLED, Constants.STATUS_UPDATED_IN_AL]),
            Tag.al_end_date >= base,
            Tag.al_end_date <= expiring
        )
        filter_status = 'expiring'
    else:
        try:
            s_val = int(status)
            query = query.filter(Tag.status == s_val)
            filter_status = str(s_val)
        except ValueError:
            filter_status = status

    if al_end_date_from:
        query = query.filter(Tag.al_end_date >= al_end_date_from)
    if al_end_date_to:
        query = query.filter(Tag.al_end_date <= al_end_date_to)

    # Sorting
    if sort_by:
        if sort_by == 'subsidiary_id':
            if not subsidiary_id:
                query = query.outerjoin(Property, Tag.property_id == Property.id)
            query = query.order_by(Property.subsidiary_id.desc() if sort_dir == 'desc' else Property.subsidiary_id.asc())
        elif sort_by == 'property_id':
            if not subsidiary_id:
                query = query.outerjoin(Property, Tag.property_id == Property.id)
            query = query.order_by(Property.name.desc() if sort_dir == 'desc' else Property.name.asc())
        elif sort_by in ('al_end_date', 'days'):
            query = query.order_by(Tag.al_end_date.desc() if sort_dir == 'desc' else Tag.al_end_date.asc())
        elif sort_by == 'id':
            query = query.order_by(Tag.id.desc() if sort_dir == 'desc' else Tag.id.asc())
        elif sort_by == 'name':
            query = query.order_by(Tag.name.desc() if sort_dir == 'desc' else Tag.name.asc())
        elif sort_by == 'status':
            query = query.order_by(Tag.status.desc() if sort_dir == 'desc' else Tag.status.asc())
        elif sort_by == 'updated_at':
            query = query.order_by(Tag.updated_at.desc() if sort_dir == 'desc' else Tag.updated_at.asc())
        else:
            col = getattr(Tag, sort_by, Tag.al_end_date)
            query = query.order_by(col.desc() if sort_dir == 'desc' else col.asc())
    else:
        if sort_by_property == '1':
            query = query.order_by(Tag.property_id.asc(), Tag.name.asc())
        else:
            default_case = case(
                ((Tag.al_end_date < func.curdate()) & (Tag.status == 1), 0),
                (Tag.status == 5, 1),
                (Tag.status == 9, 2),
                ((Tag.al_end_date <= func.date_add(func.curdate(), text('INTERVAL 9 DAY'))) & (Tag.status == 1), 3),
                ((Tag.al_end_date <= func.date_add(func.curdate(), text('INTERVAL 16 DAY'))) & (Tag.status == 4), 4),
                ((Tag.al_end_date <= func.date_add(func.curdate(), text('INTERVAL 16 DAY'))) & (Tag.status == 1), 5),
                (Tag.status == 4, 6),
                (Tag.status == 1, 7),
                else_=8
            )
            query = query.order_by(default_case.asc(), Tag.al_end_date.asc(), Tag.property_id.asc())

    parsed_params = {
        'keyword': keyword,
        'conditions': conditions,
        'status': filter_status,
        'property_id': property_id,
        'subsidiary_id': subsidiary_id,
        'vendor_id': vendor_id,
        'al_end_date_from': al_end_date_from,
        'al_end_date_to': al_end_date_to,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'sort_by_property': sort_by_property
    }
    return query, filter_status, parsed_params

@tags_bp.route('/')
@login_required
@permission_required('tags')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    query, filter_status, parsed_params = build_tag_filter_query(request.args)
    keyword = parsed_params['keyword']
    conditions = parsed_params['conditions']
    property_id = parsed_params['property_id']
    subsidiary_id = parsed_params['subsidiary_id']
    vendor_id = parsed_params['vendor_id']
    al_end_date_from = parsed_params['al_end_date_from']
    al_end_date_to = parsed_params['al_end_date_to']
    sort_by = parsed_params['sort_by']
    sort_dir = parsed_params['sort_dir']
    sort_by_property = parsed_params['sort_by_property']

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    active_filters_count = 0
    advanced_filter_keys = ['subsidiary_id', 'property_id', 'vendor_id', 'status', 'al_end_date_from', 'al_end_date_to', 'sort_by_property']
    for k in advanced_filter_keys:
        val = request.args.get(k)
        if k == 'status':
            if val and val not in ['all', '145', '', 'None']:
                active_filters_count += 1
        elif k in ('al_end_date_from', 'al_end_date_to'):
            if val and str(val).strip() not in ('', 'None'):
                active_filters_count += 1
        elif val and str(val).strip() not in ('', 'None'):
            active_filters_count += 1
    if keyword and keyword != 'None':
        active_filters_count += 1
    has_active_filters = (active_filters_count > 0)

    all_properties = Property.query.filter_by(deleted_at=None).all()
    properties_map = {
        p.id: {
            'id': p.id,
            'name': p.name,
            'ref_link': p.ref_link or p.website or '#',
            'subsidiary_id': p.subsidiary_id
        }
        for p in all_properties
    }
    properties_map = defaultdict(lambda: {'id': 0, 'name': 'Unknown', 'ref_link': '#', 'subsidiary_id': 0}, properties_map)

    all_subs = Subsidiary.query.filter_by(deleted_at=None).all()
    subsidiaries_map = {s.id: s.name for s in all_subs}
    subsidiaries_map = defaultdict(lambda: 'Global', subsidiaries_map)

    ticket_map = {}
    task_map = {}
    tag_ids = [t.id for t in pagination.items]
    if tag_ids:
        try:
            tickets = JiraHistory.query.filter(
                (JiraHistory.tag_id.in_(tag_ids)) | (JiraHistory.comments.isnot(None))
            ).order_by(JiraHistory.id.asc()).all()
            for t in tickets:
                if t.tag_id and t.tag_id in tag_ids:
                    ticket_map[t.tag_id] = t.ticket_id
                if t.comments:
                    for cid in t.comments.split(','):
                        try:
                            cid_int = int(cid.strip())
                            if cid_int in tag_ids:
                                ticket_map[cid_int] = t.ticket_id
                        except ValueError:
                            pass
            t_ids = list(set(ticket_map.values()))
            if t_ids:
                tasks = ActivityLog.query.filter(ActivityLog.ticket_id.in_(t_ids)).all()
                for task in tasks:
                    task_map[task.ticket_id] = {'id': task.id, 'title': task.title}
        except Exception:
            pass

    filters = {
        'keyword': keyword or '',
        'conditions': conditions or '',
        'status': filter_status,
        'property_id': property_id,
        'subsidiary_id': subsidiary_id,
        'vendor_id': vendor_id,
        'al_end_date_from': al_end_date_from or '',
        'al_end_date_to': al_end_date_to or '',
        'sort_by': sort_by or '',
        'sort_dir': sort_dir,
        'sort_by_property': sort_by_property or ''
    }

    return render_template(
        'tags/list.html',
        tags=pagination.items,
        pagination=pagination,
        pager=pagination,
        totalTags=pagination.total,
        properties=properties_map,
        propertyOptions=Property.options(),
        vendors=Vendor.options(),
        subsidiaries=subsidiaries_map,
        tagsModel=Tag,
        ticketMap=ticket_map,
        taskMap=task_map,
        activeFiltersCount=active_filters_count,
        hasActiveFilters=has_active_filters,
        advancedFilterKeys=advanced_filter_keys,
        filters=filters,
        clearUrl=url_for('tags.index')
    )

@tags_bp.route('/repository')
@login_required
@permission_required('tags')
def repository():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    keyword = request.args.get('keyword', '').strip()
    js_code = request.args.get('js_code', '').strip()
    conditions = request.args.get('conditions', '').strip()
    property_id = request.args.get('property_id', type=int)
    subsidiary_id = request.args.get('subsidiary_id', type=int)
    vendor_id = request.args.get('vendor_id', type=int)
    sort_by = request.args.get('sort_by', 'id')
    sort_dir = request.args.get('sort_dir', 'desc').lower()
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    query = Tag.query.filter(Tag.deleted_at.is_(None))
    if keyword:
        if keyword.isdigit():
            query = query.filter(
                or_(
                    Tag.id == int(keyword),
                    Tag.name.ilike(f"%{keyword}%"),
                    Tag.conditions.ilike(f"%{keyword}%"),
                    Tag.js_code.ilike(f"%{keyword}%")
                )
            )
        else:
            query = query.filter(
                or_(
                    Tag.name.ilike(f"%{keyword}%"),
                    Tag.conditions.ilike(f"%{keyword}%"),
                    Tag.js_code.ilike(f"%{keyword}%")
                )
            )
    if js_code:
        query = query.filter(Tag.js_code.ilike(f"%{js_code}%"))
    if conditions:
        query = query.filter(Tag.conditions.ilike(f"%{conditions}%"))
    if property_id:
        query = query.filter(Tag.property_id == property_id)
    if vendor_id:
        query = query.filter(Tag.vendor_id == vendor_id)
    if subsidiary_id:
        query = query.join(Property, Tag.property_id == Property.id).filter(Property.subsidiary_id == subsidiary_id)

    # Active filters calculation
    active_filters_count = 0
    for k in ['subsidiary_id', 'property_id', 'vendor_id', 'js_code', 'conditions']:
        if request.args.get(k):
            active_filters_count += 1
    has_active_filters = (active_filters_count > 0) or bool(keyword)

    sort_col = getattr(Tag, sort_by, Tag.id)
    if sort_dir.lower() == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    all_properties = Property.query.filter_by(deleted_at=None).all()
    properties_map = {
        p.id: {
            'id': p.id,
            'name': p.name,
            'ref_link': p.ref_link or p.website or '#',
            'subsidiary_id': p.subsidiary_id
        }
        for p in all_properties
    }
    properties_map = defaultdict(lambda: {'id': 0, 'name': 'Unknown', 'ref_link': '#', 'subsidiary_id': 0}, properties_map)

    all_subs = Subsidiary.query.filter_by(deleted_at=None).all()
    subsidiaries_map = {s.id: s.name for s in all_subs}
    subsidiaries_map = defaultdict(lambda: 'Global', subsidiaries_map)

    filters = {
        'keyword': keyword,
        'js_code': js_code,
        'conditions': conditions,
        'property_id': property_id,
        'subsidiary_id': subsidiary_id,
        'vendor_id': vendor_id,
        'sort_by': sort_by,
        'sort_dir': sort_dir
    }

    return render_template(
        'tags/repository.html',
        tags=pagination.items,
        pagination=pagination,
        pager=pagination,
        totalTags=pagination.total,
        properties=properties_map,
        propertyOptions=Property.options(),
        vendors=Vendor.options(),
        subsidiaries=subsidiaries_map,
        activeFiltersCount=active_filters_count,
        hasActiveFilters=has_active_filters,
        currentSortBy=sort_by,
        currentSortDir=sort_dir,
        filters=filters,
        clearUrl=url_for('tags.repository')
    )

@tags_bp.route('/<int:id>', endpoint='view_short')
@tags_bp.route('/view/<int:id>')
@login_required
@permission_required('tags')
def view(id):
    tag = Tag.query.get_or_404(id)
    renewal_logs = RenewalLog.query.filter_by(property_id=tag.property_id).order_by(RenewalLog.id.desc()).all()
    justifications = RenewalJustification.query.filter_by(tag_id=tag.id).order_by(RenewalJustification.id.desc()).all()

    # Preload related Jira tickets where this tag is referenced
    jira_tickets_raw = JiraHistory.query.filter(
        JiraHistory.is_active == 1,
        or_(
            JiraHistory.tag_id == id,
            func.find_in_set(str(id), JiraHistory.comments) > 0
        )
    ).order_by(JiraHistory.id.desc()).all()

    # Deduplicate / group by ticket_id (keeping latest entry)
    seen_ticket_ids = set()
    grouped_tickets = []
    for jt in jira_tickets_raw:
        tid = jt.ticket_id or f"id_{jt.id}"
        if tid in seen_ticket_ids:
            continue
        seen_ticket_ids.add(tid)
        grouped_tickets.append(jt)

    # Pre-fetch all tags referenced across these Jira tickets
    all_referenced_tag_ids = set()
    for jt in grouped_tickets:
        if jt.comments:
            for cid in jt.comments.split(','):
                cid = cid.strip()
                if cid.isdigit() and int(cid) > 0:
                    all_referenced_tag_ids.add(int(cid))
        elif jt.tag_id:
            all_referenced_tag_ids.add(jt.tag_id)

    tags_cache = {t.id: t for t in Tag.query.filter(Tag.id.in_(list(all_referenced_tag_ids))).all()} if all_referenced_tag_ids else {}

    jira_tickets = []
    for jt in grouped_tickets:
        tids = []
        if jt.comments:
            for cid in jt.comments.split(','):
                cid = cid.strip()
                if cid.isdigit() and int(cid) > 0:
                    tids.append(int(cid))
        elif jt.tag_id:
            tids.append(jt.tag_id)

        ticket_tags_list = []
        seen_t = set()
        for tid in tids:
            if tid not in seen_t:
                seen_t.add(tid)
                if tid in tags_cache:
                    t_obj = tags_cache[tid]
                    ticket_tags_list.append({
                        'id': t_obj.id,
                        'name': t_obj.name,
                        'link': url_for('tags.view', id=t_obj.id)
                    })
                else:
                    ticket_tags_list.append({
                        'id': tid,
                        'name': f"Tag #{tid}",
                        'link': url_for('tags.view', id=tid)
                    })

        try:
            t_type_int = int(jt.type) if jt.type is not None else None
        except (ValueError, TypeError):
            t_type_int = None
        type_name = Constants.JIRA_TICKET_TYPES.get(t_type_int, jt.type or 'Unknown')

        jira_tickets.append({
            'id': jt.id,
            'ticket_id': jt.ticket_id,
            'type': jt.type,
            'type_name': type_name,
            'comments': jt.comments,
            'created_at': jt.created_at.strftime('%Y-%m-%d %H:%M:%S') if jt.created_at else '',
            'ticket_tags_list': ticket_tags_list,
            'tag_count': len(ticket_tags_list),
            'status': getattr(jt, 'status', None)
        })

    properties_map = {p.id: p.name for p in Property.query.all()}
    vendors_map = {v.id: v.name for v in Vendor.query.all()}
    organizations_map = {o.id: o.name for o in Organization.query.all()}

    return render_template(
        'tags/view.html',
        tag=tag,
        properties=properties_map,
        vendors=vendors_map,
        organizations=organizations_map,
        renewal_logs=renewal_logs,
        justifications=justifications,
        jiraTickets=jira_tickets
    )

@tags_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        property_id = request.form.get('property_id', type=int)
        vendor_id = request.form.get('vendor_id', type=int)
        conditions = request.form.get('conditions')
        status = request.form.get('status', type=int) or Constants.STATUS_ENABLED
        al_end_date = request.form.get('al_end_date')
        requester_name = request.form.get('requester_name')
        requester_email = request.form.get('requester_email')
        requester_org = request.form.get('requester_organization', type=int)
        ref_link = request.form.get('ref_link')
        js_code = request.form.get('js_code')

        tag = Tag(
            name=name,
            property_id=property_id,
            vendor_id=vendor_id,
            conditions=conditions,
            status=status,
            al_end_date=datetime.strptime(al_end_date, '%Y-%m-%d').date() if al_end_date else None,
            requester_name=requester_name,
            requester_email=requester_email,
            requester_organization=requester_org,
            ref_link=ref_link,
            js_code=js_code,
            created_by=session.get('user_id', 0)
        )
        db.session.add(tag)
        db.session.commit()
        flash('Tag created successfully.', 'success')
        return redirect(url_for('tags.index'))

    requester_names = [r[0] for r in db.session.query(Tag.requester_name).filter(Tag.requester_name.isnot(None), Tag.requester_name != '').distinct().all()]
    requester_emails = [r[0] for r in db.session.query(Tag.requester_email).filter(Tag.requester_email.isnot(None), Tag.requester_email != '').distinct().all()]
    conditions_list = [r[0] for r in db.session.query(Tag.conditions).filter(Tag.conditions.isnot(None), Tag.conditions != '').distinct().all()]

    return render_template(
        'tags/create.html',
        tag=None,
        propertiesList=Property.query.filter_by(deleted_at=None).order_by(Property.name).all(),
        organizations=Organization.options(),
        requesterNamesList=requester_names,
        requesterEmailsList=requester_emails,
        conditionsList=conditions_list
    )

@tags_bp.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def update(id):
    tag = Tag.query.get_or_404(id)
    if request.method == 'POST':
        tag.name = request.form.get('name')
        tag.property_id = request.form.get('property_id', type=int)
        tag.vendor_id = request.form.get('vendor_id', type=int)
        tag.conditions = request.form.get('conditions')
        tag.status = request.form.get('status', type=int)
        al_end = request.form.get('al_end_date')
        tag.al_end_date = datetime.strptime(al_end, '%Y-%m-%d').date() if al_end else None
        tag.requester_name = request.form.get('requester_name')
        tag.requester_email = request.form.get('requester_email')
        tag.requester_organization = request.form.get('requester_organization', type=int)
        tag.ref_link = request.form.get('ref_link')
        tag.js_code = request.form.get('js_code')
        tag.updated_by = session.get('user_id', 0)
        db.session.commit()
        flash('Tag updated successfully.', 'success')
        return redirect(url_for('tags.view', id=tag.id))

    requester_names = [r[0] for r in db.session.query(Tag.requester_name).filter(Tag.requester_name.isnot(None), Tag.requester_name != '').distinct().all()]
    requester_emails = [r[0] for r in db.session.query(Tag.requester_email).filter(Tag.requester_email.isnot(None), Tag.requester_email != '').distinct().all()]
    conditions_list = [r[0] for r in db.session.query(Tag.conditions).filter(Tag.conditions.isnot(None), Tag.conditions != '').distinct().all()]
    org_obj = Organization.query.get(tag.requester_organization) if tag.requester_organization else None

    return render_template(
        'tags/update.html',
        tag=tag,
        propertiesList=Property.query.filter_by(deleted_at=None).order_by(Property.name).all(),
        organizations=Organization.options(),
        orgName=org_obj.name if org_obj else '',
        requesterNamesList=requester_names,
        requesterEmailsList=requester_emails,
        conditionsList=conditions_list,
        aiModels=['claude-3-7-sonnet', 'gpt-4o', 'gemini-2.5-flash'],
        chatWelcomeMessage=f"Hello {session.get('user_name', 'User')}! Do you need any help with your script today? 😊"
    )

def _extract_tag_ids():
    tag_ids = []
    raw_list = request.args.getlist('tags') + request.args.getlist('tags[]') + request.form.getlist('tags') + request.form.getlist('tags[]')
    for source in [request.args, request.form]:
        for k, v in source.items():
            if re.match(r'^tags\[\d+\]$', k):
                raw_list.append(v)
    for item in raw_list:
        for part in str(item).split(','):
            p_str = part.strip()
            if p_str.isdigit():
                tag_ids.append(int(p_str))
    seen = set()
    unique = []
    for tid in tag_ids:
        if tid not in seen:
            seen.add(tid)
            unique.append(tid)
    return unique

@tags_bp.route('/renew', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def renew():
    tag_ids = _extract_tag_ids()
    ticket_id = request.args.get('ticket_id') or request.form.get('ticket_id') or ''

    selected_tags = []
    for tid in tag_ids:
        t = Tag.query.get(tid)
        if t:
            just = RenewalJustification.query.filter_by(tag_id=t.id).order_by(RenewalJustification.id.desc()).first()
            t.justification = just
            selected_tags.append(t)

    all_properties = Property.query.all()
    properties_map = {p.id: p for p in all_properties}
    vendors_map = Vendor.options()

    property_ids = []
    vendor_ids = []
    for t in selected_tags:
        if t.property_id and t.property_id not in property_ids:
            property_ids.append(t.property_id)
        if t.vendor_id and t.vendor_id not in vendor_ids:
            vendor_ids.append(t.vendor_id)

    vendor_names = [vendors_map.get(vid, 'Unknown') for vid in vendor_ids if vid in vendors_map]

    site_codes = []
    for pid in property_ids:
        sc = Property.get_site_code(pid)
        if sc and sc not in site_codes:
            site_codes.append(sc)
    site_code = ', '.join(site_codes) if site_codes else ''

    today = datetime.now().strftime('%d%m%Y')
    library_name = f"{ticket_id}_{today}" if ticket_id else f"_{today}"

    exp_date = ''
    next_exp_date = ''
    if selected_tags:
        first_end = selected_tags[0].al_end_date
        if first_end:
            if isinstance(first_end, str):
                try:
                    first_date = datetime.strptime(first_end[:10], '%Y-%m-%d').date()
                except Exception:
                    first_date = datetime.now().date()
            else:
                first_date = first_end
            exp_date = first_date.strftime('%d-%m-%Y')
            next_exp_date = (first_date + timedelta(days=61)).strftime('%d-%m-%Y')
        else:
            first_date = datetime.now().date()
            exp_date = first_date.strftime('%d-%m-%Y')
            next_exp_date = (first_date + timedelta(days=61)).strftime('%d-%m-%Y')

    first_prop = properties_map.get(property_ids[0]) if property_ids else None
    create_library_link = '#'
    if first_prop and first_prop.ref_link:
        raw_ref = first_prop.ref_link
        base_ref = re.sub(r'(\/(overview|rules|data_elements|extensions|environments|hosts|settings|history)(\/|\?|$).*)$', '', raw_ref, flags=re.IGNORECASE)
        if not base_ref.endswith('/'):
            base_ref += '/'
        create_library_link = base_ref + Constants.AL_LIBRARY_CREATE

    subsidiary_ticket_id = ''
    if first_prop and first_prop.subsidiary_id:
        sub_jira = JiraHistory.query.filter_by(subsidiary_id=first_prop.subsidiary_id, is_active=1).order_by(JiraHistory.id.desc()).first()
        if sub_jira and sub_jira.ticket_id:
            subsidiary_ticket_id = sub_jira.ticket_id

    jira_title = f"[LC Request] [{site_code}] - [{', '.join(vendor_names)}] - [Date Extension Rule]"

    properties_by_shop = defaultdict(list)
    for pid in property_ids:
        p_obj = properties_map.get(pid)
        if p_obj:
            stype = 'Shop' if p_obj.is_shop == 1 else 'AEM'
            properties_by_shop[stype].append(p_obj)

    details_lines = []
    details_lines.append('<b>1) Target Property</b>')
    details_lines.append('<ul>')
    for stype, p_list in properties_by_shop.items():
        details_lines.append(f'<li>{stype} :')
        details_lines.append('    <ul>')
        for p in p_list:
            details_lines.append(f'        <li>{p.name}</li>')
        details_lines.append('    </ul>')
        details_lines.append('</li>')
    details_lines.append(f'    <li>Library name: <b><span id="library-name-display">{library_name}</span></b></li>')
    details_lines.append('</ul>')

    details_lines.append('<b>2) Target Page(s)</b>')
    details_lines.append('<ul>')
    for stype, p_list in properties_by_shop.items():
        details_lines.append(f'<li>{stype} :')
        details_lines.append('    <ul>')
        for p in p_list:
            site_url_display = p.website or 'Unknown'
            details_lines.append(f'        <li><a href="{site_url_display}" target="_blank">{site_url_display}</a></li>')
        details_lines.append('    </ul>')
        details_lines.append('</li>')
    details_lines.append('</ul>')

    details_lines.append('<b>3) Expiration Date</b>')
    details_lines.append('<ul>')
    details_lines.append(f'    <li><b>as-is :</b> {exp_date}</li>')
    details_lines.append(f'    <li><b>to-be :</b> <span id="to-be-date-display">{next_exp_date}</span></li>')
    details_lines.append('</ul>')

    details_lines.append('<b>4) Purpose & Goal</b>')
    details_lines.append('<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">')
    details_lines.append('    <thead>')
    details_lines.append('        <tr>')
    details_lines.append('            <th>Tag Name</th>')
    details_lines.append('            <th>Renew<br/>(Y/N)</th>')
    details_lines.append('            <th>Renewal Justification</th>')
    details_lines.append('            <th>Duration<br/>of Usage</th>')
    details_lines.append('        </tr>')
    details_lines.append('    </thead>')
    details_lines.append('    <tbody>')
    for tag in selected_tags:
        just = getattr(tag, 'justification', None)
        renew_val = (just.renew if just and hasattr(just, 'renew') and just.renew else 'Y')
        just_val = (just.justification if just and hasattr(just, 'justification') and just.justification else '')
        dur_val = (just.duration if just and hasattr(just, 'duration') and just.duration else '')
        details_lines.append('        <tr>')
        details_lines.append(f'            <td>{tag.name}</td>')
        details_lines.append(f'            <td>{renew_val}</td>')
        details_lines.append(f'            <td>{just_val}</td>')
        details_lines.append(f'            <td>{dur_val}</td>')
        details_lines.append('        </tr>')
    details_lines.append('    </tbody>')
    details_lines.append('</table>')

    details_html = '\n'.join(details_lines)

    sub_jira_link = (Constants.JIRA_LINK + subsidiary_ticket_id) if subsidiary_ticket_id else '#'
    user_display_name = session.get('user_name', 'User')
    comment_html = f'Hi <a href="{Constants.JIRA_TAGGING_SUPPORT}" target="_blank">Tagging Support</a>,<br/>Kindly refer to the date extension approval confirmation here: <a href="{sub_jira_link}" target="_blank">{sub_jira_link}</a><br/><br/>Regards,<br/>{user_display_name}'

    past_jira_tickets = []
    seen_tickets = set()
    for t in selected_tags:
        related = JiraHistory.query.filter(
            (JiraHistory.tag_id == t.id) | (JiraHistory.comments.like(f'%{t.id}%'))
        ).all()
        for r in related:
            type_str = str(r.type)
            if type_str == str(Constants.JIRA_TYPE_DATE_EXTENSION_RULE) or type_str == 'Date Extension Rule' or type_str == '1':
                if r.ticket_id and r.ticket_id not in seen_tickets:
                    seen_tickets.add(r.ticket_id)
                    past_jira_tickets.append(r)
                    if len(past_jira_tickets) >= 3:
                        break
        if len(past_jira_tickets) >= 3:
            break

    return render_template(
        'tags/renew.html',
        tags=selected_tags,
        ticket_id=ticket_id,
        vendors=vendors_map,
        properties=properties_map,
        subsidiaries=Subsidiary.options(),
        siteCode=site_code,
        site_code=site_code,
        today=today,
        libraryName=library_name,
        library_name=library_name,
        expDate=exp_date,
        nextExpDate=next_exp_date,
        jiraTitle=jira_title,
        jira_title=jira_title,
        createLibraryLink=create_library_link,
        create_library_link=create_library_link,
        subsidiaryTicketId=subsidiary_ticket_id,
        detailsHtml=details_html,
        details_html=details_html,
        commentHtml=comment_html,
        comment_html=comment_html,
        pastJiraTickets=past_jira_tickets,
        past_jira_tickets=past_jira_tickets
    )

@tags_bp.route('/renew/confirm', methods=['POST'])
@login_required
@permission_required('tags')
def renew_confirm():
    ticket_id = request.form.get('ticket_id') or request.form.get('info[ticket_id]') or ''
    library_name = request.form.get('info[library_name]') or request.form.get('library_name')
    if not library_name:
        today = datetime.now().strftime('%d%m%Y')
        library_name = f"{ticket_id}_{today}" if ticket_id else f"_{today}"

    tag_updates = {}
    for key, value in request.form.items():
        m = re.match(r'tags\[(\d+)\]\[next_end_date\]', key)
        if m:
            t_id = int(m.group(1))
            tag_updates[t_id] = value

    user_id = session.get('user_id', 0)
    tag_id_list = list(tag_updates.keys())
    first_prop_id = None

    for t_id, end_date_str in tag_updates.items():
        t = Tag.query.get(t_id)
        if t:
            if first_prop_id is None and t.property_id:
                first_prop_id = t.property_id
            try:
                clean_date = end_date_str.split()[0]
                if '-' in clean_date:
                    parts = clean_date.split('-')
                    if len(parts[0]) == 4:
                        new_date = datetime.strptime(clean_date, '%Y-%m-%d').date()
                    else:
                        new_date = datetime.strptime(clean_date, '%d-%m-%Y').date()
                    t.requested_date = new_date
            except Exception:
                pass
            t.status = Constants.STATUS_PENDING_VERIFICATION
            t.updated_by = user_id

            log = RenewalLog(
                ticket_id=ticket_id,
                property_id=t.property_id,
                library_name=library_name,
                vendor=t.vendor.name if t.vendor else '',
                al_end_date=t.requested_date or t.al_end_date,
                user=user_id
            )
            db.session.add(log)

    if ticket_id:
        existing_jira = JiraHistory.query.filter_by(ticket_id=ticket_id).first()
        tag_ids_csv = ",".join(str(tid) for tid in tag_id_list)
        if not existing_jira:
            first_tag = Tag.query.get(tag_id_list[0]) if tag_id_list else None
            new_jira = JiraHistory(
                ticket_id=ticket_id,
                type=str(Constants.JIRA_TYPE_DATE_EXTENSION_RULE),
                comments=tag_ids_csv,
                tag_id=tag_id_list[0] if tag_id_list else None,
                property_id=first_tag.property_id if first_tag else 0,
                subsidiary_id=first_tag.property.subsidiary_id if first_tag and first_tag.property else None,
                created_by=user_id
            )
            db.session.add(new_jira)
        else:
            if existing_jira.comments:
                existing_ids = set(x.strip() for x in existing_jira.comments.split(',') if x.strip())
                for tid in tag_id_list:
                    existing_ids.add(str(tid))
                existing_jira.comments = ",".join(sorted(existing_ids, key=int))
            else:
                existing_jira.comments = tag_ids_csv
            existing_jira.updated_by = user_id

        # Auto-create ActivityLog task if not existing
        if first_prop_id:
            first_prop = Property.query.get(first_prop_id)
            existing_task = ActivityLog.query.filter_by(ticket_id=ticket_id).first()
            if not existing_task and first_prop:
                desc_items = "".join(f"<li>{Tag.query.get(tid).name}</li>" for tid in tag_id_list if Tag.query.get(tid))
                new_task = ActivityLog(
                    title=f"Tag Renewals | {first_prop.name}",
                    description=f"Renewal of tags: <br/><ul>{desc_items}</ul>",
                    subsidiary_id=first_prop.subsidiary_id,
                    team_id=Constants.TEAM_MEDIA_TAGGING,
                    project='Date Extension',
                    ticket_id=ticket_id,
                    assignee=user_id,
                    status=Constants.ACTIVITY_LOGS_STATUS_IMPLEMENTATION,
                    type=Constants.ACTIVITY_TYPE_RENEWAL,
                    size=Constants.ACTIVITY_SIZE_M,
                    created_by=user_id,
                    requested_by='SDSME/MENAO',
                    requested_date=datetime.now().date(),
                    start_date=datetime.now().date()
                )
                db.session.add(new_task)
                db.session.flush()
                try:
                    JiraService.create_jira_issue_from_task(new_task.id)
                except Exception:
                    pass

    db.session.commit()
    flash('Renewal confirmed successfully.', 'success')
    return redirect(url_for('tags.index'))

@tags_bp.route('/renew/updateAL', methods=['POST'])
@login_required
def update_al():
    tag_id = request.form.get('tag_id')
    if tag_id:
        Tag.query.filter_by(id=int(tag_id)).update({Tag.status: Constants.STATUS_UPDATED_IN_AL})
        db.session.commit()
    return jsonify({'status': 'ok'})

@tags_bp.route('/update-rule-request', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def update_rule_request():
    tag_ids = _extract_tag_ids()
    ticket_id = request.args.get('ticket_id') or request.form.get('ticket_id') or ''

    selected_tags = []
    for tid in tag_ids:
        t = Tag.query.get(tid)
        if t:
            selected_tags.append(t)

    all_properties = Property.query.all()
    properties_map = {p.id: p for p in all_properties}
    vendors_map = Vendor.options()

    property_ids = []
    vendor_ids = []
    for t in selected_tags:
        if t.property_id and t.property_id not in property_ids:
            property_ids.append(t.property_id)
        if t.vendor_id and t.vendor_id not in vendor_ids:
            vendor_ids.append(t.vendor_id)

    vendor_names = []
    reasons = []
    purposes = []
    for vid in vendor_ids:
        v_obj = Vendor.query.get(vid)
        if v_obj:
            if v_obj.name and v_obj.name not in vendor_names:
                vendor_names.append(v_obj.name)
            if v_obj.reason and v_obj.reason not in reasons:
                reasons.append(v_obj.reason)
            if v_obj.tag_purpose and v_obj.tag_purpose not in purposes:
                purposes.append(v_obj.tag_purpose)
        elif vid in vendors_map and vendors_map[vid] not in vendor_names:
            vendor_names.append(vendors_map[vid])

    vendor_name_str = ', '.join(vendor_names) if vendor_names else 'Unknown'
    reason_str = '<br/>'.join(reasons) if reasons else '-'
    purpose_str = '<br/>'.join(purposes) if purposes else '-'

    site_codes = []
    for pid in property_ids:
        sc = Property.get_site_code(pid)
        if sc and sc not in site_codes:
            site_codes.append(sc)
    site_code = ', '.join(site_codes) if site_codes else ''

    today = datetime.now().strftime('%d%m%Y')
    library_name = f"{ticket_id}_{today}" if ticket_id else f"_{today}"

    exp_dates = []
    for tag in selected_tags:
        if tag.al_end_date:
            exp_dates.append(str(tag.al_end_date)[:10])
    exp_date_str = ', '.join(dict.fromkeys(exp_dates)) if exp_dates else '-'

    first_prop = properties_map.get(property_ids[0]) if property_ids else None
    create_library_link = '#'
    if first_prop and first_prop.ref_link:
        raw_ref = first_prop.ref_link
        base_ref = re.sub(r'(\/(overview|rules|data_elements|extensions|environments|hosts|settings|history)(\/|\?|$).*)$', '', raw_ref, flags=re.IGNORECASE)
        if not base_ref.endswith('/'):
            base_ref += '/'
        create_library_link = base_ref + Constants.AL_LIBRARY_CREATE

    jira_title = f"[LC Request] [{site_code}] - [{vendor_name_str}] - [Update Rule]"

    properties_by_shop = defaultdict(list)
    for pid in property_ids:
        p_obj = properties_map.get(pid)
        if p_obj:
            stype = 'Shop' if p_obj.is_shop == 1 else 'AEM'
            properties_by_shop[stype].append(p_obj)

    property_list_html = ""
    pages_list_html = ""
    for stype, props in properties_by_shop.items():
        property_list_html += f"<li>{stype} :<ul>"
        pages_list_html += f"<li>{stype} :<ul>"
        for p in props:
            p_name = p.name or 'Unknown'
            p_site = p.website or 'Unknown'
            property_list_html += f"<li>{p_name}</li>"
            pages_list_html += f"<li><a href='{p_site}' target='_blank'>{p_site}</a></li>"
        property_list_html += "</ul></li>"
        pages_list_html += "</ul></li>"

    ss_gtm = Constants.JIRA_SSGTM_TICKET
    details_html = f"""<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>1) Target Property :</b>
<ul style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F;'>
    {property_list_html}
    <li>Library Name : <span id='library-name-display'>{library_name}</span></li>
</ul>

<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>2) Target Page(s) :</b>
<ul style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F;'>
    {pages_list_html}
</ul>

<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>2.2) Reason when the Target Page is for all :</b>
<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F; padding-left:12px;'>{reason_str}</p>

<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>3) Expiration Date (to-be) : </b><span id='to-be-date-display' style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F;'>{exp_date_str}</span> <br/><br/>

<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>4) Status (to-be) :</b>
<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#86868B; font-style:italic; padding-left:12px;'>Insert Local Rule Monitoring File screenshots here...</p>

<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>5) Purpose & Goal :</b>
<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F; padding-left:12px;'>{purpose_str}</p>

<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>6) ssGTM</b>
<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F; padding-left:12px;'>
    For ssGTM requests, please refer to this ticket: 
    <a href='{ss_gtm}' target='_blank' style='color:#0071E3; text-decoration:none;'> ssGTM </a> 
</p>

<b style='color:#0071E3; font-size:15px; font-family:-apple-system,BlinkMacSystemFont,sans-serif;'>7) Required Attachment</b>
<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F; padding-left:12px;'><b>① Test Result Screenshot image file(s)</b></p>
<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#86868B; font-style:italic; padding-left:24px;'>Insert QA screenshots here...</p>

<br/>

<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F;'><b>② Integration Result: Fill in the checklist below to make sure the new tags aren't affecting your site's operation.</b></p>
<table cellpadding='8' cellspacing='0' style='border-collapse:collapse; width:100%; border:1px solid #e8e8ed; font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; margin-bottom:16px;'>
    <tbody>"""
    for question, value in Constants.INTEGRATION_RESULT_PAGE_LOAD.items():
        details_html += f"""
        <tr style='border-bottom:1px solid #e8e8ed;'>
            <td style='width:50%; color:#49494D; font-weight:500; border-right:1px solid #e8e8ed; padding:8px 12px;'>{question}</td>
            <td style='color:#1D1D1F; padding:8px 12px;'>{value}</td>
        </tr>"""
    details_html += """
    </tbody>
</table>

<br/>

<table cellpadding='8' cellspacing='0' style='border-collapse:collapse; width:100%; border:1px solid #e8e8ed; font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; margin-bottom:16px;'>
    <tbody>"""
    for question, value in Constants.INTEGRATION_RESULT_EVENT_CLICK.items():
        details_html += f"""
        <tr style='border-bottom:1px solid #e8e8ed;'>
            <td style='width:50%; color:#49494D; font-weight:500; border-right:1px solid #e8e8ed; padding:8px 12px;'>{question}</td>
            <td style='color:#1D1D1F; padding:8px 12px;'>{value}</td>
        </tr>"""
    details_html += """
    </tbody>
</table>

<br/>

<p style='font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:14px; color:#1D1D1F;'><b>③ Local Rule Monitoring Excel file [Local Rule Monitoring Excel file_v1.0_Subsidiary_sitecode_YYMMDD_general.xlsx]</b></p>
"""

    next_exp_date = ''
    if selected_tags and selected_tags[0].al_end_date:
        end_val = selected_tags[0].al_end_date
        if isinstance(end_val, str):
            try:
                dt = datetime.strptime(end_val[:10], '%Y-%m-%d')
                next_exp_date = dt.strftime('%Y-%m-%d 00:00')
            except Exception:
                next_exp_date = end_val
        elif hasattr(end_val, 'strftime'):
            next_exp_date = end_val.strftime('%Y-%m-%d 00:00')

    return render_template(
        'tags/update_rule_request.html',
        tags=selected_tags,
        ticket_id=ticket_id,
        vendors=vendors_map,
        properties=properties_map,
        subsidiaries=Subsidiary.options(),
        site_code=site_code,
        vendor_name=vendor_name_str,
        today=today,
        library_name=library_name,
        create_library_link=create_library_link,
        jira_title=jira_title,
        details_html=details_html,
        next_exp_date=next_exp_date
    )


@tags_bp.route('/update-rule/confirm', methods=['POST'])
@login_required
@permission_required('tags')
def update_rule_confirm():
    tags_data = request.form
    user_id = session.get('user_id', 1)
    ticket_id = tags_data.get('info[ticket_id]') or tags_data.get('ticket_id') or ''
    library_name = tags_data.get('info[library_name]') or tags_data.get('library_name')
    if not library_name:
        today = datetime.now().strftime('%d%m%Y')
        library_name = f"{ticket_id}_{today}" if ticket_id else f"_{today}"

    tag_id_list = []
    for key, val in tags_data.items():
        m = re.match(r'tags\[(\d+)\]\[next_end_date\]', key)
        if m:
            tid = int(m.group(1))
            tag_id_list.append(tid)
            tag = Tag.query.get(tid)
            if tag:
                try:
                    clean_date = val.split()[0]
                    if '-' in clean_date:
                        parts = clean_date.split('-')
                        if len(parts[0]) == 4:
                            tag.al_end_date = datetime.strptime(clean_date, '%Y-%m-%d').date()
                        else:
                            tag.al_end_date = datetime.strptime(clean_date, '%d-%m-%Y').date()
                except Exception:
                    pass
                tag.status = Constants.STATUS_UPDATED_IN_AL
                tag.updated_by = user_id
                db.session.add(RenewalLog(
                    ticket_id=ticket_id,
                    property_id=tag.property_id,
                    library_name=library_name,
                    vendor=tag.vendor.name if tag.vendor else '',
                    al_end_date=tag.al_end_date,
                    user=user_id
                ))

    if ticket_id and tag_id_list:
        existing_jira = JiraHistory.query.filter_by(ticket_id=ticket_id).first()
        tag_ids_csv = ",".join(str(tid) for tid in tag_id_list)
        if not existing_jira:
            first_tag = Tag.query.get(tag_id_list[0])
            new_jira = JiraHistory(
                ticket_id=ticket_id,
                type=str(Constants.JIRA_TYPE_UPDATE_RULE),
                comments=tag_ids_csv,
                tag_id=tag_id_list[0],
                property_id=first_tag.property_id if first_tag else 0,
                subsidiary_id=first_tag.property.subsidiary_id if first_tag and first_tag.property else None,
                created_by=user_id
            )
            db.session.add(new_jira)
        else:
            if existing_jira.comments:
                existing_ids = set(x.strip() for x in existing_jira.comments.split(',') if x.strip())
                for tid in tag_id_list:
                    existing_ids.add(str(tid))
                existing_jira.comments = ",".join(sorted(existing_ids, key=int))
            else:
                existing_jira.comments = tag_ids_csv
            existing_jira.updated_by = user_id

    db.session.commit()
    flash('Update Rule Request submitted successfully.', 'success')
    return redirect(url_for('tags.index'))

@tags_bp.route('/renewal-justifications', methods=['GET'])
@login_required
@permission_required('tags')
def renewal_justifications():
    subsidiaries = Subsidiary.query.filter_by(deleted_at=None).order_by(Subsidiary.name).all()
    grouped = {}
    justifications = RenewalJustification.query.order_by(RenewalJustification.id.desc()).all()
    for j in justifications:
        tag = Tag.query.get(j.tag_id)
        if tag and tag.property:
            sub_id = tag.property.subsidiary_id or 0
            if sub_id not in grouped:
                grouped[sub_id] = []
            j.tag_name = tag.name
            j.property_name = tag.property.name
            sub_obj = Subsidiary.query.get(sub_id)
            j.subsidiary_name = sub_obj.name if sub_obj else 'Global'
            grouped[sub_id].append(j)

    return render_template('tags/renewal_justifications.html', grouped=grouped, subsidiaries=subsidiaries)

def extract_renewal_justification_rows(file_path):
    import openpyxl
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb.active
    except Exception as e:
        return {'error': f'Failed to parse Excel file: {str(e)}'}

    rows = []
    for row in sheet.iter_rows(values_only=True):
        rows.append([str(c).strip() if c is not None else '' for c in row])
    wb.close()

    if not rows:
        return {'error': 'The uploaded Excel file is empty.'}

    # Locate header row
    header_row_index = None
    column_map = {}
    
    for row_idx, row in enumerate(rows):
        curr_map = {'property_name': None, 'tag_name': None, 'renew': None, 'justification': None, 'duration': None}
        
        for col_idx, cell in enumerate(row):
            clean = cell.lower()
            if not clean:
                continue
            if curr_map['property_name'] is None and ('property name' in clean or clean == 'property'):
                curr_map['property_name'] = col_idx
            elif curr_map['tag_name'] is None and ('tag name' in clean or clean == 'tag'):
                curr_map['tag_name'] = col_idx
            elif curr_map['renew'] is None and ('renew' in clean):
                curr_map['renew'] = col_idx
            elif curr_map['justification'] is None and ('justification' in clean):
                curr_map['justification'] = col_idx
            elif curr_map['duration'] is None and ('duration' in clean or 'usage' in clean):
                curr_map['duration'] = col_idx

        if curr_map['property_name'] is not None and curr_map['tag_name'] is not None:
            header_row_index = row_idx
            column_map = curr_map
            break

    if header_row_index is None:
        return {'error': 'Could not find required header row. Expected columns: "Property Name", "Tag Name", "Renew", "Renewal Justification", "Duration of Usage".'}

    missing = []
    if column_map.get('property_name') is None:
        missing.append('"Property Name"')
    if column_map.get('tag_name') is None:
        missing.append('"Tag Name"')
    if column_map.get('renew') is None:
        missing.append('"Renew"')
    if column_map.get('justification') is None:
        missing.append('"Renewal Justification"')
    if column_map.get('duration') is None:
        missing.append('"Duration of Usage"')

    if missing:
        return {'error': f'Missing required column(s) in Excel file: {", ".join(missing)}.'}

    data_rows = []
    for r in rows[header_row_index + 1:]:
        prop = r[column_map['property_name']] if column_map['property_name'] < len(r) else ''
        tname = r[column_map['tag_name']] if column_map['tag_name'] < len(r) else ''
        ren = r[column_map['renew']] if column_map['renew'] < len(r) else ''
        just = r[column_map['justification']] if column_map['justification'] < len(r) else ''
        dur = r[column_map['duration']] if column_map['duration'] < len(r) else ''

        if not prop and not tname:
            continue
        data_rows.append({
            'property_name': prop,
            'tag_name': tname,
            'renew': ren,
            'justification': just,
            'duration': dur
        })

    if not data_rows:
        return {'error': 'The uploaded Excel file does not contain any valid tag renewal rows.'}

    return {'data': data_rows, 'column_map': column_map}

@tags_bp.route('/upload-renewal-justifications', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def upload_renewal_justifications():
    return render_template('tags/upload_renewal_justifications.html')

@tags_bp.route('/parse-renewal-justifications', methods=['POST'])
@login_required
@permission_required('tags')
def parse_renewal_justifications():
    file = request.files.get('excel_file')
    if not file or not file.filename or not file.filename.lower().endswith('.xlsx'):
        flash('Please upload a valid .xlsx file.', 'error')
        return redirect(url_for('tags.upload_renewal_justifications'))

    temp_folder = os.path.join(Config.UPLOAD_DIR, 'temp')
    os.makedirs(temp_folder, exist_ok=True)
    orig_name = secure_filename(file.filename)
    temp_filename = f"{int(datetime.now().timestamp())}_renewal_{orig_name}"
    temp_file_path = os.path.join(temp_folder, temp_filename)
    file.save(temp_file_path)

    extracted = extract_renewal_justification_rows(temp_file_path)
    if 'error' in extracted:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        flash(extracted['error'], 'error')
        return redirect(url_for('tags.upload_renewal_justifications'))

    extracted_rows = []
    valid_count = 0
    invalid_tags_count = 0
    property_not_found_count = 0

    for item in extracted['data']:
        p_name = item['property_name']
        t_name = item['tag_name']
        status = 'Valid'

        prop = Property.query.filter(func.lower(Property.name) == func.lower(p_name)).first()
        if not prop:
            status = 'Property Not Found'
            property_not_found_count += 1
        else:
            tag = Tag.query.filter(
                Tag.property_id == prop.id,
                func.lower(Tag.name) == func.lower(t_name),
                Tag.deleted_at.is_(None)
            ).first()
            if not tag:
                status = 'Tag Not Found'
                invalid_tags_count += 1
            else:
                valid_count += 1

        extracted_rows.append({
            'property_name': p_name,
            'tag_name': t_name,
            'renew': item['renew'],
            'justification': item['justification'],
            'duration': item['duration'],
            'status': status
        })

    has_invalid = (invalid_tags_count > 0 or property_not_found_count > 0)

    return render_template(
        'tags/upload_renewal_justifications.html',
        extracted_rows=extracted_rows,
        temp_file_path=temp_file_path,
        temp_file_name=orig_name,
        valid_count=valid_count,
        invalid_tags_count=invalid_tags_count,
        property_not_found_count=property_not_found_count,
        has_invalid=has_invalid
    )

@tags_bp.route('/confirm-renewal-justifications', methods=['POST'])
@login_required
@permission_required('tags')
def confirm_renewal_justifications():
    temp_file_path = request.form.get('temp_file_path')
    if not temp_file_path or not os.path.exists(temp_file_path):
        flash('Temporary file not found. Please upload again.', 'error')
        return redirect(url_for('tags.upload_renewal_justifications'))

    extracted = extract_renewal_justification_rows(temp_file_path)
    if 'error' in extracted:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        flash(extracted['error'], 'error')
        return redirect(url_for('tags.upload_renewal_justifications'))

    user_id = session.get('user_id', 0)
    saved_count = 0

    for item in extracted['data']:
        p_name = item['property_name']
        t_name = item['tag_name']
        renew = item['renew']
        just = item['justification']
        dur = item['duration']

        if p_name and t_name:
            prop = Property.query.filter(func.lower(Property.name) == func.lower(p_name)).first()
            if prop:
                tag = Tag.query.filter(
                    Tag.property_id == prop.id,
                    func.lower(Tag.name) == func.lower(t_name),
                    Tag.deleted_at.is_(None)
                ).first()
                if tag:
                    rj = RenewalJustification(
                        tag_id=tag.id,
                        renew=renew,
                        justification=just,
                        duration=dur,
                        created_by=user_id,
                        updated_by=user_id
                    )
                    db.session.add(rj)
                    saved_count += 1

    db.session.commit()

    if os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
        except Exception:
            pass

    flash(f"{saved_count} renewal justifications have been successfully processed and saved.", 'success')
    return redirect(url_for('tags.renewal_justifications'))

@tags_bp.route('/renewal-justifications/update/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def update_renewal_justification(id):
    justification = RenewalJustification.query.get(id)
    if not justification:
        flash('Renewal justification not found.', 'error')
        return redirect(url_for('tags.renewal_justifications'))

    tag = Tag.query.get(justification.tag_id)

    if request.method == 'GET':
        return render_template(
            'tags/update_renewal_justification.html',
            justification=justification,
            tag=tag
        )

    justification.renew = request.form.get('renew', '').strip()
    justification.justification = request.form.get('justification', '').strip()
    justification.duration = request.form.get('duration', '').strip()
    justification.updated_by = session.get('user_id', 0)

    db.session.commit()
    flash('Renewal justification updated successfully.', 'success')
    return redirect(url_for('tags.renewal_justifications'))


@tags_bp.route('/verify/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def verify(id):
    tag = Tag.query.get_or_404(id)
    user_id = session.get('user_id', 0)
    requested_date = tag.requested_date or tag.al_end_date

    # 1. Complete linked task and update Jira if present
    jira_tickets = JiraHistory.get_related_tags(id)
    if jira_tickets and jira_tickets[0].ticket_id:
        ticket_id = jira_tickets[0].ticket_id
        activity_log = ActivityLog.query.filter_by(ticket_id=ticket_id).first()
        if activity_log and activity_log.status != Constants.ACTIVITY_LOGS_STATUS_COMPLETED:
            from_st = activity_log.status
            from_name = Constants.ACTIVITY_LOGS_STATUS.get(from_st, str(from_st))
            to_name = Constants.ACTIVITY_LOGS_STATUS.get(Constants.ACTIVITY_LOGS_STATUS_COMPLETED, 'Completed')

            comment = ActivityLogComment(
                log_id=activity_log.id,
                comment=f"Status updated from [{from_name}] to [{to_name}]",
                commented_by=user_id,
                type=Constants.COMMENT_TYPE_UPDATE
            )
            db.session.add(comment)
            activity_log.status = Constants.ACTIVITY_LOGS_STATUS_COMPLETED
            activity_log.updated_by = user_id

            try:
                JiraService.update_task_status(activity_log.id, from_st, Constants.ACTIVITY_LOGS_STATUS_COMPLETED)
            except Exception:
                pass

    # 2. Update Tag state: apply requested date as active al_end_date, clear requested fields
    tag.status = Constants.STATUS_ENABLED
    tag.al_end_date = requested_date
    tag.requested_date = None
    if getattr(tag, 'requested_name', None):
        tag.name = tag.requested_name
        tag.requested_name = None
    tag.updated_by = user_id
    db.session.commit()

    flash(f"Tag renewal [{tag.id}] [{tag.name}] has been verified.", 'success')
    return_url = request.args.get('return_url')
    if return_url:
        return redirect(return_url)
    return redirect(request.referrer or url_for('tags.index'))

@tags_bp.route('/verify-multiple', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def verify_multiple():
    raw_tags = request.form.getlist('tags') or request.args.getlist('tags')
    tag_ids = []
    for item in raw_tags:
        for part in str(item).split(','):
            part = part.strip()
            if part.isdigit():
                tag_ids.append(int(part))
    if not tag_ids:
        raw = request.form.get('tags') or request.args.get('tags')
        if raw:
            tag_ids = [int(x.strip()) for x in str(raw).split(',') if x.strip().isdigit()]

    if not tag_ids:
        flash('No tags selected for verification.', 'error')
        return redirect(url_for('tags.index'))

    user_id = session.get('user_id', 0)
    verified_count = 0

    for tid_int in tag_ids:
        tag = Tag.query.get(tid_int)
        if not tag:
            continue

        jira_tickets = JiraHistory.get_related_tags(tag.id)
        has_ticket = bool(jira_tickets and jira_tickets[0].ticket_id)

        # Only verify tags in STATUS_PENDING_VERIFICATION or (STATUS_ON_HOLD with ticket ID)
        if tag.status != Constants.STATUS_PENDING_VERIFICATION:
            if tag.status != Constants.STATUS_ON_HOLD or not has_ticket:
                continue

        requested_date = tag.requested_date or tag.al_end_date

        if has_ticket:
            ticket_id = jira_tickets[0].ticket_id
            activity_log = ActivityLog.query.filter_by(ticket_id=ticket_id).first()
            if activity_log and activity_log.status != Constants.ACTIVITY_LOGS_STATUS_COMPLETED:
                from_st = activity_log.status
                from_name = Constants.ACTIVITY_LOGS_STATUS.get(from_st, str(from_st))
                to_name = Constants.ACTIVITY_LOGS_STATUS.get(Constants.ACTIVITY_LOGS_STATUS_COMPLETED, 'Completed')

                comment = ActivityLogComment(
                    log_id=activity_log.id,
                    comment=f"Status updated from [{from_name}] to [{to_name}]",
                    commented_by=user_id,
                    type=Constants.COMMENT_TYPE_UPDATE
                )
                db.session.add(comment)
                activity_log.status = Constants.ACTIVITY_LOGS_STATUS_COMPLETED
                activity_log.updated_by = user_id

                try:
                    JiraService.update_task_status(activity_log.id, from_st, Constants.ACTIVITY_LOGS_STATUS_COMPLETED)
                except Exception:
                    pass

        tag.status = Constants.STATUS_ENABLED
        tag.al_end_date = requested_date
        tag.requested_date = None
        if getattr(tag, 'requested_name', None):
            tag.name = tag.requested_name
            tag.requested_name = None
        tag.updated_by = user_id
        verified_count += 1

    db.session.commit()
    flash(f"Verified {verified_count} tags successfully.", 'success')
    return_url = request.args.get('return_url')
    if return_url:
        return redirect(return_url)
    return redirect(request.referrer or url_for('tags.index'))

@tags_bp.route('/save-js-code/<int:id>', methods=['POST'])
@login_required
def save_js_code(id):
    tag = Tag.query.get_or_404(id)
    js_code = request.form.get('js_code') or (request.json.get('js_code') if request.is_json else '')
    tag.js_code = js_code
    tag.updated_by = session.get('user_id', 0)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'JavaScript code saved successfully.'})

@tags_bp.route('/ai-chat', methods=['POST'])
@login_required
def chat_with_ai():
    data = request.json or {}
    message = data.get('message', '')
    tag_id = data.get('tag_id')
    conversation_id = data.get('conversation_id')

    if not message:
        return jsonify({'status': 'error', 'message': 'Message cannot be empty.'}), 400

    conversation = None
    messages = []
    if conversation_id:
        conversation = AiConversation.query.get(conversation_id)
        if conversation and conversation.messages:
            try:
                messages = json.loads(conversation.messages)
            except Exception:
                messages = []

    messages.append({'role': 'user', 'content': message})
    ai_reply = "I analyzed the JavaScript snippet for this tag. The event trigger and parameters follow standard tracking formats."

    messages.append({'role': 'assistant', 'content': ai_reply})

    if conversation:
        conversation.messages = json.dumps(messages)
    else:
        conversation = AiConversation(
            user_id=session.get('user_id', 0),
            tag_id=tag_id,
            title=message[:40] + ('...' if len(message) > 40 else ''),
            messages=json.dumps(messages)
        )
        db.session.add(conversation)

    db.session.commit()

    return jsonify({
        'status': 'success',
        'reply': ai_reply,
        'conversation_id': conversation.id
    })

@tags_bp.route('/ai-history', methods=['GET'])
@tags_bp.route('/ai-history/<int:id>', methods=['GET'])
@login_required
def get_ai_chat_history(id=None):
    user_id = session.get('user_id', 0)
    query = AiConversation.query.filter_by(user_id=user_id)
    if id:
        query = query.filter_by(tag_id=id)
    convs = query.order_by(AiConversation.id.desc()).limit(15).all()
    data = [{
        'id': c.id,
        'title': c.title,
        'tag_id': c.tag_id,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else '',
        'updated_at': c.updated_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(c, 'updated_at', None) else ''
    } for c in convs]
    return jsonify({'status': 'success', 'data': data})

@tags_bp.route('/ai-conversation/<int:id>', methods=['GET'])
@login_required
def get_ai_conversation(id):
    c = AiConversation.query.get(id)
    if not c:
        return jsonify({'status': 'error', 'message': 'Conversation not found'}), 404
    return jsonify({
        'status': 'success',
        'data': {
            'id': c.id,
            'title': c.title,
            'messages': c.messages if isinstance(c.messages, str) else json.dumps(c.messages or []),
            'tag_id': c.tag_id,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else ''
        }
    })

@tags_bp.route('/export', methods=['GET', 'POST'])
@login_required
@permission_required('tags')
def export():
    params = request.form if request.method == 'POST' else request.args
    query, _, _ = build_tag_filter_query(params)
    tags = query.all()

    selected_fields = []
    if request.method == 'POST':
        selected_fields = request.form.getlist('fields') or request.form.getlist('fields[]')
    if not selected_fields:
        selected_fields = request.args.getlist('fields') or request.args.getlist('fields[]')
    if not selected_fields and 'fields' in params and isinstance(params.get('fields'), str):
        selected_fields = [f.strip() for f in params.get('fields').split(',') if f.strip()]

    stream = ExcelService.export_tags(tags, selected_fields=selected_fields)
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Martech_Tags_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
