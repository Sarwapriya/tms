import os
import re

def clean_common_php(content):
    # Strip top helper and namespace lines
    content = re.sub(r'<\?php\s*use\s+App\\Models\\[a-zA-Z0-9_]+;\s*\?>', '', content)
    content = re.sub(r'<\?php\s*helper\([^)]+\);\s*\?>', '', content)
    content = re.sub(r'use\s+App\\Models\\[a-zA-Z0-9_]+;\s*', '', content)
    content = re.sub(r'helper\([\'"][^\'"]+[\'"]\);\s*', '', content)

    # Template blocks
    content = re.sub(r'<\?=\s*\$this->extend\([\'"](.+?)[\'"]\)\s*\?>', r"{% extends '\1.html' %}", content)
    content = re.sub(r'<\?=\s*\$this->section\([\'"](.+?)[\'"]\)\s*\?>', r"{% block \1 %}", content)
    content = re.sub(r'<\?=\s*\$this->endSection\(\)\s*\?>', r"{% endblock %}", content)
    content = re.sub(r'<\?=\s*\$this->include\([\'"](.+?)[\'"]\)\s*\?>', r"{% include '\1.html' %}", content)

    # CSRF & URLs
    content = re.sub(r'<\?=\s*csrf_field\(\)\s*\?>', r"{{ csrf_field() }}", content)
    content = re.sub(r'<\?=\s*site_url\((.*?)\)\s*\?>', r"{{ site_url(\1) }}", content)
    content = re.sub(r'<\?=\s*base_url\((.*?)\)\s*\?>', r"{{ base_url(\1) }}", content)
    content = re.sub(r'<\?=\s*json_encode\((.*?)\)\s*\?>', r"{{ \1 | tojson }}", content)
    content = re.sub(r'<\?=\s*esc\((.*?)\)\s*\?>', r"{{ \1 }}", content)
    content = re.sub(r'<\?=\s*htmlspecialchars\((.*?)\)\s*\?>', r"{{ \1 }}", content)
    content = re.sub(r'<\?=\s*old\((.*?)\)\s*\?>', r"{{ old(\1) }}", content)

    # Constants
    content = re.sub(r'\\?App\\Models\\Constants::', 'Constants.', content)
    content = re.sub(r'Constants::', 'Constants.', content)

    # Helper echo calls
    content = re.sub(r'<\?=\s*getMeModeUrl\(\)\s*\?>', r"{{ getMeModeUrl() }}", content)
    content = re.sub(r'<\?=\s*getGroupFilterUrl\((.*?)\)\s*\?>', r"{{ getGroupFilterUrl(\1) }}", content)
    content = re.sub(r'<\?=\s*getSortUrl\((.*?)\)\s*\?>', r"{{ getSortUrl(\1) }}", content)
    content = re.sub(r'<\?=\s*getSortIcon\((.*?)\)\s*\?>', r"{{ getSortIcon(\1) }}", content)

    # Control flow
    content = re.sub(r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\s*=>\s*\$([a-zA-Z0-9_]+)\)\s*:\s*\?>', 
                     r'{% for \2, \3 in \1 %}', content)
    content = re.sub(r'<\?php\s*foreach\s*\((.*?)\s+as\s+\$([a-zA-Z0-9_]+)\)\s*:\s*\?>', 
                     r'{% for \2 in \1 %}', content)
    content = re.sub(r'<\?php\s*endforeach;?\s*\?>', r'{% endfor %}', content)

    content = re.sub(r'<\?php\s*if\s*\((.*?)\)\s*:\s*\?>', r'{% if \1 %}', content)
    content = re.sub(r'<\?php\s*elseif\s*\((.*?)\)\s*:\s*\?>', r'{% elif \1 %}', content)
    content = re.sub(r'<\?php\s*else\s*:\s*\?>', r'{% else %}', content)
    content = re.sub(r'<\?php\s*endif;?\s*\?>', r'{% endif %}', content)

    # Echo <?= ... ?>
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

    # Clean up variables inside {{ }} and {% %}
    def clean_tags(m):
        txt = m.group(0)
        txt = re.sub(r'\$([a-zA-Z0-9_]+)', r'\1', txt)
        txt = re.sub(r'!empty\((.*?)\)', r'\1', txt)
        txt = re.sub(r'empty\((.*?)\)', r'not \1', txt)
        txt = re.sub(r'isset\((.*?)\)', r'\1 is defined', txt)
        txt = txt.replace('&&', ' and ').replace('||', ' or ').replace('!', 'not ')
        return txt

    content = re.sub(r'(\{\{.*?\}\}|\{%.*?%\})', clean_tags, content, flags=re.DOTALL)
    return content

