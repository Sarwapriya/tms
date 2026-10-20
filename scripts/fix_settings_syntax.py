import re

def clean_settings():
    path = 'app/templates/settings/index.html'
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()

    # 1. Remove (int) casts
    txt = txt.replace('(int)', '')
    txt = txt.replace('(string)', '')

    # 2. Fix concatenation . with ~ inside {{ }}
    # Specifically: user['first_name'] . ' ' ~ user['last_name']
    txt = txt.replace("user['first_name'] . ' ' ~ user['last_name']", "user['first_name'] ~ ' ' ~ user['last_name']")
    txt = txt.replace("user['first_name'] . ' ' . user['last_name']", "user['first_name'] ~ ' ' ~ user['last_name']")
    txt = txt.replace("substr(user['first_name'], 0, 1) . substr(user['last_name'], 0, 1)", "substr(user['first_name'], 0, 1) ~ substr(user['last_name'], 0, 1)")

    # 3. session().get -> session.get
    txt = txt.replace("session().get", "session.get")

    # 4. Check for any remaining foreach ($modules as $key => $meta):
    txt = re.sub(
        r'<\?php\s*foreach\s*\(\$modules\s+as\s+\$key\s*=>\s*\$meta\):\s*\?>',
        '{% for key, meta in modules.items() %}',
        txt
    )

    # 5. Check for any remaining <?php foreach ... ?>
    def repl_foreach(m):
        raw = m.group(1).strip()
        if ' as ' in raw:
            parts = raw.split(' as ')
            obj = parts[0].strip().lstrip('$')
            val = parts[1].strip()
            if '=>' in val:
                k, v = val.split('=>')
                return f"{{% for {k.strip().lstrip('$')}, {v.strip().lstrip('$')} in {obj}.items() %}}"
            return f"{{% for {val.strip().lstrip('$')} in {obj} %}}"
        return m.group(0)

    txt = re.sub(r'<\?php\s*foreach\s*\((.*?)\)\s*:\s*\?>', repl_foreach, txt)
    txt = re.sub(r'<\?php\s*endforeach;\s*\?>', '{% endfor %}', txt)
    txt = re.sub(r'<\?php\s*endif;\s*\?>', '{% endif %}', txt)
    txt = re.sub(r'<\?php\s*else\s*:\s*\?>', '{% else %}', txt)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt)
    print("Cleaned settings/index.html")

if __name__ == '__main__':
    clean_settings()
