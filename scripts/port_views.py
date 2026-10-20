import os
import re

def php_to_jinja(text):
    # 1. Strip top-level helper & use imports
    text = re.sub(r'<\?php\s*use\s+[^;]+;\s*\?>', '', text)
    text = re.sub(r'<\?php\s*helper\([^)]+\);\s*\?>', '', text)
    text = re.sub(r'use\s+App\\Models\\[a-zA-Z0-9_]+;\s*', '', text)
    text = re.sub(r'helper\([\'"][^\'"]+[\'"]\);\s*', '', text)

    # 2. Template layout blocks
    text = re.sub(r'<\?=\s*\$this->extend\([\'"](.+?)[\'"]\)\s*\?>', r"{% extends '\1.html' %}", text)
    text = re.sub(r'<\?=\s*\$this->section\([\'"](.+?)[\'"]\)\s*\?>', r"{% block \1 %}", text)
    text = re.sub(r'<\?=\s*\$this->endSection\(\)\s*\?>', r"{% endblock %}", text)
    text = re.sub(r'<\?=\s*\$this->include\([\'"](.+?)[\'"]\)\s*\?>', r"{% include '\1.html' %}", text)

    # 3. CodeIgniter CSRF & URLs
    text = re.sub(r'<\?=\s*csrf_field\(\)\s*\?>', r"{{ csrf_field() }}", text)
    text = re.sub(r'<\?=\s*site_url\((.*?)\)\s*\?>', r"{{ site_url(\1) }}", text)
    text = re.sub(r'<\?=\s*base_url\((.*?)\)\s*\?>', r"{{ base_url(\1) }}", text)
    text = re.sub(r'<\?=\s*json_encode\((.*?)\)\s*\?>', r"{{ \1 | tojson }}", text)

    # 4. Escaped outputs
    text = re.sub(r'<\?=\s*esc\((.*?)\)\s*\?>', r"{{ \1 }}", text)
    text = re.sub(r'<\?=\s*htmlspecialchars\((.*?)\)\s*\?>', r"{{ \1 }}", text)

    # 5. Constants namespace
    text = re.sub(r'\\?App\\Models\\Constants::', r'Constants.', text)
    text = re.sub(r'Constants::', r'Constants.', text)

    # 6. Basic control structures in PHP tags
    # Foreach
    text = re.sub(r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\s*=>\s*\$([a-zA-Z0-9_]+)\)\s*:\s*\?>', 
                 r'{% for \2, \3 in \1 %}', text)
    text = re.sub(r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\)\s*:\s*\?>', 
                 r'{% for \2 in \1 %}', text)
    text = re.sub(r'<\?php\s*endforeach;?\s*\?>', r'{% endfor %}', text)

    # If / Elseif / Else
    text = re.sub(r'<\?php\s*if\s*\((.*?)\)\s*:\s*\?>', r'{% if \1 %}', text)
    text = re.sub(r'<\?php\s*elseif\s*\((.*?)\)\s*:\s*\?>', r'{% elif \1 %}', text)
    text = re.sub(r'<\?php\s*else\s*:\s*\?>', r'{% else %}', text)
    text = re.sub(r'<\?php\s*endif;?\s*\?>', r'{% endif %}', text)

    # Single-line expressions: <?= $var ?>
    def replace_echo(match):
        expr = match.group(1).strip()
        # strip trailing semicolon if present
        if expr.endswith(';'):
            expr = expr[:-1].strip()
        # replace ternary $a ? $b : $c with ($b if $a else $c)
        ternary_match = re.match(r'^(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$', expr)
        if ternary_match:
            cond = ternary_match.group(1).strip()
            val_true = ternary_match.group(2).strip()
            val_false = ternary_match.group(3).strip()
            return f"{{{{ {val_true} if {cond} else {val_false} }}}}"
        return f"{{{{ {expr} }}}}"

    text = re.sub(r'<\?=\s*(.*?)\s*\?>', replace_echo, text)

    # Remove remaining PHP dollar signs in Jinja expressions
    def clean_jinja_tags(match):
        tag_content = match.group(0)
        # remove '$' from variable names inside {{ }} and {% %}
        cleaned = re.sub(r'\$([a-zA-Z0-9_]+)', r'\1', tag_content)
        # replace PHP !empty(x) with x
        cleaned = re.sub(r'!empty\((.*?)\)', r'\1', cleaned)
        cleaned = re.sub(r'empty\((.*?)\)', r'not \1', cleaned)
        # replace PHP isset(x) with x is defined
        cleaned = re.sub(r'isset\((.*?)\)', r'\1 is defined', cleaned)
        # replace PHP && and || with and / or
        cleaned = cleaned.replace('&&', 'and').replace('||', 'or').replace('!', 'not ')
        # replace null with none
        cleaned = re.sub(r'\bnull\b', 'none', cleaned)
        return cleaned

    text = re.sub(r'(\{\{.*?\}\}|\{%.*?%\})', clean_jinja_tags, text, flags=re.DOTALL)

    return text

if __name__ == '__main__':
    print("Converter module ready.")
