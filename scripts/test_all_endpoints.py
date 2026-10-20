import os
import sys
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.models import db, User, Tag, Property, Vendor, JiraHistory, ActivityLog, TagRequest

app = create_app()
app.config['TESTING'] = True


def run_tests():
    with app.test_client() as client:
        # Simulate login session
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'admin'
            sess['user_name'] = 'System Administrator'
            sess['account_type'] = 1
            sess['user_role'] = 3
            sess['user_role_name'] = 'Administrator'
            sess['is_logged_in'] = True
            sess['permissions'] = {
                'dashboard': True,
                'tags': True,
                'tag-requests': True,
                'properties': True,
                'vendors': True,
                'jira': True,
                'tasks': True,
                'reports': True,
                'settings': True
            }

        routes_to_test = [
            # Dashboard
            ('/dashboard/', 'Dashboard Index'),

            # Tasks
            ('/tasks/', 'Tasks List'),
            ('/tasks/create', 'Tasks Create'),
            ('/tasks/project-spreadsheet', 'Tasks Spreadsheet'),

            # Tags
            ('/tags/', 'Tags List'),
            ('/tags/repository', 'Tags Repository'),
            ('/tags/create', 'Tags Create'),
            ('/tags/renew', 'Tags Renew'),
            ('/tags/renewal-justifications', 'Tags Renewal Justifications'),
            ('/tags/update-rule-request', 'Tags Update Rule Request'),
            ('/tags/upload-renewal-justifications', 'Tags Upload Renewal Justifications'),

            # Tag Requests
            ('/tag-requests/', 'Tag Requests List'),
            ('/tag-requests/create', 'Tag Requests Create'),
            ('/tag-requests/create-from-excel', 'Tag Requests Create From Excel'),
            ('/tag-requests/upload-excel', 'Tag Requests Upload Excel'),
            ('/tag-requests/capture-tags', 'Tag Requests Capture Tags'),
            ('/tag-requests/shop-manual-input', 'Tag Requests Shop Manual Input'),

            # Properties
            ('/properties/', 'Properties List'),
            ('/properties/create', 'Properties Create'),

            # Vendors
            ('/vendors/', 'Vendors List'),

            # Jira
            ('/jira/', 'Jira List'),
            ('/jira/create', 'Jira Create'),
            ('/jira/add-entry', 'Jira Add Entry'),

            # Reports
            ('/reports/', 'Reports Index'),
            ('/reports/pdf', 'Reports PDF View'),

            # Settings
            ('/settings/', 'Settings Index'),

            # Profile
            ('/profile/', 'Profile Index'),
        ]

        with app.app_context():
            # Add dynamic ID routes if records exist
            first_tag = Tag.query.first()
            if first_tag:
                routes_to_test.append((f'/tags/view/{first_tag.id}', f'Tag View #{first_tag.id}'))
                routes_to_test.append((f'/tags/update/{first_tag.id}', f'Tag Update #{first_tag.id}'))

            first_task = ActivityLog.query.first()
            if first_task:
                routes_to_test.append((f'/tasks/view/{first_task.id}', f'Task View #{first_task.id}'))
                routes_to_test.append((f'/tasks/update/{first_task.id}', f'Task Update #{first_task.id}'))

            first_vendor = Vendor.query.first()
            if first_vendor:
                routes_to_test.append((f'/vendors/view/{first_vendor.id}', f'Vendor View #{first_vendor.id}'))
                routes_to_test.append((f'/vendors/update/{first_vendor.id}', f'Vendor Update #{first_vendor.id}'))

            first_req = TagRequest.query.first()
            if first_req:
                routes_to_test.append((f'/tag-requests/view/{first_req.id}', f'Tag Request View #{first_req.id}'))

            first_jira = JiraHistory.query.first()
            if first_jira:
                routes_to_test.append((f'/jira/update-tags/{first_jira.id}', f'Jira Update Tags #{first_jira.id}'))

        print(f"Testing {len(routes_to_test)} routes across all blueprints...\n")
        passed = 0
        failed = 0
        errors = []

        for url, name in routes_to_test:
            try:
                res = client.get(url, follow_redirects=False)
                status = res.status_code
                size = len(res.data)
                if status == 200:
                    passed += 1
                    print(f"[200 OK] {name:35s} | {url:35s} | {size:7d} bytes")
                elif status in (301, 302):
                    print(f"[{status} REDIR] {name:35s} | {url:35s} -> {res.location}")
                    passed += 1
                else:
                    failed += 1
                    print(f"[{status} FAIL] {name:35s} | {url:35s}")
                    errors.append((name, url, status, res.data[:300].decode('utf-8', errors='ignore')))
            except Exception as e:
                import traceback
                failed += 1
                tb = traceback.format_exc()
                print(f"[EXC FAIL] {name:35s} | {url:35s} -> {e}")
                errors.append((name, url, 'EXCEPTION', tb))


        print(f"\n==========================================")
        print(f"RESULTS: {passed} passed, {failed} failed out of {len(routes_to_test)} routes.")
        print(f"==========================================")
        if errors:
            print("\nDetailed Errors:")
            for name, url, status, snippet in errors:
                print(f"\n--- {name} ({url}) Status: {status} ---")
                print(snippet)

if __name__ == '__main__':
    run_tests()
