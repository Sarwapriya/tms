import os
import re

def convert_tasks_list():
    src = r'..\app\Views\tasks\list.php'
    dst = r'app\templates\tasks\list.html'

    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Strip top PHP block declaring getSortUrl etc (handled globally)
    content = re.sub(r'<\?php\s*use\s+App\\Models\\SubsidiariesModel;.*?function\s+getSortIcon\b.*?\}\s*\?>', '', content, flags=re.DOTALL)

    # 2. Template layout blocks
    content = re.sub(r'<\?=\s*\$this->extend\([\'"](.+?)[\'"]\)\s*\?>', r"{% extends '\1.html' %}", content)
    content = re.sub(r'<\?=\s*\$this->section\([\'"](.+?)[\'"]\)\s*\?>', r"{% block \1 %}", content)
    content = re.sub(r'<\?=\s*\$this->endSection\(\)\s*\?>', r"{% endblock %}", content)

    # 3. CodeIgniter CSRF & URLs
    content = re.sub(r'<\?=\s*csrf_field\(\)\s*\?>', r"{{ csrf_field() }}", content)
    content = re.sub(r'<\?=\s*site_url\((.*?)\)\s*\?>', r"{{ site_url(\1) }}", content)
    content = re.sub(r'<\?=\s*base_url\((.*?)\)\s*\?>', r"{{ base_url(\1) }}", content)
    content = re.sub(r'<\?=\s*json_encode\((.*?)\)\s*\?>', r"{{ \1 | tojson }}", content)
    content = re.sub(r'<\?=\s*esc\((.*?)\)\s*\?>', r"{{ \1 }}", content)
    content = re.sub(r'<\?=\s*htmlspecialchars\((.*?)\)\s*\?>', r"{{ \1 }}", content)

    # 4. Helper functions in echo
    content = re.sub(r'<\?=\s*getMeModeUrl\(\)\s*\?>', r"{{ getMeModeUrl() }}", content)
    content = re.sub(r'<\?=\s*getGroupFilterUrl\((.*?)\)\s*\?>', r"{{ getGroupFilterUrl(\1) }}", content)
    content = re.sub(r'<\?=\s*getSortUrl\((.*?)\)\s*\?>', r"{{ getSortUrl(\1) }}", content)
    content = re.sub(r'<\?=\s*getSortIcon\((.*?)\)\s*\?>', r"{{ getSortIcon(\1) }}", content)

    # 5. Top PHP block after content section
    top_logic_match = re.search(r'<\?php\s*use\s+App\\Models\\Constants;.*?\$isAdmin\s*=.*?;?\s*\?>', content, flags=re.DOTALL)
    if top_logic_match:
        jinja_top = """{% set pendingCount = (status_counts.get(1, 0)) + (status_counts.get(5, 0)) %}
{% set inProgressCount = (status_counts.get(2, 0)) + (status_counts.get(3, 0)) + (status_counts.get(4, 0)) %}
{% set blockedCount = status_counts.get(7, 0) %}
{% set completedCount = status_counts.get(6, 0) %}
{% set isMeMode = (request.args.get('me_mode') == '1') if 'me_mode' in request.args else (session.get('al_me_mode') == 1) %}
{% set isDWF = (Constants.USER_TEAMS.get(session.get('user_id')) == Constants.TEAM_DWF) %}
{% set totalLogs = pagination.total if pagination else logs|length %}"""
        content = content.replace(top_logic_match.group(0), jinja_top)

    # 6. Chatbot include at bottom
    chatbot_call = re.search(r'<\?=\s*view\([\'"]components/chatbot[\'"],\s*\[(.*?)\]\)\s*\?>', content, flags=re.DOTALL)
    if chatbot_call:
        jinja_chatbot = """{% with chatTitle='Task Assistant', chatEndpoint=site_url('tasks/ai-chat'), historyEndpoint=site_url('tasks/ai-history/'), conversationEndpoint=site_url('tasks/ai-conversation/') %}
{% include 'components/chatbot.html' %}
{% endwith %}"""
        content = content.replace(chatbot_call.group(0), jinja_chatbot)

    # 7. Pagination block
    old_pager = re.search(r'<\?php if \(isset\(\$pager\) && \$pager->getPageCount\(\) > 1\): \?>.*?<\?php endif; \?>', content, flags=re.DOTALL)
    if old_pager:
        jinja_pager = """{% if pagination and pagination.pages > 1 %}
    <div class="mt-4 d-flex justify-content-center">
        <nav aria-label="Page navigation" class="apple-pagination-container">
            <ul class="apple-pagination">
                {% if pagination.has_prev %}
                    <li><a href="{{ url_for_page(1) }}" aria-label="First">&laquo;</a></li>
                    <li><a href="{{ url_for_page(pagination.prev_num) }}" aria-label="Previous">&lsaquo;</a></li>
                {% endif %}
                {% for p in pagination.iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2) %}
                    {% if p %}
                        <li class="{% if p == pagination.page %}active{% endif %}">
                            <a href="{{ url_for_page(p) }}">{{ p }}</a>
                        </li>
                    {% else %}
                        <li class="disabled"><span>&hellip;</span></li>
                    {% endif %}
                {% endfor %}
                {% if pagination.has_next %}
                    <li><a href="{{ url_for_page(pagination.next_num) }}" aria-label="Next">&rsaquo;</a></li>
                    <li><a href="{{ url_for_page(pagination.pages) }}" aria-label="Last">&raquo;</a></li>
                {% endif %}
            </ul>
        </nav>
    </div>
{% endif %}"""
        content = content.replace(old_pager.group(0), jinja_pager)

    # 8. Constants mapping
    content = re.sub(r'\\?App\\Models\\Constants::', 'Constants.', content)
    content = re.sub(r'Constants::', 'Constants.', content)

    # 9. Control loops
    content = re.sub(r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\s*=>\s*\$([a-zA-Z0-9_]+)\)\s*:\s*\?>', 
                     r'{% for \2, \3 in \1 %}', content)
    content = re.sub(r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\)\s*:\s*\?>', 
                     r'{% for \2 in \1 %}', content)
    content = re.sub(r'<\?php\s*endforeach;?\s*\?>', r'{% endfor %}', content)

    content = re.sub(r'<\?php\s*if\s*\((.*?)\)\s*:\s*\?>', r'{% if \1 %}', content)
    content = re.sub(r'<\?php\s*elseif\s*\((.*?)\)\s*:\s*\?>', r'{% elif \1 %}', content)
    content = re.sub(r'<\?php\s*else\s*:\s*\?>', r'{% else %}', content)
    content = re.sub(r'<\?php\s*endif;?\s*\?>', r'{% endif %}', content)

    # 10. Table row PHP assignment block inside foreach:
    row_assignments = re.search(r'<\?php\s*foreach \(logs as log\):.*?<\?=\s*log\[[\'"]id[\'"]\]\s*\?>', content, flags=re.DOTALL)
    if row_assignments:
        old_block = row_assignments.group(0)
        # Convert the inner assignments to Jinja {% set ... %}
        converted_block = """{% for log in logs %}
        {% set subsidiary = Constants.ACTIVITY_LOG_SUBSIDIARIES.get(log['subsidiary_id'], 'Unknown') %}
        {% set status_str = Constants.ACTIVITY_LOGS_STATUS.get(log['status'], 'Unknown') %}
        {% set type_str = Constants.ACTIVITY_TYPES.get(log['type'], 'Unknown') %}
        {% set team = Constants.TEAMS.get(log['team_id'], 'Unknown') %}
        {% set project = log['project'] or 'Generic' %}
        {% set assignee = Constants.USERS.get(log['assignee'], Constants.USER_SYSTEM_LABEL) %}
        {% set size = Constants.ACTIVITY_SIZES.get(log['size'], 'Unknown') %}
        <tr>
            <td>{{ log['id'] }}</td>"""
        content = content.replace(old_block, converted_block)

    # 11. Replace <?= ... ?> expressions
    def replace_echo(match):
        expr = match.group(1).strip()
        if expr.endswith(';'):
            expr = expr[:-1].strip()
        ternary_match = re.match(r'^(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$', expr)
        if ternary_match:
            cond = ternary_match.group(1).strip()
            val_true = ternary_match.group(2).strip()
            val_false = ternary_match.group(3).strip()
            return f"{{{{ {val_true} if {cond} else {val_false} }}}}"
        return f"{{{{ {expr} }}}}"

    content = re.sub(r'<\?=\s*(.*?)\s*\?>', replace_echo, content)

    # 12. Clean up dollar signs inside Jinja tags
    def clean_jinja(m):
        txt = m.group(0)
        txt = re.sub(r'\$([a-zA-Z0-9_]+)', r'\1', txt)
        txt = txt.replace('empty(', 'not ').replace('!empty(', '')
        txt = txt.replace('&&', ' and ').replace('||', ' or ').replace('!', 'not ')
        return txt

    content = re.sub(r'(\{\{.*?\}\}|\{%.*?%\})', clean_jinja, content, flags=re.DOTALL)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)
    print("tasks/list.html generated successfully.")

if __name__ == '__main__':
    convert_tasks_list()