def convert_file(src_rel, dst_rel, custom_fn=None):
    src = os.path.join(r'..\app\Views', src_rel)
    dst = os.path.join(r'app\templates', dst_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    if custom_fn:
        content = custom_fn(content)

    content = clean_common_php(content)

    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Converted {src_rel} -> {dst_rel}")

# Custom transformer for tasks/list.php
def custom_tasks_list(content):
    content = re.sub(r'<\?php\s*use\s+App\\Models\\SubsidiariesModel;.*?function\s+getSortIcon\b.*?\}\s*\?>', '', content, flags=re.DOTALL)
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

    chatbot_call = re.search(r'<\?=\s*view\([\'"]components/chatbot[\'"],\s*\[(.*?)\]\)\s*\?>', content, flags=re.DOTALL)
    if chatbot_call:
        jinja_chatbot = """{% with chatTitle='Task Assistant', chatEndpoint=site_url('tasks/ai-chat'), historyEndpoint=site_url('tasks/ai-history/'), conversationEndpoint=site_url('tasks/ai-conversation/') %}
{% include 'components/chatbot.html' %}
{% endwith %}"""
        content = content.replace(chatbot_call.group(0), jinja_chatbot)

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

    # Active filters pills loop in list.php
    pills_php = re.search(r'<\?php if \(\$activeFiltersCount > 0\): \?>.*?<\?php endif; \?>\s*<!-- #endregion -->', content, flags=re.DOTALL)
    if pills_php:
        jinja_pills = """{% if active_pills %}
        <div class="d-flex flex-wrap gap-2 mb-3 align-items-center">
            <span class="text-secondary small fw-medium">Active Filters:</span>
            {% for pill in active_pills %}
                <a href="{{ pill.clear_url }}"
                    class="badge bg-secondary text-decoration-none d-inline-flex align-items-center gap-1.5 py-1.5 px-2.5 rounded-pill border border-secondary"
                    style="font-size: 0.8rem; font-weight: 500;">
                    <span>{{ pill.label }}</span>
                    <i class="bi bi-x-circle-fill text-muted" style="font-size: 0.75rem;"></i>
                </a>
            {% endfor %}
        </div>
    {% endif %}
    <!-- #endregion -->"""
        content = content.replace(pills_php.group(0), jinja_pills)

    # Clean up commented php lines
    content = re.sub(r'<\?php\s*//.*?\?>', '', content)
    return content

# Custom transformer for tasks/view.php
def custom_tasks_view(content):
    top_php = re.search(r'<\?php\s*use\s+App\\Models\\Constants;.*?\$hideAssigneeSystemWide\s*=.*?;?\s*\?>', content, flags=re.DOTALL)
    if top_php:
        jinja_top = """{% set subsidiary = Constants.ACTIVITY_LOG_SUBSIDIARIES.get(task.subsidiary_id, 'Unknown') %}
{% set status_str = Constants.ACTIVITY_LOGS_STATUS.get(task.status, 'Unknown') %}
{% set type_str = Constants.ACTIVITY_TYPES.get(task.type, 'Unknown') %}
{% set team = Constants.TEAMS.get(task.team_id, 'Unknown') %}
{% set project = task.project or 'Generic' %}
{% set assignee = Constants.USERS.get(task.assignee, Constants.USER_SYSTEM_LABEL) %}
{% set size = Constants.ACTIVITY_SIZES.get(task.size, 'Unknown') %}
{% set priority = Constants.PRIORITIES.get(task.priority, 'Unknown') %}
{% set showRelatedTags = ((task.type == Constants.ACTIVITY_TYPE_RENEWAL or task.type == Constants.ACTIVITY_TYPE_REQUEST) and task.team_id == Constants.TEAM_MEDIA_TAGGING) %}
{% set hideAssigneeSystemWide = false %}"""
        content = content.replace(top_php.group(0), jinja_top)

    # In view.php, $log is used for the task
    content = content.replace('$log', '$task')
    content = content.replace('log.', 'task.').replace("log['", "task['").replace('log["', 'task["')

    return content

# Custom transformer for tasks/project_spreadsheet.php
def custom_tasks_spreadsheet(content):
    top_php = re.search(r'<\?php\s*use\s+App\\Models\\Constants;.*?\};\s*\?>', content, flags=re.DOTALL)
    if top_php:
        jinja_top = """{% set hideAssigneeSystemWide = false %}
{% set isMeMode = (request.args.get('me_mode') == '1') %}"""
        content = content.replace(top_php.group(0), jinja_top)

    content = content.replace('$log', '$task')
    return content

if __name__ == '__main__':
    convert_file('tasks/list.php', 'tasks/list.html', custom_tasks_list)
    convert_file('tasks/view.php', 'tasks/view.html', custom_tasks_view)
    convert_file('tasks/project_spreadsheet.php', 'tasks/project_spreadsheet.html', custom_tasks_spreadsheet)
    convert_file('tasks/create.php', 'tasks/create.html')
    convert_file('tasks/update.php', 'tasks/update.html')
