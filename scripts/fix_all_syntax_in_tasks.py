import os
import re

def fix_tasks_list():
    path = r'app\templates\tasks\list.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Replace bad select option ternaries
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('subsidiary_id',\s*filters\['subsidiary_id'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (filters.get('subsidiary_id')|string == value|string) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*==\s*pName\s*\?\s*'selected'\s*if\s*\(filters\['project'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (filters.get('project') == pName) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('assignee',\s*filters\['assignee'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (filters.get('assignee')|string == value|string) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*null\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('status',\s*filters\['status'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (filters.get('status')|string == value|string) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*null\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('priority',\s*filters\['priority'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (filters.get('priority')|string == value|string) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('type',\s*filters\['type'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (filters.get('type')|string == value|string) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*null\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('campaign_status',\s*filters\['campaign_status'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (filters.get('campaign_status')|string == value|string) else '' }}",
        c
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed list.html")

def fix_tasks_view():
    path = r'app\templates\tasks\view.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = c.replace("session()->get('user_id')", "session.get('user_id')")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed view.html")

def fix_tasks_create():
    path = r'app\templates\tasks\create.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = c.replace("session()->get('user_id')", "session.get('user_id')")
    c = c.replace("session()->get('user_name')", "session.get('user_name')")

    # Department select block
    old_dept = re.search(r'<select name="department_id".*?<\/select>', c, flags=re.DOTALL)
    if old_dept:
        new_dept = """<select name="department_id" id="department-select" class="form-select form-select-xs">
                                <option value="">-Select-</option>
                                {% for dName in department_names %}
                                    <option value="{{ dName }}" {{ 'selected' if (log and log['department_id'] == dName) else '' }}>
                                        {{ dName }}
                                    </option>
                                {% endfor %}
                            </select>"""
        c = c.replace(old_dept.group(0), new_dept)

    # Option ternaries in create
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('campaign_status'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['campaign_status'] == value) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*Constants\.ACTIVITY_LOGS_STATUS_TO_DO\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('status'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['status'] == value) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*Constants\.PRIORITY_DEFAULT\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('priority'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['priority'] == value) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*Constants\.ACTIVITY_SIZE_M\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('size'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['size'] == value) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*session.*?==\s*value\s*\?\s*'selected'\s*if\s*old\('assignee'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['assignee'] == value) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('subsidiary_id'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['subsidiary_id'] == value) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*Constants\.USER_TEAMS\[session.*?==\s*value\s*\?\s*'selected'\s*if\s*old\('team_id'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['team_id'] == value) else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*Constants\.ACTIVITY_TYPE_TASK\)\s*==\s*value\s*\?\s*'selected'\s*if\s*old\('type'.*?else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['type'] == value) else '' }}",
        c
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed create.html")

def fix_tasks_update():
    path = r'app\templates\tasks\update.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = c.replace("session()->get('user_id')", "session.get('user_id')")
    c = c.replace("session()->get('user_name')", "session.get('user_name')")

    # Department select block
    old_dept = re.search(r'<select name="department_id".*?<\/select>', c, flags=re.DOTALL)
    if old_dept:
        new_dept = """<select name="department_id" id="department-select" class="form-select form-select-xs">
                                <option value="">-Select-</option>
                                {% for dName in department_names %}
                                    <option value="{{ dName }}" {{ 'selected' if (log and log['department_id'] == dName) else '' }}>
                                        {{ dName }}
                                    </option>
                                {% endfor %}
                            </select>"""
        c = c.replace(old_dept.group(0), new_dept)

    # Project option
    c = re.sub(
        r"\{\{\s*\?\s*'Generic'\)\s*==\s*pName\s*\?\s*'selected'\s*if\s*old\('project',\s*log\['project'\]\s*else\s*''\s*\}\}",
        "{{ 'selected' if (log and log['project'] == pName) else '' }}",
        c
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed update.html")

def fix_project_spreadsheet():
    path = r'app\templates\tasks\project_spreadsheet.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = c.replace("session()->get('user_id')", "session.get('user_id')")
    c = c.replace("session()->get('user_name')", "session.get('user_name')")

    c = re.sub(
        r"this\.checked\s*\?\s*'\{\{\s*buildProjectUrl\(project_name,\s*\[\s*'show_completed'\s*=>\s*'1'\s*\]\)\s*\}\}'\s*:\s*'\{\{\s*buildProjectUrl\(project_name,\s*\[\s*'show_completed'\s*=>\s*'0'\s*\]\)\s*\}\}'",
        "this.checked ? '{{ buildProjectUrl(project_name, {'show_completed': '1'}) }}' : '{{ buildProjectUrl(project_name, {'show_completed': '0'}) }}'",
        c
    )

    c = re.sub(
        r"\{\{\s*'0'\s*if\s*buildProjectUrl\(project_name,\s*\[\s*'me_mode'\s*=>\s*\(me_mode\s*is\s*defined\s*and\s*me_mode\)\s*else\s*'1'\]\)\s*\}\}",
        "{{ buildProjectUrl(project_name, {'me_mode': '0' if me_mode else '1'}) }}",
        c
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed project_spreadsheet.html")

if __name__ == '__main__':
    fix_tasks_list()
    fix_tasks_view()
    fix_tasks_create()
    fix_tasks_update()
    fix_project_spreadsheet()
