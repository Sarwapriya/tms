def fix_reports():
    for fname in ['app/templates/reports/index.html', 'app/templates/reports/pdf.html']:
        with open(fname, 'r', encoding='utf-8') as f:
            txt = f.read()

        # 1. completed_tasks
        # Find where completed_tasks table body is
        idx_comp = txt.find("empty(completed_tasks)")
        if idx_comp != -1:
            idx_else = txt.find("{% else %}", idx_comp)
            idx_tr = txt.find("<tr>", idx_else)
            snippet = txt[idx_else:idx_tr]
            rep = "{% else %}\n                            {% for task in completed_tasks %}\n                                {% set subLabel = Constants.ACTIVITY_LOG_SUBSIDIARIES.get(task['subsidiary_id'], 'Unknown') %}\n                                {% set prioLabel = Constants.PRIORITIES.get(task['priority'], 'Unknown') %}\n                                {% set assigneeLabel = Constants.USERS.get(task['assignee'], Constants.USER_SYSTEM_LABEL) %}\n                                {% set lastComment = task.get('last_comment') or '' %}\n"
            txt = txt[:idx_else] + rep + txt[idx_tr:]

        # 2. new_requests
        idx_req = txt.find("empty(new_requests)")
        if idx_req != -1:
            idx_else = txt.find("{% else %}", idx_req)
            idx_tr = txt.find("<tr>", idx_else)
            snippet = txt[idx_else:idx_tr]
            rep = "{% else %}\n                            {% for req in new_requests %}\n                                {% set reqType = Constants.JIRA_TICKET_TYPES.get(req['type'], 'Unknown') %}\n                                {% set statusLabel = Constants.STATUS_REQUESTS.get(req['status'], 'Unknown') %}\n                                {% set ticket = req['new_rule_ticket'] if req['type'] == Constants.JIRA_TYPE_NEW_RULE else req['new_tag_ticket'] %}\n"
            txt = txt[:idx_else] + rep + txt[idx_tr:]

        # 3. ongoing_tasks
        idx_ong = txt.find("empty(ongoing_tasks)")
        if idx_ong != -1:
            idx_else = txt.find("{% else %}", idx_ong)
            idx_tr = txt.find("<tr>", idx_else)
            snippet = txt[idx_else:idx_tr]
            rep = "{% else %}\n                            {% for task in ongoing_tasks %}\n                                {% set subLabel = Constants.ACTIVITY_LOG_SUBSIDIARIES.get(task['subsidiary_id'], 'Unknown') %}\n                                {% set prioLabel = Constants.PRIORITIES.get(task['priority'], 'Unknown') %}\n                                {% set assigneeLabel = Constants.USERS.get(task['assignee'], Constants.USER_SYSTEM_LABEL) %}\n                                {% set statusLabel = Constants.ACTIVITY_LOG_STATUS.get(task['status'], 'Unknown') %}\n"
            txt = txt[:idx_else] + rep + txt[idx_tr:]

        # 4. new_tags
        idx_nt = txt.find("empty(new_tags)")
        if idx_nt != -1:
            idx_else = txt.find("{% else %}", idx_nt)
            idx_div_or_tr = min([pos for pos in [txt.find("<div class=\"tag-row-item", idx_else), txt.find("<tr", idx_else)] if pos != -1])
            snippet = txt[idx_else:idx_div_or_tr]
            rep = "{% else %}\n                                    {% for tag in new_tags %}\n                                        {% set sub = Constants.SUBSIDIARIES.get(tag.get('subsidiary_id'), 'Unknown') %}\n                                        {% set statusLabel = Constants.STATUS.get(tag['status'], 'Unknown') %}\n"
            txt = txt[:idx_else] + rep + txt[idx_div_or_tr:]

        # 5. updated_tags
        idx_ut = txt.find("empty(updated_tags)")
        if idx_ut != -1:
            idx_else = txt.find("{% else %}", idx_ut)
            idx_div_or_tr = min([pos for pos in [txt.find("<div class=\"tag-row-item", idx_else), txt.find("<tr", idx_else)] if pos != -1])
            snippet = txt[idx_else:idx_div_or_tr]
            rep = "{% else %}\n                                    {% for tag in updated_tags %}\n                                        {% set sub = Constants.SUBSIDIARIES.get(tag.get('subsidiary_id'), 'Unknown') %}\n                                        {% set statusLabel = Constants.STATUS.get(tag['status'], 'Unknown') %}\n"
            txt = txt[:idx_else] + rep + txt[idx_div_or_tr:]

        with open(fname, 'w', encoding='utf-8') as f:
            f.write(txt)
        print(f"Fixed {fname}")

if __name__ == '__main__':
    fix_reports()
