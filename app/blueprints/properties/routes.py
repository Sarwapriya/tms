from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import func, or_
from app.models import db, Property, Subsidiary, Country, Language
from app.utils.decorators import login_required, permission_required

properties_bp = Blueprint('properties', __name__)

@properties_bp.route('/')
@login_required
@permission_required('properties')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    keyword = request.args.get('keyword', '').strip()
    subsidiary_id = request.args.get('subsidiary_id', type=int)
    is_epp = request.args.get('is_epp')
    is_shop = request.args.get('is_shop')
    sort_by = request.args.get('sort_by') or 'subsidiary_id'
    sort_dir = request.args.get('sort_dir', 'asc').lower()
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'asc'

    query = Property.query.filter_by(deleted_at=None)

    if keyword:
        if keyword.isdigit():
            query = query.filter(
                (Property.id == int(keyword)) |
                (Property.name.ilike(f"%{keyword}%")) |
                (Property.website.ilike(f"%{keyword}%"))
            )
        else:
            query = query.filter(
                (Property.name.ilike(f"%{keyword}%")) |
                (Property.website.ilike(f"%{keyword}%"))
            )

    if subsidiary_id:
        query = query.filter(Property.subsidiary_id == subsidiary_id)
    if is_epp is not None and is_epp != '':
        query = query.filter(Property.is_epp == int(is_epp))
    if is_shop is not None and is_shop != '':
        query = query.filter(Property.is_shop == int(is_shop))

    allowed_columns = {
        'id': Property.id,
        'subsidiary_id': Property.subsidiary_id,
        'name': Property.name,
        'is_epp': Property.is_epp,
        'is_shop': Property.is_shop
    }
    col = allowed_columns.get(sort_by, Property.subsidiary_id)
    if sort_dir == 'desc':
        query = query.order_by(col.desc(), Property.name.asc())
    else:
        query = query.order_by(col.asc(), Property.name.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    advanced_filter_keys = ['subsidiary_id', 'is_epp', 'is_shop']
    active_filters_count = sum(1 for k in advanced_filter_keys if request.args.get(k) is not None and request.args.get(k) != '')
    if keyword:
        active_filters_count += 1
    has_active_filters = (active_filters_count > 0) or bool(keyword)

    filters = {
        'keyword': keyword,
        'subsidiary_id': subsidiary_id,
        'is_epp': is_epp,
        'is_shop': is_shop,
        'sort_by': sort_by,
        'sort_dir': sort_dir
    }

    # Fetch attribute lists for the Add Attribute modals
    subsidiaries_list = Subsidiary.query.filter_by(deleted_at=None).order_by(Subsidiary.name.asc()).all()
    languages_list = Language.query.filter_by(deleted_at=None).order_by(Language.name.asc()).all()
    countries_list = Country.query.filter_by(deleted_at=None).order_by(Country.name.asc()).all()

    return render_template(
        'properties/list.html',
        properties=pagination.items,
        pagination=pagination,
        pager=pagination,
        totalProperties=pagination.total,
        subsidiaryOptions=Subsidiary.options(),
        subsidiariesList=subsidiaries_list,
        languagesList=languages_list,
        countriesList=countries_list,
        activeFiltersCount=active_filters_count,
        hasActiveFilters=has_active_filters,
        advancedFilterKeys=advanced_filter_keys,
        filters=filters
    )

@properties_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('properties')
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        website = request.form.get('website')
        ref_link = request.form.get('ref_link')
        subsidiary_id = request.form.get('subsidiary_id', type=int)
        country_id = request.form.get('country_id', type=int)
        language_id = request.form.get('language_id', type=int)
        is_shop = 1 if request.form.get('is_shop') else 0
        is_epp = 1 if request.form.get('is_epp') else 0

        prop = Property(
            name=name,
            website=website,
            ref_link=ref_link,
            subsidiary_id=subsidiary_id,
            country_id=country_id,
            language_id=language_id,
            is_shop=is_shop,
            is_epp=is_epp,
            created_by=session.get('user_id', 0)
        )
        db.session.add(prop)
        db.session.commit()
        flash(f'Property {name} created successfully.', 'success')
        return redirect(url_for('properties.index'))

    return render_template(
        'properties/create.html',
        subsidiaries=Subsidiary.options(),
        countries=Country.options(),
        languages=Language.options(),
        property={}
    )

@properties_bp.route('/update-url/<int:id>', methods=['POST'])
@login_required
@permission_required('properties')
def update_url(id):
    prop = Property.query.get_or_404(id)
    new_url = request.form.get('website', '').strip()
    if new_url:
        prop.website = new_url
        prop.updated_by = session.get('user_id', 0)
        db.session.commit()
        flash(f"Property URL updated successfully.", 'success')
    return redirect(url_for('properties.index'))

@properties_bp.route('/add-attribute', methods=['POST'])
@login_required
@permission_required('properties')
def add_attribute():
    attr_type = (request.form.get('type') or '').strip().lower()
    name = (request.form.get('name') or '').strip()
    code = (request.form.get('code') or '').strip().upper()
    is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json)

    if not attr_type:
        msg = 'Attribute type is required.'
        if is_ajax:
            return jsonify({'status': 'error', 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('properties.index'))

    if not name:
        msg = 'Name is required.'
        if is_ajax:
            return jsonify({'status': 'error', 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('properties.index'))

    try:
        if attr_type == 'subsidiary':
            clean_name = name.upper()
            existing = Subsidiary.query.filter(func.upper(Subsidiary.name) == clean_name).first()
            if existing:
                if existing.deleted_at:
                    existing.is_active = 1
                    existing.deleted_at = None
                    existing.deleted_by = 0
                    existing.updated_by = session.get('user_id', 0)
                    db.session.commit()
                    msg = f"Subsidiary '{clean_name}' has been restored."
                    if is_ajax:
                        return jsonify({'status': 'success', 'message': msg, 'data': {'id': existing.id, 'name': existing.name}})
                    flash(msg, 'success')
                    return redirect(url_for('properties.index'))

                msg = f"Subsidiary '{clean_name}' already exists."
                if is_ajax:
                    return jsonify({'status': 'error', 'message': msg}), 422
                flash(msg, 'error')
                return redirect(url_for('properties.index'))

            sub = Subsidiary(name=clean_name, is_active=1, created_by=session.get('user_id', 0), deleted_by=0)
            db.session.add(sub)
            db.session.commit()
            msg = f"Subsidiary '{clean_name}' added successfully."
            if is_ajax:
                return jsonify({'status': 'success', 'message': msg, 'id': sub.id})
            flash(msg, 'success')
            return redirect(url_for('properties.index'))

        elif attr_type == 'language':
            clean_name = name.upper()
            existing = Language.query.filter(func.upper(Language.name) == clean_name).first()
            if existing:
                if existing.deleted_at:
                    existing.deleted_at = None
                    existing.deleted_by = 0
                    existing.updated_by = session.get('user_id', 0)
                    db.session.commit()
                    msg = f"Language '{clean_name}' has been restored."
                    if is_ajax:
                        return jsonify({'status': 'success', 'message': msg, 'data': {'id': existing.id, 'name': existing.name}})
                    flash(msg, 'success')
                    return redirect(url_for('properties.index'))

                msg = f"Language '{clean_name}' already exists."
                if is_ajax:
                    return jsonify({'status': 'error', 'message': msg}), 422
                flash(msg, 'error')
                return redirect(url_for('properties.index'))

            lang = Language(name=clean_name, created_by=session.get('user_id', 0), deleted_by=0)
            db.session.add(lang)
            db.session.commit()
            msg = f"Language '{clean_name}' added successfully."
            if is_ajax:
                return jsonify({'status': 'success', 'message': msg, 'id': lang.id})
            flash(msg, 'success')
            return redirect(url_for('properties.index'))

        elif attr_type == 'country':
            clean_name = name
            clean_code = code
            if not clean_code:
                msg = 'Country code is required.'
                if is_ajax:
                    return jsonify({'status': 'error', 'message': msg}), 400
                flash(msg, 'error')
                return redirect(url_for('properties.index'))

            existing = Country.query.filter(
                or_(
                    func.lower(Country.name) == clean_name.lower(),
                    func.upper(Country.code) == clean_code
                )
            ).first()
            if existing:
                if existing.deleted_at:
                    existing.name = clean_name
                    existing.code = clean_code
                    existing.deleted_at = None
                    existing.deleted_by = 0
                    existing.updated_by = session.get('user_id', 0)
                    db.session.commit()
                    msg = f"Country '{clean_name}' ({clean_code}) has been restored."
                    if is_ajax:
                        return jsonify({'status': 'success', 'message': msg, 'data': {'id': existing.id, 'name': existing.name, 'code': existing.code}})
                    flash(msg, 'success')
                    return redirect(url_for('properties.index'))

                msg = f"Country with name '{clean_name}' or code '{clean_code}' already exists."
                if is_ajax:
                    return jsonify({'status': 'error', 'message': msg}), 422
                flash(msg, 'error')
                return redirect(url_for('properties.index'))

            country = Country(name=clean_name, code=clean_code, created_by=session.get('user_id', 0), deleted_by=0)
            db.session.add(country)
            db.session.commit()
            msg = f"Country '{clean_name}' ({clean_code}) added successfully."
            if is_ajax:
                return jsonify({'status': 'success', 'message': msg, 'id': country.id})
            flash(msg, 'success')
            return redirect(url_for('properties.index'))

        else:
            msg = 'Invalid attribute type.'
            if is_ajax:
                return jsonify({'status': 'error', 'message': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('properties.index'))

    except Exception as e:
        db.session.rollback()
        msg = f"Failed to add attribute: {str(e)}"
        if is_ajax:
            return jsonify({'status': 'error', 'message': msg}), 500
        flash(msg, 'error')
        return redirect(url_for('properties.index'))
