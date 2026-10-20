import os
import sys

# Ensure python-app is on path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.models import db, User, Tag, ActivityLog, Property, Vendor, Role, RolePermission
from app.constants import Constants
from app.services.excel_service import ExcelService

def test_system():
    print("[1/6] Creating application factory...")
    app = create_app()
    assert app is not None, "App creation failed"
    print("      App initialized successfully.")

    with app.app_context():
        print("[2/6] Verifying database connectivity & row counts...")
        user_count = User.query.count()
        tag_count = Tag.query.count()
        task_count = ActivityLog.query.count()
        prop_count = Property.query.count()
        vendor_count = Vendor.query.count()
        role_count = Role.query.count()
        print(f"      Users: {user_count}, Tags: {tag_count}, Tasks: {task_count}, Properties: {prop_count}, Vendors: {vendor_count}, Roles: {role_count}")
        assert user_count > 0, "No users found in database"
        assert tag_count > 0, "No tags found in database"

        print("[3/6] Verifying bcrypt password hashes...")
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None, "Admin user not found"
        assert admin.check_password('Password123'), "Admin password verification failed"
        print("      Admin credentials (admin / Password123) verified successfully!")

        khristine = User.query.filter_by(username='khristine.a').first()
        if khristine:
            assert khristine.check_password('Password123'), "Khristine password verification failed"
            print("      Khristine credentials (khristine.a / Password123) verified successfully!")

        print("[4/6] Verifying Role Permissions Matrix...")
        perms = RolePermission.query.filter_by(role_id=3).all()
        admin_perms = {p.permission_key: bool(p.permission_value) for p in perms}
        assert admin_perms.get('dashboard') is True, "Admin dashboard permission missing"
        assert admin_perms.get('settings') is True, "Admin settings permission missing"
        print(f"      Admin permissions: {list(admin_perms.keys())}")

        print("[5/6] Testing Excel export service...")
        tags = Tag.query.limit(10).all()
        stream = ExcelService.export_tags(tags)
        assert stream.getbuffer().nbytes > 0, "Export tags generated empty buffer"
        print(f"      Excel export generated {stream.getbuffer().nbytes} bytes.")

    print("[6/6] Testing Flask Test Client routes...")
    client = app.test_client()
    
    # 1. Login page GET
    resp = client.get('/login')
    assert resp.status_code == 200, f"/login returned {resp.status_code}"
    assert b"Martech TMS" in resp.data
    assert b"Sign In" in resp.data
    print("      GET /login -> 200 OK")

    # 2. Login POST
    resp = client.post('/login', data={'username': 'admin', 'password': 'Password123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dashboard Overview" in resp.data or b"Active Tags" in resp.data
    print("      POST /login (admin) -> 200 OK (Redirected to Dashboard)")

    # 3. Tags Inventory GET
    resp = client.get('/tags')
    if resp.status_code != 200:
        print(f"      ERROR on /tags: status={resp.status_code}, data={resp.data[:500]}")
    assert resp.status_code == 200, f"/tags returned {resp.status_code}"
    assert b"Tag Inventory" in resp.data
    print("      GET /tags -> 200 OK")

    # 4. Tasks GET
    resp = client.get('/tasks')
    assert resp.status_code == 200
    assert b"Tasks &amp; Activity Logs" in resp.data or b"Tasks" in resp.data
    print("      GET /tasks -> 200 OK")

    # 5. Settings GET
    resp = client.get('/settings')
    assert resp.status_code == 200
    assert b"Settings" in resp.data
    print("      GET /settings -> 200 OK")

    # 6. Additional Blueprints & Detail Views
    resp = client.get('/tag-requests')
    assert resp.status_code == 200
    print("      GET /tag-requests -> 200 OK")

    resp = client.get('/properties')
    assert resp.status_code == 200
    print("      GET /properties -> 200 OK")

    resp = client.get('/vendors')
    assert resp.status_code == 200
    print("      GET /vendors -> 200 OK")

    resp = client.get('/jira')
    assert resp.status_code == 200
    print("      GET /jira -> 200 OK")

    resp = client.get('/reports')
    assert resp.status_code == 200
    print("      GET /reports -> 200 OK")

    resp = client.get('/profile')
    assert resp.status_code == 200
    print("      GET /profile -> 200 OK")

    resp = client.get('/notifications')
    assert resp.status_code == 200
    print("      GET /notifications -> 200 OK")

    with app.app_context():
        first_tag = Tag.query.first()
        if first_tag:
            resp = client.get(f'/tags/{first_tag.id}')
            assert resp.status_code == 200
            print(f"      GET /tags/{first_tag.id} (Tag Detail) -> 200 OK")

        first_task = ActivityLog.query.first()
        if first_task:
            resp = client.get(f'/tasks/{first_task.id}')
            assert resp.status_code == 200
            print(f"      GET /tasks/{first_task.id} (Task Detail) -> 200 OK")

        first_vendor = Vendor.query.first()
        if first_vendor:
            resp = client.get(f'/vendors/{first_vendor.id}')
            assert resp.status_code == 200
            print(f"      GET /vendors/{first_vendor.id} (Vendor Detail) -> 200 OK")

    resp = client.get('/tags/export')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    print("      GET /tags/export (Excel Download) -> 200 OK")

    print("\nALL VERIFICATION CHECKS & ROUTE TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_system()
