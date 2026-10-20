import re

def fix_tasks_list():
    path = r'app\templates\tasks\list.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*===\s*'pending'\s*\?\s*'active'\s*if\s*\(filters\['status_group'\]\s*else\s*''\s*\}\}",
        "{{ 'active' if filters.get('status_group') == 'pending' else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*===\s*'in_progress'\s*\?\s*'active'\s*if\s*\(filters\['status_group'\]\s*else\s*''\s*\}\}",
        "{{ 'active' if filters.get('status_group') == 'in_progress' else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*===\s*'blocked'\s*\?\s*'active'\s*if\s*\(filters\['status_group'\]\s*else\s*''\s*\}\}",
        "{{ 'active' if filters.get('status_group') == 'blocked' else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*===\s*'needs_attention'\s*\?\s*'active'\s*if\s*\(filters\['status_group'\]\s*else\s*''\s*\}\}",
        "{{ 'active' if filters.get('status_group') == 'needs_attention' else '' }}",
        c
    )
    c = re.sub(
        r"\{\{\s*\?\s*''\)\s*===\s*'completed'\s*\?\s*'active'\s*if\s*\(filters\['status_group'\]\s*else\s*''\s*\}\}",
        "{{ 'active' if filters.get('status_group') == 'completed' else '' }}",
        c
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed tasks/list.html")

def fix_tasks_view():
    path = r'app\templates\tasks\view.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = c.replace('{% if diffDays not == null %}', '{% if diffDays is not none %}')
    c = c.replace('{% if diffDays not == None %}', '{% if diffDays is not none %}')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed tasks/view.html")

def fix_tasks_create_update():
    flash_block = """{% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ 'danger' if category == 'error' else category }} mb-4">
                    {{ message }}
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}"""

    for fname in ['create.html', 'update.html']:
        path = f'app/templates/tasks/{fname}'
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()

        c = re.sub(
            r'\{%\s*if\s*session\(\)->getFlashdata\(\'error\'\)\s*%\}.*?\{%\s*endif\s*%\}',
            flash_block,
            c,
            flags=re.DOTALL
        )
        c = re.sub(
            r'\{\{\s*session\(\)->getFlashdata\(.*?\)\s*\}\}',
            '',
            c
        )

        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Fixed tasks/{fname}")

def fix_project_spreadsheet():
    path = r'app\templates\tasks\project_spreadsheet.html'
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = re.sub(
        r"\{\{\s*'background-color\s*if\s*\(progress_percentage\s*is\s*defined\s*and\s*progress_percentage\s*<\s*100\)\s*else\s*#0071E3;'\s*:\s*''\s*\}\}",
        "{{ 'background-color: #0071E3;' if (progress_percentage is defined and progress_percentage < 100) else '' }}",
        c
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed tasks/project_spreadsheet.html")

if __name__ == '__main__':
    fix_tasks_list()
    fix_tasks_view()
    fix_tasks_create_update()
    fix_project_spreadsheet()
