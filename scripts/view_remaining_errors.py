error_lines = [
    ("jira/list.html", 533),
    ("jira/update_tags.html", 140),
    ("profile/index.html", 237),
    ("reports/index.html", 343),
    ("reports/pdf.html", 408),
    ("settings/index.html", 36),
    ("tags/renew.html", 244),
    ("tags/repository.html", 340),
    ("tags/update-rule-request.html", 286),
    ("tags/view.html", 334),
    ("tag_requests/list.html", 768),
    ("tag_requests/view.html", 76),
    ("vendors/view.html", 173),
]

for rel_path, lno in error_lines:
    path = "app/templates/" + rel_path
    print(f"=== {rel_path} Line {lno} ===")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = max(0, lno - 8)
    end = min(len(lines), lno + 8)
    for i in range(start, end):
        print(f"{i+1:4d}: {lines[i].rstrip()}")
    print("\n")
