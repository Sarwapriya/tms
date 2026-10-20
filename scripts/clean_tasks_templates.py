import re

def clean_tasks_list():
    path = r'app\templates\tasks\list.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. Total logs
    c = re.sub(r'<\?php\s*\$totalLogs\s*=\s*isset\(\$pager\).*?\?>', '{{ totalLogs }}', c)

    # 2. Labels select options
    old_lbl = re.search(r'<\?php\s*\$selectedLabels\s*=\s*\(array\).*?foreach \(\$all_labels as \$lbl\):\s*\?>', c, flags=re.DOTALL)
    if old_lbl:
        new_lbl = """{% set selectedLabels = filters.get('labels') or [] %}
                    {% for lbl in all_labels %}"""
        c = c.replace(old_lbl.group(0), new_lbl)

    # 3. Table row assignment block
    old_row = re.search(r'<\?php\s*foreach\s*\(\$logs\s+as\s+\$log\):.*?<\?=\s*\$log\[[\'"]id[\'"]\]\s*\?>', c, flags=re.DOTALL)
    if old_row:
        new_row = """{% for log in logs %}
                    {% set subsidiary = Constants.ACTIVITY_LOG_SUBSIDIARIES.get(log['subsidiary_id'], 'Unknown') %}
                    {% set status_str = Constants.ACTIVITY_LOGS_STATUS.get(log['status'], 'Unknown') %}
                    {% set type_str = Constants.ACTIVITY_TYPES.get(log['type'], 'Unknown') %}
                    {% set team = Constants.TEAMS.get(log['team_id'], 'Unknown') %}
                    {% set project = log['project'] or 'Generic' %}
                    {% set assignee = Constants.USERS.get(log['assignee'], Constants.USER_SYSTEM_LABEL) %}
                    {% set size = Constants.ACTIVITY_SIZES.get(log['size'], 'Unknown') %}
                    <tr>
                        <td>{{ log['id'] }}</td>"""
        c = c.replace(old_row.group(0), new_row)

    # 4. Labels in table row
    old_row_lbls = re.search(r'<\?php\s*foreach\s*\(explode\([\'"],[\'"],\s*\$log\[[\'"]labels[\'"]\]\).*?<\?php\s*endforeach;\s*\?>', c, flags=re.DOTALL)
    if old_row_lbls:
        new_row_lbls = """{% if log['labels'] %}
                        {% for raw_lbl in log['labels'].split(',') %}
                            {% set lbl = raw_lbl.strip() %}
                            {% if lbl %}
                                <span class="badge bg-primary text-white d-inline-flex align-items-center gap-1 rounded-pill"
                                    style="font-size: 0.68rem; font-weight: 500; background-color: var(--color-badge-primary-bg) !important; color: var(--color-badge-primary-text) !important; border: 1px solid var(--color-badge-primary-border) !important; padding: 0.2em 0.5em; cursor: pointer;">
                                    <i class="bi bi-tag-fill text-primary" style="font-size: 0.65rem; opacity: 0.7;"></i>
                                    {{ lbl }}
                                </span>
                            {% endif %}
                        {% endfor %}
                    {% endif %}"""
        c = c.replace(old_row_lbls.group(0), new_row_lbls)

    # 5. Campaign status
    old_cstatus = re.search(r'<\?php\s*\$cStatus\s*=\s*Constants\.CAMPAIGN_STATUS\[\$log\[[\'"]campaign_status[\'"]\]\].*?<\?=\s*esc\(\$cStatus\)\s*\?>', c, flags=re.DOTALL)
    if old_cstatus:
        new_cstatus = """{% set cStatus = Constants.CAMPAIGN_STATUS.get(log['campaign_status'], '—') %}
                    <span class="badge" style="{{ random_bg_style(cStatus) }}">
                        {{ cStatus }}
                    </span>"""
        c = c.replace(old_cstatus.group(0), new_cstatus)

    # Any remaining $var replacements inside {{ }} or {% %}
    c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Cleaned tasks/list.html")

