import os
import re

SRC_DIR = r"d:\www-apps\tag-monitoring\app\Views"
DEST_DIR = r"d:\www-apps\tag-monitoring\python-app\app\templates"

def convert_php_expr_to_jinja(expr):
    s = expr.strip()
    # Strip trailing semicolon
    s = s.rstrip(';').strip()
    
    # Handle esc(...)
    m_esc = re.match(r'^esc\((.*)\)$', s)
    if m_esc:
        s = m_esc.group(1).strip()

    # Handle ternary: cond ? val1 : val2
    # Be careful not to break URLs or complex strings
    # Simple ternary matching
    ternary_match = re.match(r'^(.*?)\s*\?\s*(.*?)\s*:\s*(.*)$', s)
    if ternary_match and '?' not in ternary_match.group(2) and '?' not in ternary_match.group(3):
        cond = clean_var_names(ternary_match.group(1).strip())
        val1 = clean_var_names(ternary_match.group(2).strip())
        val2 = clean_var_names(ternary_match.group(3).strip())
        return f"{val1} if {cond} else {val2}"

    return clean_var_names(s)

def clean_var_names(text):
    # Replace Constants::FOO with Constants.FOO
    text = re.sub(r'Constants::([A-Za-z0-9_]+)', r'Constants.\1', text)
    text = re.sub(r'\\App\\Models\\Constants::([A-Za-z0-9_]+)', r'Constants.\1', text)
    text = re.sub(r'App\\Models\\Constants::([A-Za-z0-9_]+)', r'Constants.\1', text)

    # Replace $var with var
    text = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', r'\1', text)

    # Replace -> with .
    text = re.sub(r'([a-zA-Z0-9_\]])\->([a-zA-Z0-9_]+)', r'\1.\2', text)

    # Boolean / null replacements (whole word)
    text = re.sub(r'\bnull\b', 'none', text)
    text = re.sub(r'\bNULL\b', 'none', text)
    text = re.sub(r'\btrue\b', 'true', text)
    text = re.sub(r'\bTRUE\b', 'true', text)
    text = re.sub(r'\bfalse\b', 'false', text)
    text = re.sub(r'\bFALSE\b', 'false', text)
    text = re.sub(r'\b&&', 'and', text)
    text = re.sub(r'\b\|\|', 'or', text)
    text = re.sub(r'!([a-zA-Z0-9_])', r'not \1', text)

    return text

def convert_php_content_to_jinja(content):
    # 1. Extends & Sections
    content = re.sub(r'<\?=\s*\$this->extend\([\'"]layouts/default[\'"]\)\s*\?>', r"{% extends 'layouts/default.html' %}", content)
    content = re.sub(r'<\?=\s*\$this->extend\([\'"](.*?)[\'"]\)\s*\?>', r"{% extends '\1.html' %}", content)
    content = re.sub(r'<\?=\s*\$this->section\([\'"](.*?)[\'"]\)\s*\?>', r"{% block \1 %}", content)
    content = re.sub(r'<\?=\s*\$this->endSection\(\)\s*\?>', r"{% endblock %}", content)

    # 2. Includes
    content = re.sub(r'<\?=\s*\$this->include\([\'"]layouts/sidebar[\'"]\)\s*\?>', r"{% include 'layouts/sidebar.html' %}", content)
    content = re.sub(r'<\?=\s*view\([\'"]components/chatbot[\'"].*?\)\s*\?>', r"{% include 'components/chatbot.html' %}", content)

    # 3. Control structures
    # foreach ($arr as $k => $v):
    content = re.sub(
        r'<\?php\s+foreach\s*\(\s*(\$?[a-zA-Z0-9_\[\]\->]+)\s+as\s+(\$?[a-zA-Z0-9_]+)\s*=>\s*(\$?[a-zA-Z0-9_]+)\s*\)\s*:\s*\?>',
        lambda m: f"{{% for {clean_var_names(m.group(2))}, {clean_var_names(m.group(3))} in {clean_var_names(m.group(1))}.items() if {clean_var_names(m.group(1))} is mapping else {clean_var_names(m.group(1))} %}}",
        content
    )
    # foreach ($arr as $v):
    content = re.sub(
        r'<\?php\s+foreach\s*\(\s*(\$?[a-zA-Z0-9_\[\]\->]+)\s+as\s+(\$?[a-zA-Z0-9_]+)\s*\)\s*:\s*\?>',
        lambda m: f"{{% for {clean_var_names(m.group(2))} in {clean_var_names(m.group(1))} %}}",
        content
    )
    content = re.sub(r'<\?php\s+endforeach;\s*\?>', r"{% endfor %}", content)

    # if (...):
    content = re.sub(
        r'<\?php\s+if\s*\((.*?)\)\s*:\s*\?>',
        lambda m: f"{{% if {clean_var_names(m.group(1).strip())} %}}",
        content
    )
    # elseif (...):
    content = re.sub(
        r'<\?php\s+elseif\s*\((.*?)\)\s*:\s*\?>',
        lambda m: f"{{% elif {clean_var_names(m.group(1).strip())} %}}",
        content
    )
    # else:
    content = re.sub(r'<\?php\s+else\s*:\s*\?>', r"{% else %}", content)
    # endif;
    content = re.sub(r'<\?php\s+endif;\s*\?>', r"{% endif %}", content)

    # 4. Expressions <?= ... ?>
    content = re.sub(
        r'<\?=\s*(.*?)\s*\?>',
        lambda m: f"{{{{ {convert_php_expr_to_jinja(m.group(1))} }}}}",
        content
    )

    # 5. Remove PHP open tags with just comments or helper calls
    content = re.sub(r'<\?php\s+helper\([^\)]+\);\s*\?>', '', content)
    content = re.sub(r'<\?php\s+use\s+[^\;]+;\s*\?>', '', content)

    return content

print("Converter script prepared.")
