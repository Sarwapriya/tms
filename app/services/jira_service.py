import os
import re
import json
import html
import uuid
import base64
import mimetypes
from datetime import datetime, timedelta
import requests
from flask import session, has_request_context, request

from config import Config
from app.models import db, JiraApiLog, ActivityLog, ActivityLogComment, User
from app.constants import Constants, JiraMapping


class JiraService:
    @staticmethod
    def log_api_call(task_id, request_type, endpoint, payload, resp=None, error=None):
        """Logs every Jira REST API request and response into mt_jira_api_log."""
        try:
            status_code = resp.status_code if resp is not None else 500
            resp_body = resp.text if resp is not None else None
            status = 'SUCCESS' if resp is not None and 200 <= resp.status_code < 300 else 'FAILED'
            
            payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload or '')
            err_msg = str(error) if error else (None if status == 'SUCCESS' else f"HTTP {status_code}")

            log = JiraApiLog(
                task_id=task_id,
                request_type=request_type,
                endpoint_url=str(endpoint)[:255],
                payload=payload_str,
                response_body=resp_body,
                status_code=status_code,
                error_message=str(err_msg)[:255] if err_msg else None,
                status=status
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception:
            db.session.rollback()
            return None

    @staticmethod
    def format_html_for_jira(html_content, extracted_images=None):
        """Converts HTML tags to Jira markup format and extracts embedded base64 images."""
        if not html_content:
            return ''

        text = html_content

        # Extract embedded base64 images if list provided
        if extracted_images is not None:
            def replace_img(match):
                ext = match.group(1).lower()
                if ext == 'jpeg':
                    ext = 'jpg'
                b64_data = match.group(2)
                try:
                    raw_data = base64.b64decode(b64_data)
                    filename = f"inline_{uuid.uuid4().hex[:8]}.{ext}"
                    temp_dir = os.path.join(Config.UPLOAD_DIR, 'temp')
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, filename)
                    with open(temp_path, 'wb') as f:
                        f.write(raw_data)
                    extracted_images.append({
                        'path': temp_path,
                        'name': filename
                    })
                    return f" !{filename}! "
                except Exception:
                    return ""

            text = re.sub(
                r'<img\s+[^>]*src=["\']data:image\/([^;]+);base64,([^"\']+)["\'][^>]*>',
                replace_img,
                text,
                flags=re.IGNORECASE
            )

        # Convert line breaks and paragraphs
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)

        # Convert list items to Jira bullets
        text = re.sub(r'<li>', '\n* ', text, flags=re.IGNORECASE)

        # Convert bold, italic, and underline
        text = re.sub(r'<(?:b|strong)[^>]*>(.*?)</(?:b|strong)>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<(?:i|em)[^>]*>(.*?)</(?:i|em)>', r'_\1_', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<u[^>]*>(.*?)</u>', r'+\1+', text, flags=re.IGNORECASE | re.DOTALL)

        # Strip remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities
        text = html.unescape(text)

        # Clean up excessive newlines
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)

        return text.strip()

    @staticmethod
    def get_auth_headers():
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'PostmanRuntime/7.32.3'
        }
        token = Config.MT_JIRA_AUTH_TOKEN
        if token:
            headers['Authorization'] = f"Bearer {token}"
        return headers

    @classmethod
    def create_issue(cls, task_id):
        """Creates an issue in Martech Jira from an ActivityLog task, mirroring TasksController.php::createJiraIssueFromTask."""
        task = ActivityLog.query.get(task_id)
        if not task:
            return {'success': False, 'message': 'Task not found'}

        jira_endpoint = Config.MT_JIRA_CREATE_ISSUE
        jira_token = Config.MT_JIRA_AUTH_TOKEN
        project_key = Config.MT_JIRA_PROJECT_KEY

        if not jira_endpoint or not jira_token:
            return {'success': False, 'message': 'Jira API endpoint or token is not configured.'}

        # Build labels
        jira_labels = [str(task.id)]
        act_type_name = Constants.ACTIVITY_TYPES.get(task.type, 'Task')
        jira_labels.append(act_type_name.replace(' ', '_'))

        if task.ticket_id:
            jira_labels.append(str(task.ticket_id).replace(' ', '_'))

        if task.labels:
            raw_labels = task.labels if isinstance(task.labels, list) else str(task.labels).split(',')
            for lbl in raw_labels:
                lbl_clean = lbl.strip().replace(' ', '_')
                if lbl_clean:
                    jira_labels.append(lbl_clean)

        # Base date & due date (10 days)
        base_date = task.start_date or task.created_at or datetime.utcnow()
        due_date = base_date + timedelta(days=10)

        extracted_images = []
        description_text = cls.format_html_for_jira(task.description or task.title, extracted_images)

        # Reporter & Assignee lookup
        creator = User.query.get(task.created_by) if task.created_by else None
        current_username = session.get('username') if has_request_context() else 'System'
        reporter_name = creator.username if creator and creator.username else current_username

        assignee_user = User.query.get(task.assignee) if task.assignee else None
        assignee_name = assignee_user.username if assignee_user and assignee_user.username else current_username

        payload_fields = {
            'project': {'key': project_key},
            'issuetype': {'name': 'Task'},
            'summary': task.title,
            'components': [{'name': Constants.TEAMS.get(task.team_id, 'Media Tagging')}],
            'description': description_text,
            'customfield_24905': task.project or '',
            'customfield_12014': Constants.ACTIVITY_LOG_SUBSIDIARIES.get(task.subsidiary_id, 'SGE'),
            'priority': {'name': JiraMapping.PRIORITIES.get(task.priority, JiraMapping.PRIORITY_MINOR)},
            'labels': jira_labels,
            'duedate': due_date.strftime('%Y-%m-%d'),
            'timetracking': {
                'originalEstimate': JiraMapping.ESTIMATES.get(task.size, '1h')
            }
        }
        if reporter_name:
            payload_fields['reporter'] = {'name': reporter_name}
        if assignee_name:
            payload_fields['assignee'] = {'name': assignee_name}

        payload = {'fields': payload_fields}
        headers = cls.get_auth_headers()
        headers['Content-Type'] = 'application/json'

        try:
            resp = requests.post(jira_endpoint, json=payload, headers=headers, timeout=30)
            cls.log_api_call(task_id, 'CREATE_ISSUE', jira_endpoint, payload, resp=resp)

            if 200 <= resp.status_code < 300:
                resp_json = resp.json()
                ticket_id = resp_json.get('key')

                if ticket_id:
                    old_ticket = task.mt_jira_ticket or 'None'
                    task.mt_jira_ticket = ticket_id

                    # Upload inline images if any were extracted
                    if extracted_images:
                        for img in extracted_images:
                            cls.upload_attachment(task_id, ticket_id, img['path'], img['name'])
                            try:
                                os.unlink(img['path'])
                            except Exception:
                                pass

                    # Add system update comment
                    user_id = session.get('user_id', Constants.USER_SYSTEM) if has_request_context() else Constants.USER_SYSTEM
                    update_comment = ActivityLogComment(
                        log_id=task_id,
                        comment=f"MT JIRA Ticket updated from [{old_ticket}] to [{ticket_id}] via API creation",
                        commented_by=user_id,
                        type=Constants.COMMENT_TYPE_UPDATE,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(update_comment)
                    db.session.commit()

                    # Send reference link as a Jira comment
                    ref_url = request.host_url.rstrip('/') + f"/tasks/view/{task_id}" if has_request_context() else f"/tasks/view/{task_id}"
                    cls.add_comment(task_id, ticket_id, f"Reference: {ref_url}")

                    # Transition status in Jira if task status is beyond To Do
                    current_status = task.status
                    mapped_jira_status = JiraMapping.STATUS_MAPPING.get(current_status)
                    if mapped_jira_status and mapped_jira_status != JiraMapping.JIRA_STATUS_TODO:
                        cls.update_status(task_id, Constants.ACTIVITY_LOGS_STATUS_TO_DO, current_status)

                    return {'success': True, 'ticket_id': ticket_id, 'message': 'MT JIRA Ticket created successfully.'}

            return {'success': False, 'message': f"Failed with status code {resp.status_code}: {resp.text}"}

        except Exception as e:
            cls.log_api_call(task_id, 'CREATE_ISSUE', jira_endpoint, payload, error=str(e))
            return {'success': False, 'message': str(e)}

    @classmethod
    def edit_issue(cls, task_id):
        """Updates an existing issue in Martech Jira, mirroring TasksController.php::updateJiraIssueFromTask."""
        task = ActivityLog.query.get(task_id)
        if not task or not task.mt_jira_ticket:
            return False

        jira_endpoint = Config.MT_JIRA_EDIT_ISSUE
        if not jira_endpoint:
            return False

        endpoint = jira_endpoint.replace('{key}', task.mt_jira_ticket).replace('{id}', task.mt_jira_ticket)
        if '{key}' not in jira_endpoint and '{id}' not in jira_endpoint:
            endpoint = jira_endpoint.rstrip('/') + '/' + task.mt_jira_ticket

        jira_labels = [str(task.id)]
        act_type_name = Constants.ACTIVITY_TYPES.get(task.type, 'Task')
        jira_labels.append(act_type_name.replace(' ', '_'))

        if task.ticket_id:
            jira_labels.append(str(task.ticket_id).replace(' ', '_'))

        if task.labels:
            raw_labels = task.labels if isinstance(task.labels, list) else str(task.labels).split(',')
            for lbl in raw_labels:
                lbl_clean = lbl.strip().replace(' ', '_')
                if lbl_clean:
                    jira_labels.append(lbl_clean)

        base_date = task.start_date or task.created_at or datetime.utcnow()
        due_date = base_date + timedelta(days=7)

        extracted_images = []
        description_text = cls.format_html_for_jira(task.description or task.title, extracted_images)

        assignee_user = User.query.get(task.assignee) if task.assignee else None
        current_username = session.get('username') if has_request_context() else 'System'
        assignee_name = assignee_user.username if assignee_user and assignee_user.username else current_username

        payload_fields = {
            'summary': task.title,
            'components': [{'name': Constants.TEAMS.get(task.team_id, 'Media Tagging')}],
            'description': description_text,
            'customfield_24905': task.project or '',
            'customfield_12014': Constants.ACTIVITY_LOG_SUBSIDIARIES.get(task.subsidiary_id, 'SGE'),
            'priority': {'name': JiraMapping.PRIORITIES.get(task.priority, JiraMapping.PRIORITY_MINOR)},
            'labels': jira_labels,
            'duedate': due_date.strftime('%Y-%m-%d'),
            'timetracking': {
                'originalEstimate': JiraMapping.ESTIMATES.get(task.size, '1h')
            }
        }
        if assignee_name:
            payload_fields['assignee'] = {'name': assignee_name}

        payload = {'fields': payload_fields}
        headers = cls.get_auth_headers()
        headers['Content-Type'] = 'application/json'

        try:
            resp = requests.put(endpoint, json=payload, headers=headers, timeout=30)
            cls.log_api_call(task_id, 'EDIT_ISSUE', endpoint, payload, resp=resp)

            if 200 <= resp.status_code < 300:
                if extracted_images:
                    for img in extracted_images:
                        cls.upload_attachment(task_id, task.mt_jira_ticket, img['path'], img['name'])
                        try:
                            os.unlink(img['path'])
                        except Exception:
                            pass
                return True
            return False
        except Exception as e:
            cls.log_api_call(task_id, 'EDIT_ISSUE', endpoint, payload, error=str(e))
            return False

    @classmethod
    def update_status(cls, task_id, old_internal_status, new_internal_status):
        """Transitions the Jira issue status, mirroring TasksController.php::updateJiraStatusFromTask."""
        task = ActivityLog.query.get(task_id)
        if not task or not task.mt_jira_ticket:
            return False

        old_jira_status = JiraMapping.STATUS_MAPPING.get(int(old_internal_status))
        new_jira_status = JiraMapping.STATUS_MAPPING.get(int(new_internal_status))

        if not old_jira_status or not new_jira_status or old_jira_status == new_jira_status:
            return False

        transition_id = JiraMapping.TRANSITIONS.get(old_jira_status, {}).get(new_jira_status)
        if not transition_id:
            return False

        jira_endpoint = Config.MT_JIRA_UPDATE_STATUS
        if not jira_endpoint:
            return False

        endpoint = jira_endpoint.replace('{key}', task.mt_jira_ticket).replace('{id}', task.mt_jira_ticket)
        if '{key}' not in jira_endpoint and '{id}' not in jira_endpoint:
            endpoint = jira_endpoint.rstrip('/') + '/' + task.mt_jira_ticket + '/transitions'

        payload = {
            'transition': {
                'id': transition_id
            }
        }
        headers = cls.get_auth_headers()
        headers['Content-Type'] = 'application/json'

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            cls.log_api_call(task_id, 'UPDATE_STATUS', endpoint, payload, resp=resp)
            return 200 <= resp.status_code < 300
        except Exception as e:
            cls.log_api_call(task_id, 'UPDATE_STATUS', endpoint, payload, error=str(e))
            return False

    @classmethod
    def add_comment(cls, task_id, ticket_id, comment_text):
        """Adds a comment to the Jira ticket, mirroring TasksController.php::addCommentToJira."""
        jira_endpoint = Config.MT_JIRA_ADD_COMMENT
        if not jira_endpoint:
            return False

        endpoint = jira_endpoint.replace('{key}', ticket_id).replace('{id}', ticket_id)
        if '{key}' not in jira_endpoint and '{id}' not in jira_endpoint:
            endpoint = jira_endpoint.rstrip('/') + '/' + ticket_id + '/comment'

        payload = {'body': comment_text}
        headers = cls.get_auth_headers()
        headers['Content-Type'] = 'application/json'

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            cls.log_api_call(task_id, 'ADD_COMMENT', endpoint, payload, resp=resp)
            return 200 <= resp.status_code < 300
        except Exception as e:
            cls.log_api_call(task_id, 'ADD_COMMENT', endpoint, payload, error=str(e))
            return False

    @classmethod
    def update_comment(cls, task_id, ticket_id, comment_id, comment_text):
        """Updates a Jira comment, mirroring TasksController.php::updateCommentToJira."""
        jira_endpoint = Config.MT_JIRA_UPDATE_COMMENT
        if not jira_endpoint:
            return False

        endpoint = jira_endpoint.replace('{key}', ticket_id).replace('{id}', ticket_id)
        if '{commentId}' in endpoint:
            endpoint = endpoint.replace('{commentId}', str(comment_id))
        else:
            endpoint = endpoint.rstrip('/') + '/' + str(comment_id)

        payload = {'body': comment_text}
        headers = cls.get_auth_headers()
        headers['Content-Type'] = 'application/json'

        try:
            resp = requests.put(endpoint, json=payload, headers=headers, timeout=30)
            cls.log_api_call(task_id, 'UPDATE_COMMENT', endpoint, payload, resp=resp)
            return 200 <= resp.status_code < 300
        except Exception as e:
            cls.log_api_call(task_id, 'UPDATE_COMMENT', endpoint, payload, error=str(e))
            return False

    @classmethod
    def upload_attachment(cls, task_id, ticket_id, file_path, file_name):
        """Uploads an attachment to the Jira ticket, mirroring TasksController.php::uploadAttachmentToJira."""
        jira_endpoint = Config.MT_JIRA_UPLOAD_ATTACHMENT
        if not jira_endpoint or not os.path.isfile(file_path):
            return False

        endpoint = jira_endpoint.replace('{key}', ticket_id).replace('{id}', ticket_id)
        if '{key}' not in jira_endpoint and '{id}' not in jira_endpoint:
            endpoint = jira_endpoint.rstrip('/') + '/' + ticket_id + '/attachments'

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or 'application/octet-stream'

        headers = cls.get_auth_headers()
        headers['X-Atlassian-Token'] = 'no-check'
        # Do not manually set Content-Type header when passing files to requests; requests will set multipart boundary automatically.

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f, mime_type)}
                resp = requests.post(endpoint, files=files, headers=headers, timeout=60)

            cls.log_api_call(
                task_id,
                'UPLOAD_ATTACHMENT',
                endpoint,
                {'type': 'multipart/form-data', 'file_path': file_path, 'file_name': file_name},
                resp=resp
            )
            return 200 <= resp.status_code < 300
        except Exception as e:
            cls.log_api_call(task_id, 'UPLOAD_ATTACHMENT', endpoint, f"File upload: {file_name}", error=str(e))
            return False

    @classmethod
    def retry_log(cls, log_id, custom_endpoint=None, custom_payload=None):
        """Retries a failed JIRA API request from mt_jira_api_log, matching SettingsController.php::retryApiLog."""
        log = JiraApiLog.query.get(log_id)
        if not log:
            return {'success': False, 'message': 'Log entry not found'}

        jira_token = Config.MT_JIRA_AUTH_TOKEN or os.getenv('MT_JIRA_AUTH_TOKEN', '')
        if not jira_token:
            return {'success': False, 'message': 'JIRA Auth Token is not configured.'}

        endpoint = custom_endpoint if (custom_endpoint and str(custom_endpoint).strip()) else log.endpoint_url
        if not endpoint:
            return {'success': False, 'message': 'Endpoint URL is not defined for this log entry.'}

        raw_payload = custom_payload if custom_payload is not None else log.payload
        req_type = (log.request_type or '').upper()

        headers = {
            'Authorization': f'Bearer {jira_token}',
            'Accept': 'application/json',
            'User-Agent': 'PostmanRuntime/7.32.3'
        }

        # Determine HTTP method
        http_method = 'PUT' if req_type in ('EDIT_ISSUE', 'UPDATE_COMMENT') else 'POST'

        status = 'FAILED'
        status_code = None
        resp_body = ''
        err_msg = ''

        try:
            if req_type == 'UPLOAD_ATTACHMENT':
                # Reconstruct multipart/form-data for attachments
                payload_data = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                if isinstance(payload_data, dict) and 'file_path' in payload_data:
                    file_path = payload_data.get('file_path')
                    file_name = payload_data.get('file_name', os.path.basename(file_path))
                    if not os.path.isfile(file_path):
                        return {'success': False, 'message': 'File no longer exists for retry.'}

                    mime_type, _ = mimetypes.guess_type(file_path)
                    mime_type = mime_type or 'application/octet-stream'
                    headers['X-Atlassian-Token'] = 'no-check'

                    with open(file_path, 'rb') as f:
                        files = {'file': (file_name, f, mime_type)}
                        resp = requests.post(endpoint, files=files, headers=headers, timeout=60)
                else:
                    return {'success': False, 'message': 'Invalid payload format for attachment retry.'}
            else:
                headers['Content-Type'] = 'application/json'
                if isinstance(raw_payload, str):
                    try:
                        json_payload = json.loads(raw_payload)
                        payload_str = json.dumps(json_payload)
                    except Exception:
                        payload_str = raw_payload
                elif isinstance(raw_payload, dict):
                    payload_str = json.dumps(raw_payload)
                else:
                    payload_str = str(raw_payload or '')

                resp = requests.request(http_method, endpoint, data=payload_str, headers=headers, timeout=30)

            status_code = resp.status_code
            resp_body = resp.text
            status = 'SUCCESS' if (200 <= status_code < 300) else 'FAILED'
            if status != 'SUCCESS':
                err_msg = f"HTTP {status_code}: {resp_body[:200]}"

        except Exception as e:
            status_code = 500
            status = 'FAILED'
            err_msg = str(e)
            resp_body = ''

        # Update log entry
        log.endpoint_url = endpoint
        if req_type != 'UPLOAD_ATTACHMENT' and raw_payload is not None:
            log.payload = raw_payload if isinstance(raw_payload, str) else json.dumps(raw_payload)
        log.status = status
        log.status_code = status_code
        log.response_body = resp_body
        log.error_message = err_msg or None
        log.retry_count = (log.retry_count or 0) + 1

        # If CREATE_ISSUE succeeded and task_id exists, link mt_jira_ticket
        if status == 'SUCCESS' and req_type == 'CREATE_ISSUE' and log.task_id:
            try:
                decoded = json.loads(resp_body)
                if isinstance(decoded, dict) and decoded.get('key'):
                    task = ActivityLog.query.get(log.task_id)
                    if task:
                        task.mt_jira_ticket = decoded['key']
            except Exception:
                pass

        db.session.commit()

        if status == 'SUCCESS':
            return {'success': True, 'message': 'Request retried successfully.'}
        else:
            return {'success': False, 'message': f"Request failed with status {status_code}" if status_code else f"Exception: {err_msg}"}