def clean_tasks_view():
    path = r'app\templates\tasks\view.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Labels pill loop
    old_lbls = re.search(r'<\?php\s*foreach\s*\(explode\([\'"],[\'"],\s*\$task\[[\'"]labels[\'"]\]\).*?<\?php\s*endforeach;\s*\?>', c, flags=re.DOTALL)
    if old_lbls:
        new_lbls = """{% if task['labels'] %}
                    {% for raw_lbl in task['labels'].split(',') %}
                        {% set lbl = raw_lbl.strip() %}
                        {% if lbl %}
                            <span class="badge bg-primary text-white d-inline-flex align-items-center gap-1 rounded-pill"
                                style="font-size: 0.75rem; font-weight: 500; background-color: var(--color-badge-primary-bg) !important; color: var(--color-badge-primary-text) !important; border: 1px solid var(--color-badge-primary-border) !important; padding: 0.25em 0.6em;">
                                <i class="bi bi-tag-fill text-primary" style="font-size: 0.7rem; opacity: 0.7;"></i>
                                {{ lbl }}
                            </span>
                        {% endif %}
                    {% endfor %}
                {% endif %}"""
        c = c.replace(old_lbls.group(0), new_lbls)

    # Diff days for related tags
    old_diff = re.search(r'<\?php\s*\$diffDays\s*=\s*null;.*?al_end_date.*?\?>', c, flags=re.DOTALL)
    if old_diff:
        new_diff = "{% set diffDays = None %}"
        c = c.replace(old_diff.group(0), new_diff)

    # Campaign status
    old_cstatus = re.search(r'<\?php\s*\$cStatus\s*=\s*Constants\.CAMPAIGN_STATUS.*?<\?=\s*esc\(\$cStatus\)\s*\?>', c, flags=re.DOTALL)
    if old_cstatus:
        new_cstatus = """{% set cStatus = Constants.CAMPAIGN_STATUS.get(task['campaign_status'], '—') %}
                    <span class="badge" style="{{ random_bg_style(cStatus) }}">
                        {{ cStatus }}
                    </span>"""
        c = c.replace(old_cstatus.group(0), new_cstatus)

    # Comments loop
    old_comments = re.search(r'<\?php\s*if\s*\(!empty\(\$comments\)\):\s*foreach\s*\(\$comments\s+as\s+\$comment\):\s*\?>', c, flags=re.DOTALL)
    if old_comments:
        new_comments = "{% if comments %}{% for comment in comments %}"
        c = c.replace(old_comments.group(0), new_comments)
    c = c.replace('<?php endforeach; endif; ?>', '{% endfor %}{% endif %}')
    c = c.replace('<?php endforeach; ?>', '{% endfor %}')

    c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Cleaned tasks/view.html")

def clean_tasks_spreadsheet():
    path = r'app\templates\tasks\project_spreadsheet.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Active count badge
    old_badge = re.search(r'<\?php\s*\$activeCount\s*=\s*\$project_comment_counts.*?\?>', c, flags=re.DOTALL)
    if old_badge:
        new_badge = "{% set activeCount = project_comment_counts.get(project_name, 0) if project_comment_counts else 0 %}"
        c = c.replace(old_badge.group(0), new_badge)

    # Project tab active check
    old_tab = re.search(r'<\?php\s*\$pName\s*=\s*!empty\(\$p\).*?\?>', c, flags=re.DOTALL)
    if old_tab:
        new_tab = "{% set pName = p or 'Generic' %}{% set isActive = (pName == project_name) %}"
        c = c.replace(old_tab.group(0), new_tab)

    # Pager index
    old_pindex = re.search(r'<\?php\s*\$currentPage\s*=\s*isset\(\$pager\).*?\?>', c, flags=re.DOTALL)
    if old_pindex:
        new_pindex = "{% set rowIndex = loop.index %}"
        c = c.replace(old_pindex.group(0), new_pindex)

    c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Cleaned tasks/project_spreadsheet.html")

def clean_tasks_create_update():
    for fname in ['create.html', 'update.html']:
        path = f'app/templates/tasks/{fname}'
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()

        # Top settings block
        c = re.sub(r'<\?php\s*\$sysSettings\s*=\s*\\App\\Controllers\\SettingsController.*?\$isAdmin\s*=.*?;?\s*\?>', 
                   "{% set hideAssigneeSystemWide = false %}{% set isDWF = (Constants.USER_TEAMS.get(session.get('user_id')) == Constants.TEAM_DWF) %}", c, flags=re.DOTALL)

        # Labels select
        old_labels = re.search(r'<\?php\s*(?:\$oldLabelsInput|\$selectedLabels).*?foreach \(\$all_labels as \$lbl\):\s*\?>', c, flags=re.DOTALL)
        if old_labels:
            new_labels = """{% set selectedLabels = task['labels'].split(',') if task and task['labels'] else [] %}
                        {% for lbl in all_labels %}"""
            c = c.replace(old_labels.group(0), new_labels)

        # Department select
        old_dept = re.search(r'<\?php\s*\$selectedDepartment\s*=.*?\?>', c, flags=re.DOTALL)
        if old_dept:
            new_dept = "{% set selectedDepartment = task['department_id'] if task else '' %}"
            c = c.replace(old_dept.group(0), new_dept)

        # Project select
        old_proj = re.search(r'<\?php\s*\$selectedProject\s*=.*?\?>', c, flags=re.DOTALL)
        if old_proj:
            new_proj = "{% set selectedProject = task['project'] if task else 'Generic' %}"
            c = c.replace(old_proj.group(0), new_proj)

        c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Cleaned tasks/{fname}")

if __name__ == '__main__':
    clean_tasks_list()
    clean_tasks_view()
    clean_tasks_spreadsheet()
    clean_tasks_create_update()
