import os
import sys
sys.path.insert(0, '.')
import re
import glob
from app import create_app
import jinja2

def auto_fix_template(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        c = f.read()

    orig = c

    # 1. Remove <?php ... ?> tags
    c = re.sub(r'<\?php\s*helper\(.*?\);\s*\?>', '', c)
    c = re.sub(r'<\?php\s*use\s+.*?;?\s*\?>', '', c)
    c = re.sub(r'<\?php\s*\$sysSettings\s*=.*?\?>', '', c, flags=re.DOTALL)
    c = re.sub(r'<\?php\s*\$isAdmin\s*=.*?\?>', '', c, flags=re.DOTALL)

    # 2. Variable syntax inside {{ }} and {% %}
    c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)
    c = re.sub(r'([a-zA-Z0-9_]+)->([a-zA-Z0-9_]+)', r'\1.\2', c)
    c = c.replace('session()->get', 'session.get')
    c = c.replace('session.get', 'session.get')

    # 3. String concatenation . to ~ inside {{ }}
    c = re.sub(r"site_url\((['\"][^'\"]+['\"])\s*\.\s*", r"site_url(\1 ~ ", c)
    c = re.sub(r"Constants\.JIRA_LINK\s*\.\s*", r"Constants.JIRA_LINK ~ ", c)
    c = re.sub(r"Constants\.MT_JIRA_LINK\s*\.\s*", r"Constants.MT_JIRA_LINK ~ ", c)
    c = re.sub(r"url_for\((['\"][^'\"]+['\"])\s*\.\s*", r"url_for(\1 ~ ", c)

    # 4. Common dict iterations .items()
    dict_names = [
        'CAMPAIGN_STATUS', 'ACTIVITY_LOGS_STATUS', 'PRIORITIES',
        'ACTIVITY_SIZES', 'USERS', 'ACTIVITY_LOG_SUBSIDIARIES',
        'TEAMS', 'ACTIVITY_TYPES', 'STATUS', 'USER_ROLES', 'ACCOUNT_TYPES'
    ]
    for dname in dict_names:
        pat = r'\{%\s*for\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s+in\s+Constants\.' + dname + r'(?!\.items\(\))\s*%\}'
        repl = r'{% for \1, \2 in Constants.' + dname + r'.items() %}'
        c = re.sub(pat, repl, c)

    # 5. Operators
    c = re.sub(r'\s*\?\?\s*', ' or ', c)
    c = re.sub(r'\s*\?:\s*', ' or ', c)
    c = c.replace('===', '==')
    c = c.replace('!==', '!=')

    # 6. flashdata
    c = re.sub(r'session\(\)\.getFlashdata\([\'"]error[\'"]\)', 'error', c)
    c = re.sub(r'session\(\)\.getFlashdata\([\'"]success[\'"]\)', 'success', c)

    # 7. Common select ternaries
    c = re.sub(r"\{\{\s*\?\s*''\)\s*==\s*([a-zA-Z0-9_]+)\s*\?\s*'selected'\s*if\s*old\((.*?)\)\s*else\s*''\s*\}\}", r"{{ 'selected' if old(\2) == \1 else '' }}", c)

    if c != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Applied general fixes to {filepath}")

def test_all_templates():
    app = create_app()
    with app.app_context():
        all_templates = []
        for root, _, files in os.walk('app/templates'):
            for f in files:
                if f.endswith('.html'):
                    rel = os.path.relpath(os.path.join(root, f), 'app/templates').replace('\\', '/')
                    all_templates.append(rel)

        print(f"Total templates to check: {len(all_templates)}")
        errors = []
        for tname in all_templates:
            try:
                app.jinja_env.get_template(tname)
            except jinja2.TemplateSyntaxError as e:
                errors.append((tname, e.lineno, e.message))
            except Exception as e:
                errors.append((tname, 0, str(e)))

        return errors

if __name__ == '__main__':
    # First pass: auto-fix all templates
    for root, _, files in os.walk('app/templates'):
        for f in files:
            if f.endswith('.html'):
                auto_fix_template(os.path.join(root, f))

    errors = test_all_templates()
    if not errors:
        print("ALL TEMPLATES COMPILED SUCCESSFULLY!")
    else:
        print(f"\nFound {len(errors)} template errors:")
        for tname, lno, msg in errors[:25]:
            print(f"  {tname}:{lno} -> {msg}")
