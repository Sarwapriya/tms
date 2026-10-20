import os
import re

def convert_php_to_jinja(content):
    # Basic structural replacements
    content = re.sub(r'<\?=\s*\$this->extend\([\'"](.+?)[\'"]\)\s*\?>', r"{% extends '\1.html' %}", content)
    content = re.sub(r'<\?=\s*\$this->section\([\'"](.+?)[\'"]\)\s*\?>', r"{% block \1 %}", content)
    content = re.sub(r'<\?=\s*\$this->endSection\(\)\s*\?>', r"{% endblock %}", content)
    content = re.sub(r'<\?=\s*\$this->include\([\'"](.+?)[\'"]\)\s*\?>', r"{% include '\1.html' %}", content)

    # Convert echo helpers
    content = re.sub(r'<\?=\s*site_url\((.*?)\)\s*\?>', r"{{ site_url(\1) }}", content)
    content = re.sub(r'<\?=\s*base_url\((.*?)\)\s*\?>', r"{{ base_url(\1) }}", content)
    content = re.sub(r'<\?=\s*esc\((.*?)\)\s*\?>', r"{{ \1 }}", content)
    content = re.sub(r'<\?=\s*json_encode\((.*?)\)\s*\?>', r"{{ \1 | tojson }}", content)

    # csrf_field
    content = re.sub(r'<\?=\s*csrf_field\(\)\s*\?>', r"{{ csrf_field() }}", content)

    return content

if __name__ == '__main__':
    src = r'..\app\Views\components\chatbot.php'
    dst = r'app\templates\components\chatbot.html'
    with open(src, 'r', encoding='utf-8') as f:
        c = f.read()

    # Chatbot specific header conversion
    c = re.sub(r'<\?php\s*\$chatTitle\s*=\s*\$chatTitle\s*\?\?\s*[\'"]Script Assistant[\'"];.*?\?>', 
               r"""{% set chatTitle = chatTitle|default('Script Assistant') %}
{% set chatEndpoint = chatEndpoint|default(site_url('tags/ai-chat')) %}
{% set historyEndpoint = historyEndpoint|default(site_url('tags/ai-history/')) %}
{% set conversationEndpoint = conversationEndpoint|default(site_url('tags/ai-conversation/')) %}
{% set contextId = contextId|default(0) %}
{% set user = session.get('user_name', 'User') %}
{% set aiModels = aiModels|default([]) %}
{% set chatWelcomeMessage = chatWelcomeMessage|default('Hello ' ~ session.get('user_name', 'User') ~ '! How can I help you today? 😊') %}""", 
               c, flags=re.DOTALL)

    # Models options loop
    old_models = re.search(r'<\?php if \(!empty\(\$aiModels\)\): \?>.*?<\?php endif; \?>', c, flags=re.DOTALL)
    if old_models:
        jinja_models = """{% if aiModels %}
                        {% for model in aiModels %}
                            <option value="{{ model.modelId or model.id }}" data-description="{{ model.description or '' }}">{{ model.name or 'Model' }}</option>
                        {% endfor %}
                    {% else %}
                        <option value="">No models available</option>
                    {% endif %}"""
        c = c.replace(old_models.group(0), jinja_models)

    c = convert_php_to_jinja(c)
    c = c.replace('<?= $chatEndpoint ?>', '{{ chatEndpoint }}')
    c = c.replace('<?= $historyEndpoint ?>', '{{ historyEndpoint }}')
    c = c.replace('<?= $conversationEndpoint ?>', '{{ conversationEndpoint }}')
    c = c.replace('<?= $chatWelcomeMessage ?>', '{{ chatWelcomeMessage }}')
    c = c.replace('<?= $contextId ?>', '{{ contextId }}')
    c = c.replace('<?= $user ?>', '{{ user }}')
    c = c.replace('<?= $chatTitle ?>', '{{ chatTitle }}')

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(c)
    print("chatbot.html created successfully.")
