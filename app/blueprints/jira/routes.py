from io import BytesIO
from datetime import datetime
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
import openpyxl
from app.models import db, JiraHistory, Property, Tag, Subsidiary, ActivityLog
from app.constants import Constants
from app.utils.decorators import login_required, permission_required
from app.services.excel_service import ExcelService

jira_bp = Blueprint('jira', __name__)

@jira_bp.route('/')
@login_required
@permission_required('jira')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    keyword = request.args.get('keyword', '').strip()
    subsidiary_id = request.args.get('subsidiary_id', type=int)
    property_id = request.args.get('property_id', type=int)
    ticket_type = request.args.get('ticket_type', '').strip()
    created_at_from = request.args.get('created_at_from', '').strip()
    created_at_to = request.args.get('created_at_to', '').strip()
    sort_by = request.args.get('sort_by', 'id')
    sort_dir = request.args.get('sort_dir', 'desc')

    subq = db.session.query(db.func.max(JiraHistory.id)).filter(
        JiraHistory.is_active == 1
    ).group_by(JiraHistory.ticket_id, JiraHistory.property_id)

    query = JiraHistory.query.filter(JiraHistory.id.in_(subq), JiraHistory.is_active == 1)
    if keyword:
        query = query.filter(
            (JiraHistory.ticket_id.ilike(f"%{keyword}%")) |
            (JiraHistory.comments.ilike(f"%{keyword}%"))
        )
    if subsidiary_id:
        query = query.filter_by(subsidiary_id=subsidiary_id)
    if property_id:
        query = query.filter_by(property_id=property_id)
    if ticket_type:
        query = query.filter(JiraHistory.type == str(ticket_type))
    if created_at_from:
        query = query.filter(JiraHistory.created_at >= f"{created_at_from} 00:00:00")
    if created_at_to:
        query = query.filter(JiraHistory.created_at <= f"{created_at_to} 23:59:59")

    sort_col = getattr(JiraHistory, sort_by, JiraHistory.id)
    if sort_dir.lower() == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Active filters calculation
    active_filters_count = 0
    for k in ['subsidiary_id', 'property_id', 'ticket_type', 'created_at_from', 'created_at_to']:
        if request.args.get(k):
            active_filters_count += 1
    has_active_filters = (active_filters_count > 0) or bool(keyword)

    all_subs = Subsidiary.query.filter_by(deleted_at=None).all()
    subs_map = {s.id: s.name for s in all_subs}

    all_props = Property.query.filter_by(deleted_at=None).all()
    props_map = {p.id: p.name for p in all_props}

    # Pre-fetch tasks by ticket_id
    ticket_ids = [t.ticket_id for t in pagination.items if t.ticket_id]
    tasks_map = {}
    if ticket_ids:
        tasks = ActivityLog.query.filter(ActivityLog.ticket_id.in_(ticket_ids)).all()
        for t in tasks:
            tasks_map[t.ticket_id] = t.id

    # Count total tags and unique tags across ALL matching tickets (not just current page)
    all_comments_data = query.with_entities(JiraHistory.comments, JiraHistory.tag_id).all()
    all_unique_tag_ids = set()
    total_tags_count = 0
    for comm, t_id in all_comments_data:
        ticket_tags = set()
        if t_id:
            ticket_tags.add(t_id)
        if comm:
            for cid in comm.split(','):
                cid = cid.strip()
                if cid.isdigit() and int(cid) > 0:
                    ticket_tags.add(int(cid))
        total_tags_count += len(ticket_tags)
        all_unique_tag_ids.update(ticket_tags)
    unique_tags_count = len(all_unique_tag_ids)

    # Enrich jiraTickets on current page
    all_page_tag_ids = set()
    for t in pagination.items:
        if t.tag_id:
            all_page_tag_ids.add(t.tag_id)
        if t.comments:
            for cid in t.comments.split(','):
                cid = cid.strip()
                if cid.isdigit():
                    all_page_tag_ids.add(int(cid))

    tags_cache = {tag.id: tag for tag in Tag.query.filter(Tag.id.in_(list(all_page_tag_ids))).all()} if all_page_tag_ids else {}

    enriched_tickets = []
    for t in pagination.items:
        t_tag_ids = []
        if t.tag_id:
            t_tag_ids.append(t.tag_id)
        if t.comments:
            for cid in t.comments.split(','):
                cid = cid.strip()
                if cid.isdigit():
                    t_tag_ids.append(int(cid))

        tag_objs = {}
        tag_status = None
        for tid in t_tag_ids:
            if tid in tags_cache:
                tag_obj = tags_cache[tid]
                tag_objs[tag_obj.id] = {'id': tag_obj.id, 'name': tag_obj.name, 'status': tag_obj.status}
                if tag_status is None:
                    tag_status = tag_obj.status
            else:
                tag_objs[tid] = {'id': tid, 'name': f"Tag #{tid}", 'status': None}

        # Dynamic properties for Jinja
        t.subsidiary_name = subs_map.get(t.subsidiary_id, 'Global')
        t.property_name = props_map.get(t.property_id, 'Unknown')
        t.ticket_tags_list = tag_objs
        t.related_task_id = tasks_map.get(t.ticket_id)
        t.related_tag_status = tag_status
        enriched_tickets.append(t)

    filters = {
        'keyword': keyword,
        'subsidiary_id': subsidiary_id,
        'property_id': property_id,
        'ticket_type': ticket_type,
        'created_at_from': created_at_from,
        'created_at_to': created_at_to,
        'sort_by': sort_by,
        'sort_dir': sort_dir
    }

    return render_template(
        'jira/list.html',
        jiraTickets=enriched_tickets,
        pagination=pagination,
        pager=pagination,
        totalTickets=pagination.total,
        tagCount=total_tags_count,
        uniqueTagsCount=unique_tags_count,
        subsidiaries=subs_map,
        propertyOptions=Property.options(),
        activeFiltersCount=active_filters_count,
        hasActiveFilters=has_active_filters,
        filters=filters,
        currentSortBy=sort_by,
        currentSortDir=sort_dir,
        clearUrl=url_for('jira.index'),
        collapseId='collapseFilter'
    )

