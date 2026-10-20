import os
import re

def fix_dict_iterations():
    dict_names = [
        'CAMPAIGN_STATUS', 'ACTIVITY_LOGS_STATUS', 'PRIORITIES',
        'ACTIVITY_SIZES', 'USERS', 'ACTIVITY_LOG_SUBSIDIARIES',
        'TEAMS', 'ACTIVITY_TYPES'
    ]

    for fname in ['list.html', 'view.html', 'create.html', 'update.html', 'project_spreadsheet.html']:
        path = os.path.join('app', 'templates', 'tasks', fname)
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()

        for dname in dict_names:
            # Match {% for val, lbl in Constants.DNAME %} without .items()
            pattern = r'\{%\s*for\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s+in\s+Constants\.' + dname + r'\s*%\}'
            replacement = r'{% for \1, \2 in Constants.' + dname + r'.items() %}'
            c = re.sub(pattern, replacement, c)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Fixed dict iterations in {fname}")

def fix_project_spreadsheet():
    path = os.path.join('app', 'templates', 'tasks', 'project_spreadsheet.html')
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    c = re.sub(
        r'\{%\s*if\s+count\s*>\s*0\s*%\}\s*<span class="badge bg-danger text-white ms-1 rounded-circle project-tab-badge".*?\{\{\s*count\s*\}\}\s*<\/span>\s*\{%\s*endif\s*%\}',
        """{% set pCount = project_comment_counts.get(pName, 0) if project_comment_counts else 0 %}
                {% if pCount > 0 %}
                    <span class="badge bg-danger text-white ms-1 rounded-circle project-tab-badge" style="font-size: 0.7rem; padding: 0.25em 0.5em; min-width: 18px; text-align: center; line-height: 1;">
                        {{ pCount }}
                    </span>
                {% endif %}""",
        c,
        flags=re.DOTALL
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Fixed project_spreadsheet tab badge")

def fix_dates_in_create_update():
    date_fields = [
        'requested_date', 'start_date', 'target_end_date',
        'finished_date', 'campaign_start_date', 'campaign_end_date'
    ]
    for fname in ['create.html', 'update.html']:
        path = os.path.join('app', 'templates', 'tasks', fname)
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()

        for dfield in date_fields:
            pat = r"\{\{\s*date\(['\"]Y-m-d['\"],\s*strtotime\(log\['" + dfield + r"'\]\)\)\s*if\s*log\['" + dfield + r"'\]\s*else\s*''\s*\}\}"
            repl = "{{ (log['" + dfield + "'][:10] if (log and log['" + dfield + "']) else '') }}"
            c = re.sub(pat, repl, c)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Fixed dates in {fname}")

if __name__ == '__main__':
    fix_dict_iterations()
    fix_project_spreadsheet()
    fix_dates_in_create_update()
