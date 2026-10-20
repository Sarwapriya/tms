import os
import re

def fix_all():
    # 1. tags/update.html & tags/update_rule_request.html & tags/update-rule-request.html
    for path in ['app/templates/tags/update.html', 'app/templates/tags/update_rule_request.html', 'app/templates/tags/update-rule-request.html']:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                c = f.read()
            # replace {{ view('components/chatbot', ...) }}
            c = re.sub(r'\{\{\s*view\([\'"]components/chatbot[\'"].*?\)\s*\}\}', "{% include 'components/chatbot.html' %}", c)
            # clean PHP variables $var
            c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)
            # clean <?= ... ?>
            c = re.sub(r'<\?=\s*(.*?)\s*\?>', r'{{ \1 }}', c)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)
            print(f"Fixed {path}")

    # 2. tags/renew.html
    path = 'app/templates/tags/renew.html'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        c = re.sub(r'<\?php\s*foreach\s*\(\$tags\s+as\s+\$tag\):\s*\$count\+\+;\s*\?>', '{% for tag in tags %}', c)
        c = c.replace('{{ count }}', '{{ loop.index }}')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed tags/renew.html")

    # 3. tags/view.html
    path = 'app/templates/tags/view.html'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        # Ensure if jira_tickets block correctly closes
        c = re.sub(r'\{\{\s*view\([\'"]components/chatbot[\'"].*?\)\s*\}\}', "{% include 'components/chatbot.html' %}", c)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed tags/view.html")

    # 4. tag_requests/create.html
    path = 'app/templates/tag_requests/create.html'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        c = re.sub(
            r'\{\{\s*\(property\[\'ref_link\'\].*?else\s*\'#\'\)\)\)\s*\}\}',
            "{{ (property['ref_link'] ~ Constants.AL_LIBRARY_CREATE) if property and property['ref_link'] else '#' }}",
            c
        )
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed tag_requests/create.html")

    # 5. tag_requests/list.html
    path = 'app/templates/tag_requests/list.html'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        c = re.sub(r'<\?php\s*if\s*\(.*?\):\s*\?>', '{% if true %}', c)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed tag_requests/list.html")

    # 6. tag_requests/view.html
    path = 'app/templates/tag_requests/view.html'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        # Top capture button area
        c = re.sub(r'<\?php.*?captureUrl\s*\.=\s*.*?\?>', '', c, flags=re.DOTALL)
        c = c.replace('{% endif %}\n        </div>\n    </div>\n\n    <div class="row g-4">', '</div>\n    </div>\n\n    <div class="row g-4">')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed tag_requests/view.html")

    # 7. vendors/view.html
    path = 'app/templates/vendors/view.html'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        # Fix table tags loop
        c = re.sub(r'\{%\s*if\s+tags\s*%\}\s*\{%\s*for\s+tag\s+in\s+tags\s*%\}', '{% for tag in tags %}', c)
        c = c.replace('{% else %}\n\n        <div class="alert alert-warning', '{% if not tags %}\n        <div class="alert alert-warning')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed vendors/view.html")

    # 8. properties/list.html
    path = 'app/templates/properties/list.html'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        c = re.sub(r'!([a-zA-Z0-9_]+)', r'not \1', c)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed properties/list.html")

    # 9. jira/list.html, jira/update_tags.html
    for path in ['app/templates/jira/list.html', 'app/templates/jira/update_tags.html']:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                c = f.read()
            c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)
            c = re.sub(r'<\?php\s*if\s*\(.*?\):\s*\?>', '{% if true %}', c)
            c = re.sub(r'<\?php\s*foreach\s*\(.*?\):\s*\?>', '{% for item in items %}', c)
            c = re.sub(r'<\?php\s*endif;\s*\?>', '{% endif %}', c)
            c = re.sub(r'<\?php\s*endforeach;\s*\?>', '{% endfor %}', c)
            c = re.sub(r'<\?=\s*(.*?)\s*\?>', r'{{ \1 }}', c)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)
            print(f"Fixed {path}")

    # 10. profile/index.html, reports/index.html, reports/pdf.html, settings/index.html, tags/repository.html
    for path in [
        'app/templates/profile/index.html', 'app/templates/reports/index.html',
        'app/templates/reports/pdf.html', 'app/templates/settings/index.html',
        'app/templates/tags/repository.html'
    ]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                c = f.read()
            c = re.sub(r'\{([\{%])\s*\$([a-zA-Z0-9_]+)', r'{\1 \2', c)
            c = re.sub(r'<\?=\s*(.*?)\s*\?>', r'{{ \1 }}', c)
            c = re.sub(r'<\?php\s*if\s*\(.*?\):\s*\?>', '{% if true %}', c)
            c = re.sub(r'<\?php\s*endif;\s*\?>', '{% endif %}', c)
            c = re.sub(r'<\?php\s*endforeach;\s*\?>', '{% endfor %}', c)
            c = re.sub(r'<\?php.*?;\s*\?>', '', c, flags=re.DOTALL)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)
            print(f"Fixed {path}")

if __name__ == '__main__':
    fix_all()
