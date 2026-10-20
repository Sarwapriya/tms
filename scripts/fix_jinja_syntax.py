import re
import os

def fix_tasks_list():
    path = r'app\templates\tasks\list.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Replace table foreach block
    c = re.sub(
        r'<\?php\s*foreach\s*\(\$logs\s+as\s+\$log\):.*?\$size\s*=\s*Constants\.ACTIVITY_SIZES\[\$log\[[\'"]size[\'"]\]\]\s*\?\?>\s*<tr>',
        """{% for log in logs %}
                        {% set subsidiary = Constants.ACTIVITY_LOG_SUBSIDIARIES.get(log['subsidiary_id'], 'Unknown') %}
                        {% set status_str = Constants.ACTIVITY_LOGS_STATUS.get(log['status'], 'Unknown') %}
                        {% set type = Constants.ACTIVITY_TYPES.get(log['type'], 'Unknown') %}
                        {% set team = Constants.TEAMS.get(log['team_id'], 'Unknown') %}
                        {% set project = log['project'] or 'Generic' %}
                        {% set assignee = Constants.USERS.get(log['assignee'], Constants.USER_SYSTEM_LABEL) %}
                        {% set size = Constants.ACTIVITY_SIZES.get(log['size'], 'Unknown') %}
                        <tr>""",
        c,
        flags=re.DOTALL
    )

    # Replace label loop inside table
    c = re.sub(
        r'<\?php\s*foreach\s*\(explode\([\'"],[\'"],\s*\$log\[[\'"]labels[\'"]\]\)\s*as\s*\$lbl\):.*?\?>\s*<a href="\{\{\s*\$labelUrl\s*\}\}"',
        """{% for raw_lbl in log['labels'].split(',') %}
                                            {% set lbl = raw_lbl.strip() %}
                                            {% if lbl %}
                                                <a href="{{ site_url('tasks?keyword=' ~ lbl) }}" """,
        c,
        flags=re.DOTALL
    )
    c = re.sub(r'<\?php\s*endfor;\s*\?>\s*<\/div>\s*\{%\s*endif\s*%\}', '{% endif %}{% endfor %}</div>{% endif %}', c)
    c = re.sub(r'<\?php\s*endforeach;\s*\?>\s*<\/div>\s*\{%\s*endif\s*%\}', '{% endif %}{% endfor %}</div>{% endif %}', c)

    # Campaign status in table
    c = re.sub(
        r'<\?php\s*\$cStatus\s*=\s*Constants\.CAMPAIGN_STATUS\[\$log\[[\'"]campaign_status[\'"]\]\].*?\?>\s*<span class="badge" style="\{\{\s*random_bg_style\(\$cStatus\)\s*\}\}">\s*\{\{\s*\$cStatus\s*\}\}\s*</span>',
        """{% set cStatus = Constants.CAMPAIGN_STATUS.get(log['campaign_status'], '—') if log['campaign_status'] else '—' %}
                                    <span class="badge" style="{{ random_bg_style(cStatus) }}">
                                        {{ cStatus }}
                                    </span>""",
        c,
        flags=re.DOTALL
    )

    # String concatenation . to ~
    c = re.sub(r"site_url\('tasks/view/'\s*\.\s*log\['id'\]\)", "site_url('tasks/view/' ~ log['id'])", c)
    c = re.sub(r"site_url\('tasks/update/'\s*\.\s*log\['id'\]\)", "site_url('tasks/update/' ~ log['id'])", c)
    c = re.sub(r"site_url\('tasks/create\?duplicate_id='\s*\.\s*log\['id'\]\)", "site_url('tasks/create?duplicate_id=' ~ log['id'])", c)
    c = re.sub(r"site_url\('tasks/export\?'\s*\.\s*http_build_query\(_GET\)\)", "site_url('tasks/export')", c)
    c = re.sub(r"Constants\.JIRA_LINK\s*\.\s*log\['ticket_id'\]", "Constants.JIRA_LINK ~ log['ticket_id']", c)
    c = re.sub(r"Constants\.MT_JIRA_LINK\s*\.\s*log\['mt_jira_ticket'\]", "Constants.MT_JIRA_LINK ~ log['mt_jira_ticket']", c)

    # Null coalescing ?? to default
    c = c.replace('user_color_r ?? 0', "user_color_r|default(0)")
    c = c.replace('user_color_g ?? 113', "user_color_g|default(113)")
    c = c.replace('user_color_b ?? 227', "user_color_b|default(227)")
    c = c.replace("user_color ?? '#0071e3'", "user_color|default('#0071e3')")
    c = c.replace("log['requested_by'] ?? '—'", "log['requested_by']|default('—')")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed tasks/list.html")