@jira_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('jira')
def create():
    if request.method == 'POST':
        return add_entry()
    return render_template(
        'jira/create.html',
        tag=None,
        properties=Property.query.filter_by(deleted_at=None).order_by(Property.name).all(),
        subsidiaries=Subsidiary.options()
    )

@jira_bp.route('/add-entry', methods=['GET', 'POST'])
@login_required
@permission_required('jira')
def add_entry():
    tag_id = request.args.get('tag_id', type=int) or request.form.get('tag_id', type=int)
    tag = Tag.query.get(tag_id) if tag_id else None

    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id')
        entry_type = request.form.get('type')
        comments = request.form.get('comments')
        property_id = request.form.get('property_id', type=int) or (tag.property_id if tag else 0)
        subsidiary_id = request.form.get('subsidiary_id', type=int) or (tag.property.subsidiary_id if tag and tag.property else None)

        entry = JiraHistory(
            ticket_id=ticket_id,
            type=entry_type,
            comments=comments,
            tag_id=tag_id,
            property_id=property_id,
            subsidiary_id=subsidiary_id,
            created_by=session.get('user_id', 0)
        )
        db.session.add(entry)
        db.session.commit()
        flash('Jira entry logged successfully.', 'success')
        return redirect(url_for('jira.index'))

    return render_template(
        'jira/add_entry.html',
        tag=tag,
        properties=Property.query.filter_by(deleted_at=None).order_by(Property.name).all(),
        subsidiaries=Subsidiary.options()
    )

@jira_bp.route('/update-tags/<int:id>', methods=['GET', 'POST'])
@jira_bp.route('/update-tags-confirm/<int:id>', methods=['POST'])
@login_required
@permission_required('jira')
def update_tags(id):
    entry = JiraHistory.query.get_or_404(id)
    if request.method == 'POST':
        selected_tags = request.form.getlist('tag_ids[]') or request.form.getlist('tags') or request.form.getlist('tag_ids')
        tag_ids = [int(t) for t in selected_tags if str(t).strip().isdigit()]
        comments = ",".join([str(t) for t in tag_ids])
        first_tag_id = tag_ids[0] if tag_ids else None

        ticket_id = (request.form.get('ticket_id') or entry.ticket_id or '').strip()
        subsidiary_id = request.form.get('subsidiary_id', type=int) or entry.subsidiary_id
        entry_type = request.form.get('type') or entry.type

        old_ticket_id = entry.ticket_id
        if old_ticket_id:
            all_entries = JiraHistory.query.filter_by(ticket_id=old_ticket_id).all()
        else:
            all_entries = [entry]

        for ent in all_entries:
            ent.comments = comments
            ent.tag_id = first_tag_id
            if ticket_id:
                ent.ticket_id = ticket_id
            if subsidiary_id:
                ent.subsidiary_id = subsidiary_id
            if entry_type:
                ent.type = str(entry_type)
            ent.updated_by = session.get('user_id', 0)

        db.session.commit()
        flash(f'Ticket information and related tags updated successfully for {ticket_id or old_ticket_id}.', 'success')
        return redirect(url_for('jira.index'))

    all_tags = Tag.query.filter_by(deleted_at=None).order_by(Tag.name).all()
    original_comment = (entry.comments or '').strip()
    is_custom_comment = False
    linked_tag_ids = []
    if original_comment:
        raw_ids = [x.strip() for x in original_comment.split(',')]
        for rid in raw_ids:
            if rid.isdigit():
                linked_tag_ids.append(int(rid))
            else:
                is_custom_comment = True

    current_tags = []
    if linked_tag_ids:
        found_tags = Tag.query.filter(Tag.id.in_(linked_tag_ids)).all()
        tags_by_id = {t.id: t for t in found_tags}
        for tid in linked_tag_ids:
            if tid in tags_by_id:
                t = tags_by_id[tid]
                t.property_name = t.property.name if t.property else 'Unknown'
                current_tags.append(t)

    grouped_tags = defaultdict(list)
    for t in all_tags:
        prop_name = t.property.name if t.property else 'Unassigned'
        t.property_name = prop_name
        t.subsidiary_id = t.property.subsidiary_id if t.property else 0
        grouped_tags[prop_name].append(t)

    subsidiaries_map = Subsidiary.options()

    return render_template(
        'jira/update_tags.html',
        ticket=entry,
        entry=entry,
        currentTags=current_tags,
        groupedTags=grouped_tags,
        subsidiaries=subsidiaries_map,
        isCustomComment=is_custom_comment,
        originalComment=original_comment
    )

