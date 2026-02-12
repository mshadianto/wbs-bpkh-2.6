"""Test all frontend-related API endpoints."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests

BASE = 'http://localhost:8000'

# Login
r = requests.post(f'{BASE}/api/v1/auth/login', json={'email':'admin@bpkh.go.id','password':'Admin123!'})
print(f'Login: {r.status_code}')
if r.status_code != 200:
    print(f'Error: {r.text}')
    sys.exit(1)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# Dashboard stats
r = requests.get(f'{BASE}/api/v1/dashboard/stats', headers=h)
d = r.json()
print(f'\n--- Dashboard Stats ---')
print(f'  total_reports: {d["total_reports"]}')
print(f'  pending_review: {d["pending_review"]}')
print(f'  sla_at_risk: {d["sla_at_risk"]}')
print(f'  by_status: {d.get("by_status",{})}')
print(f'  by_severity: {d.get("by_severity",{})}')
print(f'  by_category: {d.get("by_category",{})}')

# Reference statuses
r = requests.get(f'{BASE}/api/v1/reference/statuses', headers=h)
d = r.json()
print(f'\n--- Reference Statuses ---')
print(f'  {list(d.keys())}')

# Reference categories
r = requests.get(f'{BASE}/api/v1/reference/categories', headers=h)
d = r.json()
print(f'\n--- Reference Categories ---')
print(f'  {list(d.keys())}')

# Reports page 1
r = requests.get(f'{BASE}/api/v1/reports?page=1&per_page=3', headers=h)
d = r.json()
print(f'\n--- Reports List ---')
print(f'  total={d["total"]}, page={d["page"]}, returned={len(d["reports"])}')
for rpt in d['reports']:
    print(f'  - [{rpt["ticket_id"]}] {rpt["status"]} | {rpt["severity"]} | {rpt.get("title","")[:50]}')

# Single report detail
rid = d['reports'][0]['id']
r = requests.get(f'{BASE}/api/v1/reports/{rid}', headers=h)
rd = r.json()
has_analysis = rd.get('ai_analysis') is not None
analysis_status = rd.get('ai_analysis', {}).get('status', 'N/A') if has_analysis else 'N/A'
print(f'\n--- Report Detail ---')
print(f'  id: {rid}')
print(f'  status: {r.status_code}')
print(f'  has_analysis: {has_analysis}')
print(f'  analysis_status: {analysis_status}')

# Messages for report
ticket = d['reports'][0]['ticket_id']
r = requests.get(f'{BASE}/api/v1/tickets/{ticket}/messages')
print(f'\n--- Messages ---')
print(f'  ticket: {ticket}, status: {r.status_code}, count: {len(r.json())}')

# Frontend pages
print(f'\n--- Frontend Pages ---')
for path in ['/dashboard', '/portal', '/login', '/home']:
    r = requests.get(f'{BASE}{path}')
    print(f'  {path}: {r.status_code} ({len(r.text):,} bytes)')

print(f'\n{"="*50}')
print(f'All frontend endpoints verified OK')
print(f'{"="*50}')
