import os
import re

def convert_php_to_jinja(content):
    # 1. Structure
    content = re.sub(r'<\?=\s*\$this->extend\([\'"]([^\'"]+)[\'"]\)\s*\?>', r"{% extends '\1.html' %}", content)
    content = re.sub(r'<\?=\s*\$this->section\([\'"]([^\'"]+)[\'"]\)\s*\?>', r"{% block \1 %}", content)
    content = re.sub(r'<\?=\s*\$this->endSection\(\)\s*\?>', r"{% endblock %}", content)

    # 2. Includes
    content = re.sub(r'<\?=\s*\$this->include\([\'"]([^\'"]+)[\'"]\)\s*\?>', r"{% include '\1.html' %}", content)

    # 3. CSRF & helpers
    content = re.sub(r'<\?=\s*csrf_field\(\)\s*\?>', r"{{ csrf_field() }}", content)
    content = re.sub(r'<\?php\s*helper\(.*?\);\s*\?>', '', content)
    content = re.sub(r'<\?php\s*use\s+App\\Models\\Constants;\s*\?>', '', content)

    # 4. Echo statements <?= ... ?>
    def convert_echo(match):
        expr = match.group(1).strip()
        # remove trailing semicolon
        expr = expr.rstrip(';')
        return f"{{{{ {expr} }}}}"

    content = re.sub(r'<\?=\s*(.*?)\s*\?>', convert_echo, content, flags=re.DOTALL)

    # 5. if / endif
    content = re.sub(r'<\?php\s*if\s*\((.*?)\)\s*:\s*\?>', r'{% if \1 %}', content)
    content = re.sub(r'<\?php\s*elseif\s*\((.*?)\)\s*:\s*\?>', r'{% elif \1 %}', content)
    content = re.sub(r'<\?php\s*else\s*:\s*\?>', r'{% else %}', content)
    content = re.sub(r'<\?php\s*endif;\s*\?>', r'{% endif %}', content)

    # 6. foreach / endforeach
    def convert_foreach(match):
        m = match.group(1).strip()
        if ' as ' in m:
            parts = m.split(' as ')
            iter_obj = parts[0].strip()
            val_part = parts[1].strip()
            if '=>' in val_part:
                k, v = val_part.split('=>')
                k = k.strip().lstrip('$')
                v = v.strip().lstrip('$')
                # Check if iterating Constants dict
                if 'Constants::' in iter_obj or 'Constants.' in iter_obj:
                    return f"{{% for {k}, {v} in {iter_obj}.items() %}}"
                return f"{{% for {k}, {v} in {iter_obj}.items() %}}"
            else:
                v = val_part.lstrip('$')
                return f"{{% for {v} in {iter_obj} %}}"
        return match.group(0)

    content = re.sub(r'<\?php\s*foreach\s*\((.*?)\)\s*:\s*\?>', convert_foreach, content)
    content = re.sub(r'<\?php\s*endforeach;\s*\?>', r'{% endfor %}', content)

    # 7. Constants:: to Constants.
    content = content.replace('Constants::', 'Constants.')

    # 8. Variable dollar signs inside {{ }} and {% %}
    def clean_vars(match):
        block = match.group(0)
        # remove $ before var names
        block = re.sub(r'\$([a-zA-Z0-9_]+)', r'\1', block)
        # replace -> with .
        block = re.sub(r'->([a-zA-Z0-9_]+)', r'.\1', block)
        # replace ?? with or
        block = re.sub(r'\s*\?\?\s*', ' or ', block)
        # replace || with or
        block = re.sub(r'\s*\|\|\s*', ' or ', block)
        # replace && with and
        block = re.sub(r'\s*&&\s*', ' and ', block)
        # replace ! with not
        block = re.sub(r'(?<=\s)!(?=[a-zA-Z(])', 'not ', block)
        # replace === with ==
        block = block.replace('===', '==')
        block = block.replace('!==', '!=')
        return block

    content = re.sub(r'\{\{.*?\}\}', clean_vars, content, flags=re.DOTALL)
    content = re.sub(r'\{%.*?%\}', clean_vars, content, flags=re.DOTALL)

    # 9. In string concatenation '.' to '~' inside {{ }}
    def clean_concat(match):
        block = match.group(0)
        # replace . surrounded by quotes or vars with ~
        block = re.sub(r'(["\']|\b[a-zA-Z0-9_\]]+\b)\s*\.\s*(["\']|\b[a-zA-Z0-9_\[]+\b)', r'\1 ~ \2', block)
        return block

    content = re.sub(r'\{\{.*?\}\}', clean_concat, content, flags=re.DOTALL)

    # 10. String concatenation in site_url
    content = re.sub(r"site_url\((['\"][^'\"]+['\"])\s*\.\s*", r"site_url(\1 ~ ", content)

    # 11. Clean remaining <?php ... ?> blocks that only have assignments or are empty
    content = re.sub(r'<\?php\s*\?>', '', content)

    return content

def port_file(src, dst):
    if not os.path.exists(src):
        print(f"Not found: {src}")
        return
    with open(src, 'r', encoding='utf-8') as f:
        php_content = f.read()

    jinja_content = convert_php_to_jinja(php_content)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(jinja_content)
    print(f"Ported {src} -> {dst} ({len(jinja_content)} bytes)")

if __name__ == '__main__':
    # 1. Tags views
    tags_views = [
        'create', 'update', 'view', 'repository', 'renew',
        'renewal_justifications', 'update-rule-request', 'upload_renewal_justifications'
    ]
    for v in tags_views:
        src = f'../app/Views/tags/{v}.php'
        dst = f'app/templates/tags/{v.replace("-", "_")}.html'
        port_file(src, dst)
        if '-' in v:
            # Also keep hyphenated filename
            port_file(src, f'app/templates/tags/{v}.html')

    # 2. Tag Requests views
    req_views = [
        'list', 'create', 'view', 'create_from_excel', 'upload_excel',
        'capture_tags', 'shop_manual_input'
    ]
    for v in req_views:
        src = f'../app/Views/tag-requests/{v}.php'
        dst = f'app/templates/tag_requests/{v}.html'
        port_file(src, dst)

    # 3. Properties views
    for v in ['list', 'create']:
        src = f'../app/Views/properties/{v}.php'
        dst = f'app/templates/properties/{v}.html'
        port_file(src, dst)

    # 4. Vendors views
    for v in ['list', 'update', 'view']:
        src = f'../app/Views/vendors/{v}.php'
        dst = f'app/templates/vendors/{v}.html'
        port_file(src, dst)

    # 5. Reports views
    for v in ['index', 'pdf']:
        src = f'../app/Views/reports/{v}.php'
        dst = f'app/templates/reports/{v}.html'
        port_file(src, dst)

    # 6. Settings views
    port_file('../app/Views/settings/index.php', 'app/templates/settings/index.html')

    # 7. Profile views
    port_file('../app/Views/profile/index.php', 'app/templates/profile/index.html')

    # 8. Jira views
    for v in ['list', 'create', 'add-entry', 'update_tags']:
        src = f'../app/Views/jira/{v}.php'
        dst = f'app/templates/jira/{v.replace("-", "_")}.html'
        port_file(src, dst)
        if '-' in v:
            port_file(src, f'app/templates/jira/{v}.html')
