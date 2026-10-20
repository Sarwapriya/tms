import os
import re

def convert_php_template(content):
    # 1. Structure
    # Strip any top-level PHP functions before extend
    content = re.sub(r'<\?php\s*function\s+getSortUrl.*?\?>\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'<\?=\s*\$this->extend\([\'"]([^\'"]+)[\'"]\)\s*\?>', r"{% extends '\1.html' %}", content)
    content = re.sub(r'<\?=\s*\$this->section\([\'"]([^\'"]+)[\'"]\)\s*\?>', r"{% block \1 %}", content)
    content = re.sub(r'<\?=\s*\$this->endSection\(\)\s*\?>', r"{% endblock %}", content)
    content = re.sub(r'<\?=\s*\$this->include\([\'"]([^\'"]+)[\'"]\)\s*\?>', r"{% include '\1.html' %}", content)

    # 2. CSRF & helpers
    content = re.sub(r'<\?=\s*csrf_field\(\)\s*\?>', r"{{ csrf_field() }}", content)
    content = re.sub(r'<\?php\s*helper\(.*?\);\s*\?>', '', content)
    content = re.sub(r'<\?php\s*use\s+App\\Models\\Constants;\s*\?>', '', content)

    # 3. Echo statements <?= ... ?>
    def convert_echo(match):
        expr = match.group(1).strip().rstrip(';')
        return f"{{{{ {expr} }}}}"
    content = re.sub(r'<\?=\s*(.*?)\s*\?>', convert_echo, content, flags=re.DOTALL)

    # 4. if / elseif / else / endif
    content = re.sub(r'<\?php\s*if\s*\((.*?)\)\s*:\s*\?>', r'{% if \1 %}', content)
    content = re.sub(r'<\?php\s*elseif\s*\((.*?)\)\s*:\s*\?>', r'{% elif \1 %}', content)
    content = re.sub(r'<\?php\s*else\s*:\s*\?>', r'{% else %}', content)
    content = re.sub(r'<\?php\s*endif;\s*\?>', r'{% endif %}', content)

    # 5. foreach / endforeach (single line)
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
                return f"{{% for {k}, {v} in {iter_obj}.items() %}}"
            else:
                v = val_part.lstrip('$')
                return f"{{% for {v} in {iter_obj} %}}"
        return match.group(0)

    content = re.sub(r'<\?php\s*foreach\s*\((.*?)\)\s*:\s*\?>', convert_foreach, content)
    content = re.sub(r'<\?php\s*endforeach;\s*\?>', r'{% endfor %}', content)

    # 6. Constants
    content = content.replace('Constants::', 'Constants.')

    # 7. Clean variables inside {{ }} and {% %}
    def clean_vars(match):
        block = match.group(0)
        block = re.sub(r'\$([a-zA-Z0-9_]+)', r'\1', block)
        block = re.sub(r'->([a-zA-Z0-9_]+)', r'.\1', block)
        block = re.sub(r'\s*\?\?\s*', ' or ', block)
        block = re.sub(r'\s*\|\|\s*', ' or ', block)
        block = re.sub(r'\s*&&\s*', ' and ', block)
        block = re.sub(r'(?<=\s)!(?=[a-zA-Z(])', 'not ', block)
        block = block.replace('===', '==')
        block = block.replace('!==', '!=')
        return block

    content = re.sub(r'\{\{.*?\}\}', clean_vars, content, flags=re.DOTALL)
    content = re.sub(r'\{%.*?%\}', clean_vars, content, flags=re.DOTALL)

    # 8. String concat in {{ }}
    def clean_concat(match):
        block = match.group(0)
        block = re.sub(r'(["\']|\b[a-zA-Z0-9_\]]+\b)\s*\.\s*(["\']|\b[a-zA-Z0-9_\[]+\b)', r'\1 ~ \2', block)
        return block
    content = re.sub(r'\{\{.*?\}\}', clean_concat, content, flags=re.DOTALL)

    return content

def rebuild():
    # Rebuild tags/repository.html
    src_repo = r'd:\www-apps\tag-monitoring\app\Views\tags\repository.php'
    with open(src_repo, 'r', encoding='utf-8') as f:
        repo_raw = f.read()

    # In repository.php, find table loop lines 680-725:
    # <?php foreach ($tags as $tag): ... ?>
    # Replace that specific block:
    repo_raw = re.sub(
        r'<\?php\s*\$currentQuery\s*=\s*\$_SERVER\[\'QUERY_STRING\'\].*?<\?php\s*foreach\s*\(\$tags\s+as\s+\$tag\):.*?\?>',
        '''{% if empty(tags) %}
                        <tr>
                            <td colspan="10" class="text-center py-5 text-muted">
                                <i class="bi bi-inbox fs-2 mb-2 d-block text-secondary" style="opacity: 0.5;"></i>
                                <span class="fw-semibold">No tags found</span>
                                <p class="small text-secondary mb-0">Try adjusting your filters or search keywords.</p>
                            </td>
                        </tr>
                    {% else %}
                        {% for tag in tags %}
                            {% set prop = properties.get(tag['property_id']) %}
                            {% set subsidiary = subsidiaries.get(prop['subsidiary_id'] if prop else 0, 'Global') %}
                            {% set property = prop['name'] if prop else 'Unknown' %}''',
        repo_raw,
        flags=re.DOTALL
    )

    repo_jinja = convert_php_template(repo_raw)
    
    # Save tags/repository.html
    with open('app/templates/tags/repository.html', 'w', encoding='utf-8') as f:
        f.write(repo_jinja)
    print("Rebuilt app/templates/tags/repository.html")

    # Rebuild settings/index.html
    src_set = r'd:\www-apps\tag-monitoring\app\Views\settings\index.php'
    with open(src_set, 'r', encoding='utf-8') as f:
        set_raw = f.read()

    # In settings/index.php, lines 10-16:
    set_raw = re.sub(r'<\?php\s*// Build a lookup map.*?\?>\s*', '', set_raw, flags=re.DOTALL)

    # In settings/index.php, user role mapping block in users table:
    set_raw = re.sub(
        r'<\?php\s*\$uRole\s*=\s*\$user\[\'role_id\'\].*?\$badgeClass\s*=\s*.*?;\s*\?>',
        '''{% set uRole = user['role_id'] or (Constants.USER_ACCESS_LEVELS.get(user['id'], (Constants.USER_ROLE_ADMIN if user['account_type'] == 1 else Constants.USER_ROLE_MEDIA_TAGGING))) %}
                                    {% set roleName = rolesMap.get(uRole, 'User') if rolesMap else 'User' %}
                                    {% set badgeClass = 'bg-danger-subtle text-danger' if uRole == Constants.USER_ROLE_ADMIN else ('bg-warning-subtle text-warning-emphasis' if uRole == Constants.USER_ROLE_MARTECH else ('bg-primary-subtle text-primary' if uRole == Constants.USER_ROLE_MEDIA_TAGGING else 'bg-secondary')) %}''',
        set_raw,
        flags=re.DOTALL
    )

    set_jinja = convert_php_template(set_raw)

    with open('app/templates/settings/index.html', 'w', encoding='utf-8') as f:
        f.write(set_jinja)
    print("Rebuilt app/templates/settings/index.html")

if __name__ == '__main__':
    rebuild()
