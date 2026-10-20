import os
import json
from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_
from app.models import (
    db, TagRequest, TagRequestFile, Property, Vendor, Subsidiary, Organization, Tag, ActivityLog, JiraHistory
)
from app.constants import Constants
from app.utils.decorators import login_required, permission_required
from app.services.excel_service import ExcelService
from config import Config

tag_requests_bp = Blueprint('tag_requests', __name__)

@tag_requests_bp.route('/')
@login_required
@permission_required('tag-requests')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status')
    property_id = request.args.get('property_id', type=int)
    vendor_id = request.args.get('vendor_id', type=int)
    subsidiary_id = request.args.get('subsidiary_id', type=int)
    req_type = request.args.get('type', type=int)
    created_at_from = request.args.get('created_at_from')
    created_at_to = request.args.get('created_at_to')

    query = TagRequest.query.filter(TagRequest.deleted_at.is_(None))

    if keyword:
        if keyword.isdigit():
            query = query.filter(
                or_(
                    TagRequest.id == int(keyword),
                    TagRequest.new_tag_ticket.ilike(f"%{keyword}%"),
                    TagRequest.new_rule_ticket.ilike(f"%{keyword}%"),
                    TagRequest.requester_name.ilike(f"%{keyword}%")
                )
            )
        else:
            query = query.filter(
                or_(
                    TagRequest.new_tag_ticket.ilike(f"%{keyword}%"),
                    TagRequest.new_rule_ticket.ilike(f"%{keyword}%"),
                    TagRequest.requester_name.ilike(f"%{keyword}%")
                )
            )
    if status and status != 'all':
        if status == 'pending':
            query = query.filter(TagRequest.status.notin_([
                Constants.STATUS_REQUEST_PUBLISHED,
                Constants.STATUS_REQUEST_REJECTED
            ]))
        else:
            try:
                query = query.filter(TagRequest.status == int(status))
            except ValueError:
                pass
    if property_id:
        query = query.filter(TagRequest.property_id == property_id)
    if vendor_id:
        query = query.filter(TagRequest.vendor_id == vendor_id)
    if subsidiary_id:
        query = query.join(Property, TagRequest.property_id == Property.id).filter(Property.subsidiary_id == subsidiary_id)
    if req_type:
        if req_type == Constants.JIRA_TYPE_NEW_RULE:
            query = query.filter(
                or_(
                    TagRequest.type == Constants.JIRA_TYPE_NEW_RULE,
                    and_(
                        TagRequest.type == Constants.JIRA_TYPE_NEW_TAG,
                        TagRequest.status == Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED
                    )
                )
            )
        elif req_type == Constants.JIRA_TYPE_NEW_TAG:
            query = query.filter(
                TagRequest.type == Constants.JIRA_TYPE_NEW_TAG,
                TagRequest.status != Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED
            )
        else:
            query = query.filter(TagRequest.type == req_type)
    if created_at_from:
        query = query.filter(TagRequest.created_at >= f"{created_at_from} 00:00:00")
    if created_at_to:
        query = query.filter(TagRequest.created_at <= f"{created_at_to} 23:59:59")

    pagination = query.order_by(TagRequest.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Active filters calculation
    active_filters_count = 0
    advanced_filter_keys = ['subsidiary_id', 'property_id', 'vendor_id', 'status', 'type', 'created_at_from', 'created_at_to']
    for k in advanced_filter_keys:
        if request.args.get(k):
            active_filters_count += 1
    if keyword:
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

    # Preload task_map for related tasks
    task_map = {}
    ticket_ids = []
    for r in pagination.items:
        if r.new_tag_ticket:
            ticket_ids.append(r.new_tag_ticket)
        if r.new_rule_ticket:
            ticket_ids.append(r.new_rule_ticket)
    if ticket_ids:
        tasks = ActivityLog.query.filter(ActivityLog.ticket_id.in_(list(set(ticket_ids)))).all()
        for t in tasks:
            task_map[t.ticket_id] = {'id': t.id, 'title': t.title}

    filters = {
        'keyword': keyword,
        'status': status,
        'property_id': property_id,
        'vendor_id': vendor_id,
        'subsidiary_id': subsidiary_id,
        'type': req_type,
        'created_at_from': created_at_from,
        'created_at_to': created_at_to
    }

    return render_template(
        'tag_requests/list.html',
        requests=pagination.items,
        pagination=pagination,
        pager=pagination,
        totalRequests=pagination.total,
        properties=properties_map,
        propertyOptions=Property.options(),
        vendors=Vendor.options(),
        subsidiaries=subsidiaries_map,
        task_map=task_map,
        activeFiltersCount=active_filters_count,
        hasActiveFilters=has_active_filters,
        advancedFilterKeys=advanced_filter_keys,
        filters=filters,
        clearUrl=url_for('tag_requests.index')
    )

@tag_requests_bp.route('/view/<int:id>')
@login_required
@permission_required('tag-requests')
def view(id):
    req = TagRequest.query.get_or_404(id)
    files = TagRequestFile.query.filter_by(request_id=req.id).all()

    # Associated tags
    tag_ids = [int(x.strip()) for x in req.tags.split(',') if x.strip().isdigit()] if req.tags else []
    tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else []

    all_properties = Property.query.filter_by(deleted_at=None).order_by(Property.name.asc()).all()
    all_vendors = Vendor.options()

    # Available tags to add, grouped by property name
    available_tags = Tag.query.filter_by(deleted_at=None).order_by(Tag.name.asc()).all()
    grouped_tags = defaultdict(list)
    for t in available_tags:
        prop_name = t.property.name if t.property else 'Other'
        grouped_tags[prop_name].append(t)

    properties_map = {p.id: p.name for p in Property.query.all()}
    vendors_map = {v.id: v.name for v in Vendor.query.all()}

    return render_template(
        'tag_requests/view.html',
        request=req,
        tags=tags,
        files=files,
        groupedTags=grouped_tags,
        allProperties=all_properties,
        allVendors=all_vendors,
        properties=properties_map,
        vendors=vendors_map,
        hasNewTag=bool(req.new_tag_ticket),
        hasNewRule=bool(req.new_rule_ticket),
        captureUrl=url_for('tag_requests.capture'),
        organizations=Organization.options()
    )

@tag_requests_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('tag-requests')
def create():
    if request.method == 'POST':
        new_tag_ticket = request.form.get('new_tag_ticket')
        tags = request.form.get('tags', '')
        property_id = request.form.get('property_id', type=int)
        vendor_id = request.form.get('vendor_id', type=int)
        req_type = request.form.get('type', type=int) or Constants.JIRA_TYPE_NEW_TAG
        new_rule_ticket = request.form.get('new_rule_ticket')
        requester_name = request.form.get('requester_name')
        requester_email = request.form.get('requester_email')
        requester_org = request.form.get('requester_organization', type=int)

        req = TagRequest(
            new_tag_ticket=new_tag_ticket,
            tags=tags,
            property_id=property_id,
            vendor_id=vendor_id,
            type=req_type,
            new_rule_ticket=new_rule_ticket,
            requester_name=requester_name,
            requester_email=requester_email,
            requester_organization=requester_org,
            status=Constants.STATUS_REQUEST_HQ_REVIEW,
            created_by=session.get('user_id', 0),
            deleted_by=0
        )
        db.session.add(req)
        db.session.commit()
        flash('Tag Request created successfully.', 'success')
        return redirect(url_for('tag_requests.view', id=req.id))

    requester_names = [r[0] for r in db.session.query(Tag.requester_name).filter(Tag.requester_name.isnot(None), Tag.requester_name != '').distinct().all()]
    requester_emails = [r[0] for r in db.session.query(Tag.requester_email).filter(Tag.requester_email.isnot(None), Tag.requester_email != '').distinct().all()]

    return render_template(
        'tag_requests/create.html',
        tag_ids=[],
        request_id=None,
        request_type=Constants.JIRA_TYPE_NEW_TAG,
        propertiesList=Property.query.filter_by(deleted_at=None).order_by(Property.name).all(),
        organizations=Organization.options(),
        allTags=Tag.query.filter_by(deleted_at=None).all(),
        requesterNamesList=requester_names,
        requesterEmailsList=requester_emails,
        requests=TagRequest.query.filter_by(deleted_at=None).order_by(TagRequest.id.desc()).limit(10).all(),
        ticket_id=None,
        property=None,
        vendor=None,
        relatedTask=None,
        jiraTitle='',
        detailsHtml='',
        libraryName='',
        actionLink='',
        extracted_data=None,
        tag=None
    )

@tag_requests_bp.route('/upload-excel', methods=['GET', 'POST'])
@tag_requests_bp.route('/create-from-excel', methods=['GET', 'POST'])
@login_required
@permission_required('tag-requests')
def upload_excel():
    return render_template('tag_requests/upload_excel.html', extracted_data=None)

@tag_requests_bp.route('/parse-excel', methods=['POST'])
@login_required
@permission_required('tag-requests')
def parse_excel():
    import uuid, openpyxl, re
    file = request.files.get('excel_file')
    if not file or not file.filename or not file.filename.lower().endswith('.xlsx'):
        flash('Please upload a valid .xlsx file.', 'error')
        return redirect(url_for('tag_requests.upload_excel'))

    temp_folder = os.path.join(Config.UPLOAD_DIR, 'temp')
    os.makedirs(temp_folder, exist_ok=True)
    orig_name = secure_filename(file.filename)
    temp_filename = f"{uuid.uuid4().hex}_{orig_name}"
    temp_file_path = os.path.join(temp_folder, temp_filename)
    file.save(temp_file_path)

    try:
        wb = openpyxl.load_workbook(temp_file_path, read_only=True, data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        wb.close()
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        flash(f"Failed to parse Excel file: {str(e)}", 'error')
        return redirect(url_for('tag_requests.upload_excel'))

    properties = Property.query.filter(Property.deleted_at.is_(None)).all()

    extracted_data = {
        'property_id': '',
        'default_tag': '',
        'excel_file_path': temp_file_path,
        'excel_file_name': orig_name,
        'vendor_name': '',
        'validity': '',
        'target_properties': '',
        'target_pages': '',
        'events': '',
        'requester_name': '',
        'requester_email': '',
        'tag_script': '',
        'background': '',
        'objective': '',
        'q1': '',
        'q2': '',
        'q3': '',
        'q4': '',
        'q5': ''
    }

    for row in rows:
        if len(row) < 3:
            continue
        key = str(row[1] or '').strip()
        val = str(row[2] or '').strip()

        if 'Partner/Vendor' in key:
            extracted_data['vendor_name'] = val
        elif 'Validity of the Tags' in key:
            extracted_data['validity'] = val
        elif 'Target Property/Sites' in key:
            extracted_data['target_properties'] = val
        elif 'Target Page(s)' in key:
            extracted_data['target_pages'] = val
        elif 'Events need to be captured' in key:
            extracted_data['events'] = val
        elif 'Requestor Name' in key or 'Requester Name' in key:
            extracted_data['requester_name'] = val
        elif 'Requestor Email' in key or 'Requester Email' in key:
            extracted_data['requester_email'] = val
        elif key == 'Tag' or key.startswith('Tag '):
            extracted_data['tag_script'] = val
        elif 'Background' in key:
            extracted_data['background'] = val
        elif 'Objective' in key:
            extracted_data['objective'] = val
        elif 'What is the official website of the platform/company?' in key:
            extracted_data['q1'] = val
        elif 'What is the duration of usage?' in key:
            extracted_data['q2'] = val
        elif 'Any KPIs applied to review this tag bi-monthly' in key:
            extracted_data['q3'] = val
        elif 'Performance thresholds that will determine renewal or deactivation of this tag?' in key:
            extracted_data['q4'] = val
        elif 'What is your internal process for reviewing and validating these KPIs every two months?' in key:
            extracted_data['q5'] = val

    has_data = any(
        bool(extracted_data[k]) for k in extracted_data
        if k not in ['property_id', 'default_tag', 'excel_file_path', 'excel_file_name']
    )

    if not has_data:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        flash('The uploaded Excel file does not contain any valid tag request data.', 'error')
        return redirect(url_for('tag_requests.upload_excel'))

    if extracted_data['target_properties']:
        urls = re.split(r'[\s,;]+', extracted_data['target_properties'])
        urls = [u.strip() for u in urls if u.strip()]

        def normalize_url(u):
            u = re.sub(r'^https?://(www\.)?', '', u.strip().lower())
            return u.rstrip('/')

        best_match_id = None
        best_match_len = 0

        for u in urls:
            norm_u = normalize_url(u)
            for p in properties:
                if not p.website:
                    continue
                norm_p = normalize_url(p.website)
                if norm_u.startswith(norm_p):
                    if len(norm_p) > best_match_len:
                        best_match_id = p.id
                        best_match_len = len(norm_p)
            if best_match_id:
                extracted_data['property_id'] = best_match_id
                break

    shop_or_aem = 'AEM'
    if extracted_data['property_id']:
        matched_prop = Property.query.get(extracted_data['property_id'])
        if matched_prop and matched_prop.is_shop == Constants.YES:
            shop_or_aem = 'Shop'

    vname = extracted_data['vendor_name'] or 'Vendor'
    uid_str = str(uuid.uuid4())
    extracted_data['default_tag'] = f"LC-{shop_or_aem}-AD({vname})-CM-ALL-WL-SDSME_{uid_str}"

    return render_template('tag_requests/upload_excel.html', extracted_data=extracted_data)

@tag_requests_bp.route('/prefill', methods=['POST'])
@login_required
@permission_required('tag-requests')
def prefill():
    extracted_data = request.form.to_dict()
    requester_names = [r[0] for r in db.session.query(Tag.requester_name).filter(Tag.requester_name.isnot(None), Tag.requester_name != '').distinct().all()]
    requester_emails = [r[0] for r in db.session.query(Tag.requester_email).filter(Tag.requester_email.isnot(None), Tag.requester_email != '').distinct().all()]

    return render_template(
        'tag_requests/create.html',
        tag_ids=[],
        request_id=None,
        request_type=Constants.JIRA_TYPE_NEW_TAG,
        propertiesList=Property.query.filter_by(deleted_at=None).order_by(Property.name).all(),
        organizations=Organization.options(),
        allTags=Tag.query.filter_by(deleted_at=None).all(),
        requesterNamesList=requester_names,
        requesterEmailsList=requester_emails,
        requests=TagRequest.query.filter_by(deleted_at=None).order_by(TagRequest.id.desc()).limit(10).all(),
        ticket_id=None,
        property=None,
        vendor=None,
        relatedTask=None,
        jiraTitle='',
        detailsHtml='',
        libraryName='',
        actionLink='',
        extracted_data=extracted_data,
        tag=None
    )

@tag_requests_bp.route('/create/confirm', methods=['POST'])
@login_required
@permission_required('tag-requests')
def create_confirm():
    ticket_id = request.form.get('ticket_id', '').strip()
    raw_ids = request.form.getlist('request_ids[]') or request.form.get('request_ids', '').split(',')
    single_id = request.form.get('request_id')
    if single_id:
        raw_ids.append(single_id)
    
    req_ids = []
    for x in raw_ids:
        if str(x).strip().isdigit():
            req_ids.append(int(str(x).strip()))
    req_ids = sorted(list(set(req_ids)))

    if not ticket_id:
        flash("Ticket was not successfully created.", "error")
        return redirect(url_for('tag_requests.index'))

    if not req_ids:
        flash("No tag requests were specified.", "error")
        return redirect(url_for('tag_requests.index'))

    user_id = session.get('user_id', 0)
    for rid in req_ids:
        tag_req = TagRequest.query.get(rid)
        if not tag_req:
            continue
        if tag_req.type == Constants.JIRA_TYPE_NEW_RULE:
            tag_req.new_rule_ticket = ticket_id
            tag_req.status = Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED
            title_prefix = "New Rule Request"
            jira_type = Constants.JIRA_TYPE_NEW_RULE
        else:
            tag_req.new_tag_ticket = ticket_id
            title_prefix = "New Tag Request"
            jira_type = Constants.JIRA_TYPE_NEW_TAG
        tag_req.updated_by = user_id

        # Save JiraHistory
        if tag_req.tags:
            for tid in [int(t.strip()) for t in tag_req.tags.split(',') if t.strip().isdigit()]:
                jh = JiraHistory(
                    ticket_id=ticket_id,
                    type=str(jira_type),
                    comments=tag_req.tags,
                    tag_id=tid,
                    property_id=tag_req.property_id or 0,
                    subsidiary_id=tag_req.property.subsidiary_id if tag_req.property else None,
                    created_by=user_id
                )
                db.session.add(jh)

        # Auto-add ActivityLog Task
        prop = Property.query.get(tag_req.property_id) if tag_req.property_id else None
        vendor = Vendor.query.get(tag_req.vendor_id) if tag_req.vendor_id else None
        prop_name = prop.name if prop else 'N/A'
        vendor_name = vendor.name if vendor else 'N/A'
        
        desc = f"<ol><li><b>{prop_name}</b></li><ul>"
        if tag_req.tags:
            for tid in [int(t.strip()) for t in tag_req.tags.split(',') if t.strip().isdigit()]:
                t_obj = Tag.query.get(tid)
                if t_obj:
                    desc += f"<li>{t_obj.name}</li>"
        desc += "</ul></ol>"

        task = ActivityLog(
            title=f"{title_prefix} | {prop_name} [{vendor_name}]",
            description=desc,
            subsidiary_id=prop.subsidiary_id if prop else None,
            team_id=Constants.TEAM_MEDIA_TAGGING if hasattr(Constants, 'TEAM_MEDIA_TAGGING') else 1,
            project='New Request',
            ticket_id=ticket_id,
            assignee=user_id,
            status=Constants.ACTIVITY_LOGS_STATUS_IMPLEMENTATION,
            type=Constants.ACTIVITY_TYPE_REQUEST if hasattr(Constants, 'ACTIVITY_TYPE_REQUEST') else 1,
            size=Constants.ACTIVITY_SIZE_M,
            priority=Constants.PRIORITY_MEDIUM,
            created_by=user_id,
            requested_date=datetime.now(),
            start_date=datetime.now()
        )
        db.session.add(task)

    db.session.commit()
    flash(f"Tag Request {ticket_id} created and confirmed successfully.", "success")
    return redirect(url_for('tag_requests.index'))

@tag_requests_bp.route('/capture', methods=['GET', 'POST'])
@tag_requests_bp.route('/capture-tags', methods=['GET', 'POST'])
@login_required
@permission_required('tag-requests')
def capture():
    if request.method == 'POST':
        import subprocess
        target_url = request.form.get('target_url', '').strip()
        launch_script_url = request.form.get('launch_script_url', '').strip()
        if not target_url:
            return jsonify({'success': False, 'error': 'Target URL is required.'})

        node_script = os.path.join(Config.BASE_DIR, 'app', 'static', 'js', 'capture_tags.js')
        node_bin = r"C:\Program Files\nodejs\node.exe"
        if not os.path.exists(node_bin):
            node_bin = "node"

        try:
            cmd = [node_bin, node_script, target_url]
            if launch_script_url:
                cmd.append(launch_script_url)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=75)
            if result.returncode == 0 and result.stdout:
                parsed = json.loads(result.stdout)
                return jsonify(parsed)
            else:
                return jsonify({
                    'success': True,
                    'rules_fired': [],
                    'condition_not_met': [],
                    'failed': [],
                    'network_tags': [],
                    'debug_activity': [f"Node exit code: {result.returncode}"]
                })
        except Exception as e:
            return jsonify({
                'success': True,
                'rules_fired': [],
                'condition_not_met': [],
                'failed': [],
                'network_tags': [],
                'debug_activity': [f"Execution error: {str(e)}"]
            })

    # GET
    system_settings = {}
    if os.path.exists(Config.SYSTEM_SETTINGS_FILE):
        try:
            with open(Config.SYSTEM_SETTINGS_FILE, 'r') as sf:
                system_settings = json.load(sf)
        except Exception:
            pass

    flagship_page = system_settings.get('flagship_page', '')
    flagship_buy_page = system_settings.get('flagship_buy_page', '')
    title_c3 = system_settings.get('excel_title_c3') or 'URL 2'
    title_d3 = system_settings.get('excel_title_d3') or 'URL 3'
    home_url = request.args.get('url', '').strip()

    target_url1 = home_url
    target_url2 = ''
    target_url3 = ''
    if home_url:
        clean = home_url.rstrip('/')
        if flagship_page:
            target_url2 = clean + '/' + flagship_page.lstrip('/')
        if flagship_buy_page:
            target_url3 = clean + '/' + flagship_buy_page.lstrip('/')

    return render_template(
        'tag_requests/capture_tags.html',
        systemSettings=system_settings,
        flagshipPage=flagship_page,
        flagshipBuyPage=flagship_buy_page,
        titleC3=title_c3,
        titleD3=title_d3,
        targetUrl1=target_url1,
        targetUrl2=target_url2,
        targetUrl3=target_url3
    )

@tag_requests_bp.route('/generate-excel', methods=['POST'])
@login_required
def generate_capture_excel():
    import io, re, openpyxl
    property_id = request.form.get('property_id', type=int)
    request_id = request.form.get('request_id', type=int)
    rules_data_raw = request.form.get('rules_data', '{}')
    try:
        rules_data = json.loads(rules_data_raw)
    except Exception:
        rules_data = {}

    prop = None
    tag_names = []
    if request_id:
        req = TagRequest.query.get(request_id)
        if req:
            prop = Property.query.get(req.property_id)
            if req.tags:
                for tid in req.tags.split(','):
                    if tid.strip().isdigit():
                        t = Tag.query.get(int(tid.strip()))
                        if t:
                            tag_names.append(t.name)
    elif property_id:
        prop = Property.query.get(property_id)
        tag_ids = request.form.getlist('tag_ids[]') or request.form.getlist('tag_ids')
        for tid in tag_ids:
            if str(tid).isdigit():
                t = Tag.query.get(int(tid))
                if t:
                    tag_names.append(t.name)
        custom_tags = request.form.getlist('custom_tags[]') or request.form.getlist('custom_tags')
        for ct in custom_tags:
            if ct and ct.strip():
                tag_names.append(ct.strip())

    property_name = prop.name if prop else 'Unknown Property'
    template_path = os.path.join(Config.UPLOAD_DIR, 'AEM - Local Rule Monitoring File.xlsx')
    if not os.path.exists(template_path):
        flash('Template file not found on server.', 'error')
        return redirect(url_for('tag_requests.generate_rule_monitoring'))

    wb = openpyxl.load_workbook(template_path)
    sheet = wb.active

    sheet['B1'] = property_name

    if len(tag_names) > 1:
        sheet.insert_rows(3, amount=len(tag_names) - 1)

    r_idx = 2
    for tname in tag_names:
        sheet[f'B{r_idx}'] = tname
        r_idx += 1

    def extract_rule(rules_list):
        res = []
        for r in rules_list:
            m = re.search(r'"([^"]+)"', str(r))
            res.append(m.group(1) if m else str(r).strip())
        return [x for x in res if x]

    url1_rules = extract_rule(rules_data.get('url1', []))
    url2_rules = extract_rule(rules_data.get('url2', []))
    url3_rules = extract_rule(rules_data.get('url3', []))

    offset = len(tag_names) - 1 if len(tag_names) > 1 else 0

    system_settings = {}
    if os.path.exists(Config.SYSTEM_SETTINGS_FILE):
        try:
            with open(Config.SYSTEM_SETTINGS_FILE, 'r') as sf:
                system_settings = json.load(sf)
        except Exception:
            pass

    title_c3 = system_settings.get('excel_title_c3')
    title_d3 = system_settings.get('excel_title_d3')
    if title_c3:
        sheet[f'C{3 + offset}'] = title_c3
    if title_d3:
        sheet[f'D{3 + offset}'] = title_d3

    sheet[f'B{4 + offset}'] = len(url1_rules)
    sheet[f'C{4 + offset}'] = len(url2_rules)
    sheet[f'D{4 + offset}'] = len(url3_rules)

    sheet[f'B{6 + offset}'] = len(url1_rules)
    sheet[f'C{6 + offset}'] = len(url2_rules)
    sheet[f'D{6 + offset}'] = len(url3_rules)

    row_b = 7 + offset
    for rule in url1_rules:
        sheet[f'B{row_b}'] = rule
        row_b += 1

    row_c = 7 + offset
    for rule in url2_rules:
        sheet[f'C{row_c}'] = rule
        row_c += 1

    row_d = 7 + offset
    for rule in url3_rules:
        sheet[f'D{row_d}'] = rule
        row_d += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = re.sub(r'[^a-zA-Z0-9_\-\.\s\(\)]', '', f"{property_name} - Local Rule Monitoring File.xlsx")
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@tag_requests_bp.route('/generate-rule-monitoring', methods=['GET'])
@login_required
@permission_required('tag-requests')
def generate_rule_monitoring():
    properties = Property.query.filter_by(deleted_at=None).order_by(Property.name.asc()).all()
    system_settings = {}
    if os.path.exists(Config.SYSTEM_SETTINGS_FILE):
        try:
            with open(Config.SYSTEM_SETTINGS_FILE, 'r') as f:
                system_settings = json.load(f)
        except Exception:
            pass
    return render_template(
        'tag_requests/generate_rule_monitoring.html',
        properties=properties,
        systemSettings=system_settings
    )

@tag_requests_bp.route('/property-tags/<int:property_id>', methods=['GET'])
@login_required
def get_property_tags(property_id):
    tags = Tag.query.filter_by(property_id=property_id, is_active=1, deleted_at=None).order_by(Tag.name.asc()).all()
    return jsonify({
        'success': True,
        'tags': [{'id': t.id, 'name': t.name} for t in tags]
    })

@tag_requests_bp.route('/shop-manual-input', methods=['GET'])
@tag_requests_bp.route('/shop-manual-input/<int:id>', methods=['GET'])
@login_required
@permission_required('tag-requests')
def shop_manual_input(id=None):
    req = TagRequest.query.get(id) if id else TagRequest.query.first()
    prop = req.property if req else None
    tag_names = []
    if req and req.tags:
        for tid in req.tags.split(','):
            if tid.strip().isdigit():
                t = Tag.query.get(int(tid.strip()))
                if t:
                    tag_names.append(t.name)
    return render_template('tag_requests/shop_manual_input.html', request=req, property=prop, tagNames=tag_names)

@tag_requests_bp.route('/generate-shop-excel', methods=['POST'])
@login_required
def generate_shop_excel():
    import io, re, openpyxl
    property_id = request.form.get('property_id', type=int)
    request_id = request.form.get('request_id', type=int)
    cart_logs = request.form.get('cart_logs', '')
    checkout_logs = request.form.get('checkout_logs', '')
    order_logs = request.form.get('order_logs', '')

    prop = None
    tag_names = []
    if request_id:
        req = TagRequest.query.get(request_id)
        if req:
            prop = Property.query.get(req.property_id)
            if req.tags:
                for tid in req.tags.split(','):
                    if tid.strip().isdigit():
                        t = Tag.query.get(int(tid.strip()))
                        if t:
                            tag_names.append(t.name)
    elif property_id:
        prop = Property.query.get(property_id)
        tag_ids = request.form.getlist('tag_ids[]') or request.form.getlist('tag_ids')
        for tid in tag_ids:
            if str(tid).isdigit():
                t = Tag.query.get(int(tid))
                if t:
                    tag_names.append(t.name)
        custom_tags = request.form.getlist('custom_tags[]') or request.form.getlist('custom_tags')
        for ct in custom_tags:
            if ct and ct.strip():
                tag_names.append(ct.strip())

    property_name = prop.name if prop else 'Unknown Property'
    is_shop = (prop.is_shop == 1) if prop else False

    tpl_name = 'Shop - Local Rule Monitoring File.xlsx' if is_shop else 'AEM - Local Rule Monitoring File.xlsx'
    template_path = os.path.join(Config.UPLOAD_DIR, tpl_name)
    if not os.path.exists(template_path):
        flash('Template file not found on server.', 'error')
        return redirect(url_for('tag_requests.generate_rule_monitoring'))

    wb = openpyxl.load_workbook(template_path)
    sheet = wb.active

    sheet['B1'] = property_name

    if len(tag_names) > 1:
        sheet.insert_rows(3, amount=len(tag_names) - 1)

    r_idx = 2
    for tname in tag_names:
        sheet[f'B{r_idx}'] = tname
        r_idx += 1

    def extract_rules_from_logs(logs):
        res = []
        for line in logs.replace('\r', '').split('\n'):
            line = line.strip()
            if not line:
                continue
            m = re.search(r'"([^"]+)"', line)
            res.append(m.group(1) if m else line)
        return res

    box1_rules = extract_rules_from_logs(cart_logs)
    box2_rules = extract_rules_from_logs(checkout_logs)
    box3_rules = extract_rules_from_logs(order_logs)

    offset = len(tag_names) - 1 if len(tag_names) > 1 else 0

    if not is_shop:
        system_settings = {}
        if os.path.exists(Config.SYSTEM_SETTINGS_FILE):
            try:
                with open(Config.SYSTEM_SETTINGS_FILE, 'r') as sf:
                    system_settings = json.load(sf)
            except Exception:
                pass
        title_c3 = system_settings.get('excel_title_c3')
        title_d3 = system_settings.get('excel_title_d3')
        if title_c3:
            sheet[f'C{3 + offset}'] = title_c3
        if title_d3:
            sheet[f'D{3 + offset}'] = title_d3

    sheet[f'B{4 + offset}'] = len(box1_rules)
    sheet[f'C{4 + offset}'] = len(box2_rules)
    sheet[f'D{4 + offset}'] = len(box3_rules)

    sheet[f'B{6 + offset}'] = len(box1_rules)
    sheet[f'C{6 + offset}'] = len(box2_rules)
    sheet[f'D{6 + offset}'] = len(box3_rules)

    row_b = 7 + offset
    for rule in box1_rules:
        sheet[f'B{row_b}'] = rule
        row_b += 1

    row_c = 7 + offset
    for rule in box2_rules:
        sheet[f'C{row_c}'] = rule
        row_c += 1

    row_d = 7 + offset
    for rule in box3_rules:
        sheet[f'D{row_d}'] = rule
        row_d += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = re.sub(r'[^a-zA-Z0-9_\-\.\s\(\)]', '', f"{property_name} - Local Rule Monitoring File.xlsx")
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@tag_requests_bp.route('/request-approved/<int:id>', methods=['GET'])
@login_required
@permission_required('tag-requests')
def request_approved(id):
    req = TagRequest.query.get_or_404(id)
    user_id = session.get('user_id', 0)

    # 1. Update request status to published
    req.status = Constants.STATUS_REQUEST_PUBLISHED
    req.updated_by = user_id

    # 2. Enable all associated tags
    tag_ids = [int(x.strip()) for x in (req.tags or '').split(',') if x.strip().isdigit()]
    if tag_ids:
        Tag.query.filter(Tag.id.in_(tag_ids)).update({
            Tag.status: Constants.STATUS_ENABLED,
            Tag.updated_by: user_id
        }, synchronize_session=False)

    # 3. Transition linked ActivityLog tasks to COMPLETED
    ticket_ids = [t for t in [req.new_tag_ticket, req.new_rule_ticket] if t and t.strip()]
    if ticket_ids:
        linked_tasks = ActivityLog.query.filter(
            ActivityLog.ticket_id.in_(ticket_ids),
            ActivityLog.deleted_at.is_(None)
        ).all()
        for task in linked_tasks:
            if task.status != Constants.ACTIVITY_LOGS_STATUS_COMPLETED:
                from_label = Constants.ACTIVITY_LOGS_STATUS.get(task.status, 'Unknown')
                to_label = Constants.ACTIVITY_LOGS_STATUS.get(Constants.ACTIVITY_LOGS_STATUS_COMPLETED, 'Completed')
                comment = ActivityLogComment(
                    log_id=task.id,
                    comment=f"Status updated from [{from_label}] to [{to_label}]",
                    commented_by=user_id,
                    type=2
                )
                db.session.add(comment)
                task.status = Constants.ACTIVITY_LOGS_STATUS_COMPLETED
                task.updated_by = user_id

    db.session.commit()
    tickets_str = ", ".join(ticket_ids) if ticket_ids else f"ID {id}"
    flash(f"[{tickets_str}] Tag Request approved, and associated tags are now enabled.", 'success')
    return redirect(url_for('tag_requests.index'))

@tag_requests_bp.route('/add-new-tag', methods=['POST'])
@login_required
def add_new_tag():
    req_id = request.form.get('request_id', type=int)
    ticket_id = request.form.get('new_tag_ticket')
    if req_id and ticket_id:
        req = TagRequest.query.get(req_id)
        if req:
            req.new_tag_ticket = ticket_id
            db.session.commit()
            flash(f"Ticket {ticket_id} attached.", 'success')
            return redirect(url_for('tag_requests.view', id=req_id))
    return redirect(url_for('tag_requests.index'))

@tag_requests_bp.route('/add-new-rule', methods=['POST'])
@login_required
def add_new_rule():
    req_id = request.form.get('request_id', type=int)
    ticket_id = request.form.get('new_rule_ticket')
    if req_id and ticket_id:
        req = TagRequest.query.get(req_id)
        if req:
            req.new_rule_ticket = ticket_id
            req.status = Constants.STATUS_REQUEST_NEW_RULE_REQUEST_SUBMITTED
            db.session.commit()
            flash(f"Rule ticket {ticket_id} attached.", 'success')
            return redirect(url_for('tag_requests.view', id=req_id))
    return redirect(url_for('tag_requests.index'))

@tag_requests_bp.route('/new-rule-request/<int:id>')
@login_required
def new_rule_request(id):
    req = TagRequest.query.get_or_404(id)
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/new-tag-request/<int:id>')
@login_required
def new_tag_request(id):
    req = TagRequest.query.get_or_404(id)
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/update-property/<int:id>', methods=['POST'])
@login_required
def update_property(id):
    req = TagRequest.query.get_or_404(id)
    pid = request.form.get('property_id', type=int)
    if pid:
        req.property_id = pid
        db.session.commit()
        flash('Property updated successfully.', 'success')
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/update-status/<int:id>', methods=['POST'])
@login_required
def update_status(id):
    req = TagRequest.query.get_or_404(id)
    st = request.form.get('status', type=int)
    if st is not None:
        req.status = st
        db.session.commit()
        flash('Status updated successfully.', 'success')
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/update-type/<int:id>', methods=['POST'])
@login_required
def update_type(id):
    req = TagRequest.query.get_or_404(id)
    tp = request.form.get('type', type=int)
    if tp is not None:
        req.type = tp
        db.session.commit()
        flash('Type updated successfully.', 'success')
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/add-tag/<int:id>', methods=['POST'])
@login_required
def add_tag(id):
    req = TagRequest.query.get_or_404(id)
    tag_id = request.form.get('tag_id')
    if tag_id:
        existing = [x.strip() for x in (req.tags or '').split(',') if x.strip()]
        if str(tag_id) not in existing:
            existing.append(str(tag_id))
            req.tags = ','.join(existing)
            db.session.commit()
            flash('Tag added to request.', 'success')
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/remove-tag/<int:id>/<int:tag_id>', methods=['POST'])
@login_required
def remove_tag(id, tag_id):
    req = TagRequest.query.get_or_404(id)
    existing = [x.strip() for x in (req.tags or '').split(',') if x.strip()]
    if str(tag_id) in existing:
        existing.remove(str(tag_id))
        req.tags = ','.join(existing)
        db.session.commit()
        flash('Tag removed from request.', 'success')
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/create-tag/<int:id>', methods=['POST'])
@login_required
def create_tag_for_request(id):
    req = TagRequest.query.get_or_404(id)
    tag_name = request.form.get('name')
    if tag_name:
        tag = Tag(
            name=tag_name,
            property_id=req.property_id,
            vendor_id=req.vendor_id,
            status=Constants.STATUS_NEW_TAG_SUBMITTED,
            created_by=session.get('user_id', 0)
        )
        db.session.add(tag)
        db.session.flush()
        existing = [x.strip() for x in (req.tags or '').split(',') if x.strip()]
        existing.append(str(tag.id))
        req.tags = ','.join(existing)
        db.session.commit()
        flash(f"Tag '{tag_name}' created and added to request.", 'success')
    return redirect(url_for('tag_requests.view', id=req.id))

@tag_requests_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    req_id = request.form.get('request_id', type=int)
    file = request.files.get('file_path')
    if req_id and file and file.filename:
        fname = secure_filename(file.filename)
        save_dir = Config.NEW_TAG_UPLOAD_DIR
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, fname)
        file.save(save_path)
        req_file = TagRequestFile(
            file_name=fname,
            file_path=os.path.relpath(save_path, Config.UPLOAD_DIR),
            type=request.form.get('type', Constants.ATTACHMENT_REQUEST_FORM),
            request_id=req_id,
            created_by=session.get('user_id', 0)
        )
        db.session.add(req_file)
        db.session.commit()
        flash('File uploaded successfully.', 'success')
        return redirect(url_for('tag_requests.view', id=req_id))
    flash('File upload failed.', 'error')
    return redirect(url_for('tag_requests.index'))

@tag_requests_bp.route('/export')
@login_required
@permission_required('tag-requests')
def export():
    requests_list = TagRequest.query.filter(TagRequest.deleted_at.is_(None)).order_by(TagRequest.id.desc()).all()
    stream = ExcelService.export_tag_requests(requests_list)
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Tag_Requests_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
