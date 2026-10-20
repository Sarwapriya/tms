import re

def fix_tasks_list():
    path = r'app\templates\tasks\list.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = re.sub(
        r'<td colspan="\{\{\s*16\s*if\s*\(isDWF\s*else\s*14\)\s*-\s*\(hideAssigneeSystemWide\s*\?\s*1\s*:\s*0\)\s*\}\}"',
        '<td colspan="{{ (16 if isDWF else 14) - (1 if hideAssigneeSystemWide else 0) }}"',
        c
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed list.html")

def fix_tasks_view():
    path = r'app\templates\tasks\view.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = c.replace("{% if comment['commented_by'] not = Constants.USER_SYSTEM %}", "{% if comment['commented_by'] != Constants.USER_SYSTEM %}")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed view.html")

def fix_tasks_create():
    path = r'app\templates\tasks\create.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Fix project select
    old_proj = re.search(r'<select name="project" id="project-select".*?<\/select>', c, flags=re.DOTALL)
    if old_proj:
        new_proj = """<select name="project" id="project-select" class="form-select form-select-xs" required>
                                {% set selectedProject = log['project'] if log and log['project'] else 'Generic' %}
                                {% for pName in project_names %}
                                    <option value="{{ pName }}" {{ 'selected' if selectedProject == pName else '' }}>
                                        {{ pName }}
                                    </option>
                                {% endfor %}
                                {% if not in_array('Generic', project_names) and selectedProject != 'Generic' %}
                                    <option value="Generic">Generic</option>
                                {% endif %}
                            </select>"""
        c = c.replace(old_proj.group(0), new_proj)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed create.html")

def fix_tasks_update():
    path = r'app\templates\tasks\update.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Validation block
    c = re.sub(
        r'\{%\s*if\s*validation\s*is\s*defined\s*%\}.*?\{%\s*endif\s*%\}',
        '',
        c,
        flags=re.DOTALL
    )

    c = re.sub(
        r'action="\{\{\s*site_url\("tasks/update/\{log\[\'id\'\]\}"\)\s*\}\}"',
        'action="{{ site_url(\'tasks/update/\' ~ log[\'id\']) }}"',
        c
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed update.html")

def fix_project_spreadsheet():
    path = r'app\templates\tasks\project_spreadsheet.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Fix activeCount badge
    c = re.sub(
        r'\{%\s*set\s*activeCount\s*=\s*project_comment_counts\.get\(project_name,\s*0\)\s*if\s*project_comment_counts\s*else\s*0\s*%\}\s*<span class="badge bg-danger.*?<\/span>\s*\{%\s*endif\s*%\}',
        """{% set activeCount = project_comment_counts.get(project_name, 0) if project_comment_counts else 0 %}
                {% if activeCount > 0 %}
                    <span class="badge bg-danger text-white ms-1 rounded-circle" id="projectCommentsCountBadge" style="font-size: 0.7rem; padding: 0.25em 0.5em; min-width: 18px; text-align: center; line-height: 1;">
                        {{ activeCount }}
                    </span>
                {% endif %}""",
        c,
        flags=re.DOTALL
    )

    c = re.sub(
        r"site_url\('tasks/create\?project='\s*\.\s*rawurlencode\(project_name\)\)",
        "site_url('tasks/create?project=' ~ project_name)",
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
