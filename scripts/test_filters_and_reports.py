import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

# 1. Login
login_res = session.post(f"{BASE_URL}/login", data={"username": "admin", "password": "Password123"})
assert login_res.status_code in [200, 302], f"Login failed: {login_res.status_code}"
print("Logged in successfully.")

# 2. Check /reports for JSON encoding and chart elements
res = session.get(f"{BASE_URL}/reports/")
assert res.status_code == 200, f"/reports/ failed: {res.status_code}"
html = res.text
assert "&#34;" not in html[html.find("const statusCounts ="):html.find("const statusCounts =") + 200], "Found HTML escaped quotes in statusCounts!"
assert "new Chart(statusCtx" in html, "statusChart initialization missing!"
assert "new Chart(projectCtx" in html, "projectChart initialization missing!"
assert "new Chart(subCtx" in html, "subChart initialization missing!"
print("Report charts verified: Valid JSON without &#34; escaping and Chart declarations present.")

# 3. Check /tags with search & filters
res = session.get(f"{BASE_URL}/tags/?keyword=Samsung")
assert res.status_code == 200
soup = BeautifulSoup(res.text, "html.parser")
pills = soup.find_all(class_="filter-pill")
print(f"Tags ?keyword=Samsung pills found: {len(pills)}")
assert any("Keyword" in p.text and "Samsung" in p.text for p in pills), "Keyword filter pill not found!"

# Check status=expiring
res = session.get(f"{BASE_URL}/tags/?status=expiring")
assert res.status_code == 200
soup = BeautifulSoup(res.text, "html.parser")
pills = soup.find_all(class_="filter-pill")
print(f"Tags ?status=expiring pills found: {len(pills)}")
assert any("Status" in p.text and "Expiring" in p.text for p in pills), "Expiring filter pill not found!"

# Check multiple filters and remove_filter_url
res = session.get(f"{BASE_URL}/tags/?keyword=Samsung&status=1")
soup = BeautifulSoup(res.text, "html.parser")
pills = soup.find_all(class_="filter-pill")
print(f"Tags multi-filter pills found: {len(pills)}")
pill_links = [p.get('href') for p in pills if p.get('href')]
print(f"Pill remove links: {pill_links}")
# One link should remove keyword and preserve status=1
assert any("status=1" in link and "keyword" not in link for link in pill_links), "Filter pill removal URL didn't preserve other filters!"

# 4. Check /tasks metrics and filters
res = session.get(f"{BASE_URL}/tasks/")
assert res.status_code == 200
soup = BeautifulSoup(res.text, "html.parser")
metric_vals = [el.text.strip() for el in soup.find_all(class_="dashboard-metric-value")]
print(f"Tasks metric-val texts: {metric_vals}")
assert len(metric_vals) >= 4, "Expected at least 4 metric values on /tasks"
for mv in metric_vals[:4]:
    assert mv.isdigit(), f"Metric value '{mv}' is not an integer!"

# Check tasks filter pills
res = session.get(f"{BASE_URL}/tasks/?keyword=Samsung&status=1")
soup = BeautifulSoup(res.text, "html.parser")
pills = soup.find_all(class_="filter-pill")
print(f"Tasks ?keyword=Samsung&status=1 pills found: {len(pills)}")
assert len(pills) >= 2, "Tasks filter pills missing!"

# 5. Check /tag-requests
res = session.get(f"{BASE_URL}/tag-requests/?status=pending")
assert res.status_code == 200
assert "<?php" not in res.text, "Found <?php in /tag-requests/"
soup = BeautifulSoup(res.text, "html.parser")
pills = soup.find_all(class_="filter-pill")
print(f"Tag requests ?status=pending pills found: {len(pills)}")

# 6. Check /properties
res = session.get(f"{BASE_URL}/properties/?keyword=Samsung")
assert res.status_code == 200
assert "<?php" not in res.text, "Found <?php in /properties/"
print("/properties/?keyword=Samsung OK")

# 7. Check /vendors
res = session.get(f"{BASE_URL}/vendors/?keyword=Google")
assert res.status_code == 200
assert "<?php" not in res.text, "Found <?php in /vendors/"
print("/vendors/?keyword=Google OK")

print("\nALL BACKEND AND TEMPLATE VERIFICATIONS PASSED!")
