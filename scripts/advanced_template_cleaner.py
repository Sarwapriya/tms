import os
import sys
sys.path.insert(0, '.')
import re
from app import create_app
import jinja2

def clean_template(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        c = f.read()

    orig = c

    # 1. Fix Constants ~ FOO to Constants.FOO
    c = re.sub(r'Constants\s*~\s*([A-Za-z0-9_]+)', r'Constants.\1', c)

    # 2. Fix foreach with extra PHP statements like $count++
    c = re.sub(
        r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\).*?:\s*(?:\$[a-zA-Z0-9_]+\+\+;)?\s*\?>',
        r'{% for \2 in \1 %}',
        c
    )
    c = re.sub(
        r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\s*=>\s*\$([a-zA-Z0-9_]+)\).*?:\s*(?:\$[a-zA-Z0-9_]+\+\+;)?\s*\?>',
        r'{% for \2, \3 in \1.items() %}',
        c
    )

    # 3. Fix (int), (string), (array) PHP casts inside {{ }} and {% %}
    def remove_casts(match):
        block = match.group(0)
        block = re.sub(r'\((?:int|integer|string|array|bool|boolean|float)\)', '', block)
        return block

    c = re.sub(r'\{\{.*?\}\}', remove_casts, c, flags=re.DOTALL)
    c = re.sub(r'\{%.*?%\}', remove_casts, c, flags=re.DOTALL)

    # 4. Convert ternary operators: (cond) ? "A" : "B" or cond ? 'A' : 'B'
    def convert_ternaries(match):
        block = match.group(0)
        is_print = block.startswith('{{')

        # Pattern: expr ? expr : expr
        # We need to find `?` and `:` that are outside of quotes
        # Simple common pattern for {{ cond ? a : b }}
        m = re.match(r'^(\{\{\s*)(.+?)\s*\?\s*(.+?)\s*:\s*(.+?)(\s*\}\})$', block)
        if m:
            prefix, cond, true_val, false_val, suffix = m.groups()
            # Clean up if cond has parentheses
            return f"{prefix}({true_val} if {cond} else {false_val}){suffix}"

        return block

    # Let's run a line-by-line regex for {{ ... ? ... : ... }}
    def line_ternary(line):
        return re.sub(
            r'\{\{\s*([^{}]+?)\s*\?\s*([^{}:]+?)\s*:\s*([^{}]+?)\s*\}\}',
            r'{{ (\2 if \1 else \3) }}',
            line
        )

    lines = c.split('\n')
    lines = [line_ternary(l) for l in lines]
    c = '\n'.join(lines)

    # 5. Fix string concatenation with '.' inside {{ }}
    def fix_dots(match):
        expr = match.group(0)
        # e.g. 'tags/verify/' ~ tag['id'] . '?return_url='
        # replace any remaining . with ~ if between expressions
        # but not attribute lookups like tag.id or Constants.FOO
        expr = re.sub(r'(?<=[)\'\"\]])\s*\.\s*(?=[\'\"\(a-zA-Z0-9_])', ' ~ ', expr)
        expr = re.sub(r'(?<=[a-zA-Z0-9_])\s*\.\s*(?=[\'\"])', ' ~ ', expr)
        return expr

    c = re.sub(r'\{\{.*?\}\}', fix_dots, c, flags=re.DOTALL)

    # 6. Any remaining <?php ... ?> tags that can be safely removed
    c = re.sub(r'<\?php\s*use\s+[^;]+;?\s*\?>', '', c)
    c = re.sub(r'<\?php\s*helper\([^)]+\);?\s*\?>', '', c)
    c = re.sub(r'<\?php\s*\?>', '', c)

    if c != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Cleaned {filepath}")

if __name__ == '__main__':
    for root, _, files in os.walk('app/templates'):
        for f in files:
            if f.endswith('.html'):
                clean_template(os.path.join(root, f))
