import os
import re
import glob

def clean_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    orig = content

    # Replace _GET['keyword'] ?? '' or _GET[...] with request.args.get(...)
    content = re.sub(r"_GET\['([a-zA-Z0-9_]+)'\]\s*\?\?\s*''", r"request.args.get('\1', '')", content)
    content = re.sub(r"_GET\['([a-zA-Z0-9_]+)'\]", r"request.args.get('\1', '')", content)
    content = re.sub(r"\$_GET", r"request.args", content)

    # Replace filters['...'] ?? '...' with filters.get('...', '...')
    content = re.sub(r"filters\['([a-zA-Z0-9_]+)'\]\s*\?\?\s*'([^']*)'", r"filters.get('\1', '\2')", content)
    content = re.sub(r"filters\['([a-zA-Z0-9_]+)'\]\s*\?\?\s*\"([^\"]*)\"", r'filters.get("\1", "\2")', content)

    # Replace strip_tags(task['last_comment'] ?? '') ?: '—'
    content = content.replace("strip_tags(task['last_comment'] ?? 'No comments posted yet.')", "strip_tags(task['last_comment'] or 'No comments posted yet.')")
    content = content.replace("strip_tags(task['last_comment'] ?? '') ?: '—'", "strip_tags(task['last_comment'] or '') or '—'")

    # Common ?? patterns
    content = re.sub(r"([a-zA-Z0-9_]+)\s*\?\?\s*0", r"\1|default(0)", content)
    content = re.sub(r"([a-zA-Z0-9_]+)\s*\?\?\s*null", r"\1|default(none)", content)
    content = re.sub(r"Constants\.USERS\[comment\['commented_by'\]\]\s*\?\?\s*'Unknown'", r"Constants.USERS.get(comment['commented_by'], 'Unknown')", content)
    content = re.sub(r"old\('comment',\s*task\['comment'\]\s*\?\?\s*''\)", r"old('comment') or (task['comment'] if task else '')", content)
    content = re.sub(r"old\('campaign_id',\s*log\['campaign_id'\]\s*\?\?\s*''\)", r"old('campaign_id') or (log['campaign_id'] if log else '')", content)
    content = re.sub(r"old\('assignee',\s*log\['assignee'\]\s*\?\?\s*Constants\.USER_SYSTEM\)", r"old('assignee') or (log['assignee'] if log else Constants.USER_SYSTEM)", content)
    content = re.sub(r"log\['project'\]\s*\?\?\s*'Generic'", r"log['project'] or 'Generic'", content)
    content = re.sub(r"task\['ticket_id'\]\s*\?\?\s*''", r"task['ticket_id'] or ''", content)
    content = re.sub(r"log\['mt_jira_ticket'\]\s*\?\?\s*''", r"log['mt_jira_ticket'] or ''", content)

    # General regex for ?? inside {{ }} or {% %}
    def replace_coalesce(match):
        expr = match.group(0)
        # replace ?? with or
        expr = re.sub(r'\s*\?\?\s*', ' or ', expr)
        # replace ?: with or
        expr = re.sub(r'\s*\?:\s*', ' or ', expr)
        return expr

    content = re.sub(r'\{\{.*?\}\}', replace_coalesce, content, flags=re.DOTALL)
    content = re.sub(r'\{%.*?%\}', replace_coalesce, content, flags=re.DOTALL)

    if content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for f in glob.glob('app/templates/tasks/*.html'):
    clean_file(f)