def fix_tasks_view():
    path = r'app\templates\tasks\view.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Labels loop
    c = re.sub(
        r'<\?php\s*foreach\s*\(explode\([\'"],[\'"],\s*\$task\[[\'"]labels[\'"]\]\)\s*as\s*\$lbl\):.*?\?>\s*<a href="\{\{\s*\$labelUrl\s*\}\}"',
        """{% for raw_lbl in task['labels'].split(',') %}
                            {% set lbl = raw_lbl.strip() %}
                            {% if lbl %}
                                <a href="{{ site_url('tasks?keyword=' ~ lbl) }}" """,
        c,
        flags=re.DOTALL
    )
    c = re.sub(r'<\?php\s*endforeach;\s*\?>\s*<\/div>\s*\{%\s*endif\s*%\}', '{% endif %}{% endfor %}</div>{% endif %}', c)

    # Campaign status in view
    c = re.sub(
        r'<\?php\s*\$cStatus\s*=\s*Constants\.CAMPAIGN_STATUS.*?\}\s*\?>\s*<div class="fw-semibold mt-1 badge" style="\{\{\s*random_bg_style\(\$cStatus\)\s*\}\}">\s*\{\{\s*\$cStatus\s*\}\}<\/div>',
        """{% set cStatus = Constants.CAMPAIGN_STATUS.get(task['campaign_status'], '—') if task['campaign_status'] else '—' %}
                            <div class="fw-semibold mt-1 badge" style="{{ random_bg_style(cStatus) }}">
                                {{ cStatus }}</div>""",
        c,
        flags=re.DOTALL
    )

    c = c.replace("task['department_id'] ?? '—'", "task['department_id']|default('—')")
    c = c.replace("user_color_r ?? 0", "user_color_r|default(0)")
    c = c.replace("user_color_g ?? 113", "user_color_g|default(113)")
    c = c.replace("user_color_b ?? 227", "user_color_b|default(227)")
    c = c.replace("user_color ?? '#0071e3'", "user_color|default('#0071e3')")
    c = re.sub(r"site_url\('tasks/update/'\s*\.\s*task\['id'\]\)", "site_url('tasks/update/' ~ task['id'])", c)
    c = re.sub(r"site_url\('tasks/create\?duplicate_id='\s*\.\s*task\['id'\]\)", "site_url('tasks/create?duplicate_id=' ~ task['id'])", c)
    c = re.sub(r"Constants\.JIRA_LINK\s*\.\s*task\['ticket_id'\]", "Constants.JIRA_LINK ~ task['ticket_id']", c)
    c = re.sub(r"Constants\.MT_JIRA_LINK\s*\.\s*task\['mt_jira_ticket'\]", "Constants.MT_JIRA_LINK ~ task['mt_jira_ticket']", c)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed tasks/view.html")

def fix_tasks_create_update():
    for fname in ['create.html', 'update.html']:
        path = f'app/templates/tasks/{fname}'
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()

        # Remove top php block
        c = re.sub(r'<\?php\s*\$sysSettings\s*=\s*\\App\\Controllers\\SettingsController.*?sort\(\$requesterNamesList\);\s*\?>', 
                   "{% set hideAssigneeSystemWide = false %}", c, flags=re.DOTALL)

        # Labels select block
        c = re.sub(
            r'<\?php\s*\$oldLabelsInput\s*=.*?foreach\s*\(\$allOptions\s+as\s+\$lbl\):.*?if\s*\(empty\(trim\(\$lbl\)\)\)\s*continue;\s*\?>',
            """{% set selectedLabels = (log['labels'].split(',') if log and log['labels'] else []) %}
                            {% for lbl in all_labels|default([]) %}""",
            c,
            flags=re.DOTALL
        )
        c = c.replace('<?php endforeach; ?>', '{% endfor %}')

        c = c.replace("old('title', log['title'] ?? '')", "(old('title') or (log['title'] if log else ''))")
        c = c.replace("old('description', log['description'] ?? '')", "(old('description') or (log['description'] if log else ''))")
        c = c.replace("old('ticket_id', log['ticket_id'] ?? '')", "(old('ticket_id') or (log['ticket_id'] if log else ''))")
        c = c.replace("old('requested_by', log['requested_by'] ?? '')", "(old('requested_by') or (log['requested_by'] if log else ''))")
        c = c.replace("old('start_date', !empty(log['start_date']) ? substr(log['start_date'], 0, 10) : '')", "old('start_date') or (log['start_date'][:10] if log and log['start_date'] else '')")
        c = c.replace("old('finished_date', !empty(log['finished_date']) ? substr(log['finished_date'], 0, 10) : '')", "old('finished_date') or (log['finished_date'][:10] if log and log['finished_date'] else '')")
        c = c.replace("old('target_end_date', !empty(log['target_end_date']) ? substr(log['target_end_date'], 0, 10) : '')", "old('target_end_date') or (log['target_end_date'][:10] if log and log['target_end_date'] else '')")
        c = c.replace("old('requested_date', !empty(log['requested_date']) ? substr(log['requested_date'], 0, 10) : '')", "old('requested_date') or (log['requested_date'][:10] if log and log['requested_date'] else '')")
        c = c.replace("old('campaign_start_date', !empty(log['campaign_start_date']) ? substr(log['campaign_start_date'], 0, 10) : '')", "old('campaign_start_date') or (log['campaign_start_date'][:10] if log and log['campaign_start_date'] else '')")
        c = c.replace("old('campaign_end_date', !empty(log['campaign_end_date']) ? substr(log['campaign_end_date'], 0, 10) : '')", "old('campaign_end_date') or (log['campaign_end_date'][:10] if log and log['campaign_end_date'] else '')")

        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Fixed tasks/{fname}")

if __name__ == '__main__':
    fix_tasks_list()
    fix_tasks_view()
    fix_tasks_create_update()