@jira_bp.route('/export')
@jira_bp.route('/download')
@login_required
@permission_required('jira')
def export():
    keyword = request.args.get('keyword', '').strip()
    subsidiary_id = request.args.get('subsidiary_id', type=int)
    property_id = request.args.get('property_id', type=int)
    ticket_type = request.args.get('ticket_type', '').strip()
    created_at_from = request.args.get('created_at_from', '').strip()
    created_at_to = request.args.get('created_at_to', '').strip()

    subq = db.session.query(db.func.max(JiraHistory.id)).filter(
        JiraHistory.is_active == 1
    ).group_by(JiraHistory.ticket_id, JiraHistory.property_id)

    query = JiraHistory.query.filter(JiraHistory.id.in_(subq), JiraHistory.is_active == 1)
    if keyword:
        query = query.filter(
            (JiraHistory.ticket_id.ilike(f"%{keyword}%")) |
            (JiraHistory.comments.ilike(f"%{keyword}%"))
        )
    if subsidiary_id:
        query = query.filter_by(subsidiary_id=subsidiary_id)
    if property_id:
        query = query.filter_by(property_id=property_id)
    if ticket_type:
        query = query.filter(JiraHistory.type == str(ticket_type))
    if created_at_from:
        query = query.filter(JiraHistory.created_at >= f"{created_at_from} 00:00:00")
    if created_at_to:
        query = query.filter(JiraHistory.created_at <= f"{created_at_to} 23:59:59")

    entries = query.order_by(JiraHistory.id.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Jira History"

    # Headers matching PHP JiraController::exportAsExcel: Subsidiary, Property, Ticket ID, Type, Comments
    headers = ['Subsidiary', 'Property', 'Ticket ID', 'Type', 'Comments']
    ws.append(headers)

    subs_cache = {s.id: s.name for s in Subsidiary.query.all()}
    props_cache = {p.id: p.name for p in Property.query.all()}
    tags_cache = {t.id: t.name for t in Tag.query.all()}

    for e in entries:
        sub_name = subs_cache.get(e.subsidiary_id, 'N/A')
        prop_name = props_cache.get(e.property_id, 'N/A')
        comments_val = e.comments or ''

        # Map comma-separated tag IDs to tag names if DATE_EXTENSION_RULE matching PHP
        try:
            if str(e.type) == str(Constants.JIRA_TYPE_DATE_EXTENSION_RULE) and comments_val:
                tag_ids = [x.strip() for x in comments_val.split(',') if x.strip().isdigit()]
                if tag_ids:
                    names = [tags_cache.get(int(tid), f"Tag #{tid}") for tid in tag_ids]
                    comments_val = ", ".join(names)
        except Exception:
            pass

        type_label = Constants.JIRA_TICKET_TYPES.get(int(e.type), str(e.type)) if e.type and str(e.type).isdigit() else (e.type or '')
        ws.append([sub_name, prop_name, e.ticket_id or '—', type_label, comments_val])

    ExcelService.apply_header_style(ws, 1)
    ExcelService.auto_fit_columns(ws)

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"JIRA_Tickets_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

