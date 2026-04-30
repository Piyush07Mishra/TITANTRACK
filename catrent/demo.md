# CatRent Faculty Demo Script (End-to-End)

Use this file as your live narration + execution checklist while screen recording.

---

## 1) Demo Goal (Opening line)

"This is **CatRent**, an equipment rental management system for heavy machinery. It includes operator and machine management, QR-based checkout/check-in, demand forecasting, anomaly monitoring, and email reminders, all connected to a cloud database."

---

## 2) Pre-Demo Quick Checklist (2 min before recording)

- Stable internet connection
- Gmail SMTP already working in `.env`
- Browser tabs ready:
  - `http://127.0.0.1:8010/`
  - `http://127.0.0.1:8010/admin/`
- Terminal opened in project root

---

## 3) Start Commands (Show this first)

From terminal:

```bash
cd "/Users/ayushmishra/Projects/cat-digital-2/catrent"
./dev_stop.sh 8010
./dev_start.sh
```


What this does:
1. Stops old process on port 8010
2. Loads `.env`
3. Runs migrations
4. Starts Django server on `127.0.0.1:8010`

Optional status check:

```bash
./dev_status.sh 8010
```

---

## 4) Recommended Recording Flow (12–18 min)

## Phase A — Project Intro + Architecture (1–2 min)

Say:
- "Single Django server hosts backend APIs, frontend templates, and admin panel."
- "Data is stored in PostgreSQL (Neon) via `DATABASE_URL`."
- "Media and notifications are environment-driven and secure through `.env`."

Show:
- Terminal running server
- Home page (`/`)

---

## Phase B — Admin Data Setup (2–3 min)

Open admin: `http://127.0.0.1:8010/admin/`

### B1) Operators
- Go to **Catrentapp → Operators**
- Show one operator with valid email
- Explain: email is used by reminder system

### B2) Machines
- Go to **Catrentapp → Machines**
- Show machine entries (example: `BLD3001`)
- Explain: each machine has QR code for checkout flow

### B3) Rentals
- Go to **Catrentapp → Rentals**
- Show Active/Completed statuses
- Explain lifecycle fields: `start_date`, `expected_end_date`, `actual_end_date`

---

## Phase C — Dashboard + QR Checkout/Check-in (3–4 min)

Open dashboard: `http://127.0.0.1:8010/`

### C1) QR Checkout
- Use URL shortcut to simulate scan quickly:
  - `http://127.0.0.1:8010/checkout/BLD3001/`
- Fill operator/site/dates and submit checkout
- Explain: status changes to **Rented**

### C2) Check-in
- From dashboard rented section, click **Check In** on an active rental card
- In the modal scanner, scan the same machine QR used for checkout
- Wait for success message from API and dashboard refresh
- Explain: machine status returns to **Available** and rental moves to **Completed**

Quick fallback (if camera permission fails during demo):
1. Open browser DevTools on dashboard
2. Run a POST request with rental id and equipment id:

```javascript
fetch('/checkin/18/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({ equipment_id: 'BLD3001' })
}).then(r => r.json()).then(console.log)
```

3. Refresh dashboard and show rental card removed from active list

---

## Phase D — Forecasting Demo (2–3 min)

### D0) Terminal Run (model test + auto-sync)

Run this first to show end-to-end ML execution:

```bash
cd "/Users/ayushmishra/Projects/cat-digital-2"
source .venv/bin/activate

cd Demand-forecast-unit
python derive_features.py
python demand_forecasting.py
```

What this run does:
1. Builds features from rental data.
2. Trains/tests the RandomForest demand model.
3. Generates forecast PNGs and feature-importance PNGs.
4. Automatically removes old dashboard PNGs and moves new PNGs to `catrent/forecast/`.

Quick verification:

```bash
cd "/Users/ayushmishra/Projects/cat-digital-2"
ls -lh catrent/forecast
```

On dashboard forecast section:
- Choose each equipment type (Bulldozer, Crane, Excavator, Loader)
- Show generated graph updates

How demand forecasting is working (say this while showing graphs):
1. System reads historical rental rows from database (`Rental` + machine type).
2. It builds weekly demand per equipment type (`year_week`) and creates training features.
3. Model used is `RandomForestRegressor` (scikit-learn).
4. Train/test split is year-based (train up to 2024, test on 2025 data).
5. It predicts weekly checkout demand, then saves outputs in `forecast/`:
  - `equipment_demand_forecast.csv`
  - `equipment_demand_forecast_2025_combined.png`
  - `<EquipmentType>_demand_forecast_2025.png`
6. Dashboard image endpoint (`/forecast_image/<equipment_type>/`) serves the generated chart.

Say:
- "Forecast is generated from historical rental features and saved as images/CSV."
- "Crane pipeline issue was fixed; all types now render properly."

Optional API view (fast proof):
- `http://127.0.0.1:8010/forecast/Crane/` (trigger generation from Django side)
- `http://127.0.0.1:8010/forecast_image/Crane/`
- `http://127.0.0.1:8010/forecast_image/Excavator/`
- `http://127.0.0.1:8010/forecast_image/Loader/`
- `http://127.0.0.1:8010/forecast_image/Bulldozer/`
- `http://127.0.0.1:8010/forecast_image/Compactor/`

---

## Phase E — Anomaly Monitoring (2–3 min)

On dashboard anomaly sections:
- Show severity counters (high/medium/low)
- Show anomaly doughnut chart
- Show top anomaly features list
- Show toast/live alert area

Say:
- "Anomalies are loaded from precomputed JSON and visualized in real time style."

Direct API proof:
- `http://127.0.0.1:8010/anomaly-data/`

### E1) Anomaly Validation (terminal proof before UI)

```bash
cd "/Users/ayushmishra/Projects/cat-digital-2/catrent"

# Check anomaly file exists
ls -lh detailed_anomaly_report.json

# Validate source JSON
python3 - <<'PY'
import json
with open('detailed_anomaly_report.json') as f:
  data = json.load(f)
print('source_rows=', len(data))
print('sample_keys=', sorted(data[0].keys()))
PY

# Validate API response used by dashboard
python3 - <<'PY'
import json, urllib.request
url = 'http://127.0.0.1:8010/anomaly-data/'
with urllib.request.urlopen(url, timeout=10) as r:
  payload = json.loads(r.read().decode())
print('api_rows=', len(payload))
sev = {}
for x in payload:
  s = str(x.get('severity', 'UNKNOWN')).upper()
  sev[s] = sev.get(s, 0) + 1
print('severity_counts=', sev)
PY
```

Say:
- "Anomaly UI is driven from /anomaly-data/ endpoint backed by JSON file."
- "Backend returns top 100 anomalies for dashboard performance."

How anomaly is actually working in this project:
1. Anomalies are precomputed and stored in `detailed_anomaly_report.json` (offline/generated earlier).
2. Django endpoint `/anomaly-data/` reads this file and returns JSON to the dashboard.
3. For fast UI rendering, backend sends first 100 rows in the API response.
4. Frontend uses that response to:
  - update severity counters,
  - render anomaly charts,
  - show top deviant features,
  - trigger toast alerts.
5. This means dashboard is visualizing real anomaly records from file + API, not training anomaly model live in browser.

---

## Phase F — Email Reminder (Live Proof) (2–3 min)

In terminal (keep server tab open, use another terminal tab):

```bash
cd "/Users/ayushmishra/Projects/cat-digital-2/catrent"
set -a && source .env && set +a
./.venv/bin/python manage.py send_rental_remainders
```

Show output lines like:
- `Found rental ...`
- `Sending email to ...`
- `Reminder sent for rental ...`

Say:
- "This confirms SMTP + business reminder logic works end-to-end."

---

## Phase G — Database Verification (1–2 min)

Run quick DB health and counts:

```bash
cd "/Users/ayushmishra/Projects/cat-digital-2/catrent"
set -a && source .env && set +a
./.venv/bin/python manage.py shell -c "from catrentapp.models import Machine,Rental,Operator; print('Machines=',Machine.objects.count()); print('Operators=',Operator.objects.count()); print('Rentals=',Rental.objects.count()); print('ActiveRentals=',Rental.objects.filter(active=True,status='Active').count())"
```

Optional rental distribution:

```bash
./.venv/bin/python manage.py shell -c "from django.db.models import Count; from catrentapp.models import Rental; print(list(Rental.objects.values('machine__type').annotate(c=Count('id')).order_by('machine__type')))"
```

Say:
- "These counts confirm persistence and real DB-backed operations."

---

## 5) Faculty-Friendly Narration Script (Compact)

Use this if you want a smooth spoken flow:

1. "I’ll start the system with one command; backend + frontend + admin all run together."
2. "In admin, I manage operators, machines, and rentals."
3. "Checkout/check-in is QR-driven for field usability."
4. "Forecasting predicts demand by equipment type from historical data."
5. "Anomaly panel tracks abnormal operational behavior and feature-level signals."
6. "Email reminders are sent automatically for upcoming check-ins."
7. "Finally, I’ll verify DB counts to prove data is persisted and consistent."

---

## 6) Backup Plan if Something Fails During Demo

## If port error occurs

```bash
cd "/Users/ayushmishra/Projects/cat-digital-2/catrent"
./dev_stop.sh 8010
./dev_start.sh
```

## If checkout URL not opening
Use:
- `http://127.0.0.1:8010/checkout/BLD3001/`

## If no reminder email sent
- Ensure at least one rental is `Active` and due today
- Ensure operator email exists
- Re-run reminder command

## If browser shows old JS cache
- Hard refresh: `Cmd + Shift + R`

---

## 7) End-of-Demo Closing Line

"CatRent demonstrates a complete rental operations workflow: admin-controlled master data, QR operational flow, predictive forecasting, anomaly intelligence, and automated reminder communication, all backed by a cloud database and environment-secured configuration."

---

## 8) One-Screen Command Summary

```bash
# Start
cd "/Users/ayushmishra/Projects/cat-digital-2/catrent"
./dev_start.sh

# Status
./dev_status.sh 8010

# Reminder send
set -a && source .env && set +a
./.venv/bin/python manage.py send_rental_remainders

# DB quick counts
./.venv/bin/python manage.py shell -c "from catrentapp.models import Machine,Rental,Operator; print(Machine.objects.count(), Rental.objects.count(), Operator.objects.count())"

# Stop
./dev_stop.sh 8010

# Demand forecast model test (manual pipeline)
cd "/Users/ayushmishra/Projects/cat-digital-2"
source .venv/bin/activate
cd Demand-forecast-unit
python derive_features.py
python demand_forecasting.py

# Anomaly quick check
cd "/Users/ayushmishra/Projects/cat-digital-2/catrent"
python3 - <<'PY'
import json, urllib.request
u='http://127.0.0.1:8010/anomaly-data/'
data=json.loads(urllib.request.urlopen(u).read().decode())
print('api_rows=', len(data))
PY
```
se this base for all checks: http://127.0.0.1:8010

Dashboard: http://127.0.0.1:8010/

Admin: http://127.0.0.1:8010/admin/

Add machine/list machines: http://127.0.0.1:8010/add/

Add operator: http://127.0.0.1:8010/add-operator/

Anomaly data (JSON): http://127.0.0.1:8010/anomaly-data/

Checkout by equipment ID: http://127.0.0.1:8010/checkout/BLD3001/

Checkin endpoint by rental ID (POST only, do not open directly in browser): http://127.0.0.1:8010/checkin/1/

Delete machine by pk: http://127.0.0.1:8010/delete/1/

Download QR by pk: http://127.0.0.1:8010/download/1/

Forecast JSON by type:

http://127.0.0.1:8010/forecast/Bulldozer/
http://127.0.0.1:8010/forecast/Excavator/
http://127.0.0.1:8010/forecast/Loader/
http://127.0.0.1:8010/forecast/Crane/
Forecast image by type:

http://127.0.0.1:8010/forecast_image/Bulldozer/ (same pattern for other types).
Perfect — here are real working URLs from your current DB.

Dashboard: http://127.0.0.1:8010/
Admin: http://127.0.0.1:8010/admin/
Add machine: http://127.0.0.1:8010/add/
Add operator: http://127.0.0.1:8010/add-operator/
Anomaly data: http://127.0.0.1:8010/anomaly-data/
Checkout links (equipment_id)

http://127.0.0.1:8010/checkout/EQX1001/
http://127.0.0.1:8010/checkout/CRN2001/
http://127.0.0.1:8010/checkout/BLD3001/
http://127.0.0.1:8010/checkout/LDR4001/
Machine action links (pk)

Download QR (pk=1): http://127.0.0.1:8010/download/1/
Delete machine (pk=1): http://127.0.0.1:8010/delete/1/
Check-in endpoint (active rental found, POST only)

Active rental is id=18 for BLD3001
http://127.0.0.1:8010/checkin/18/
Forecast links

http://127.0.0.1:8010/forecast/Bulldozer/
http://127.0.0.1:8010/forecast/Excavator/
http://127.0.0.1:8010/forecast/Loader/
http://127.0.0.1:8010/forecast/Crane/
http://127.0.0.1:8010/forecast_image/Bulldozer/
http://127.0.0.1:8010/forecast_image/Excavator/
http://127.0.0.1:8010/forecast_image/Loader/
http://127.0.0.1:8010/forecast_image/Crane/  

---

## 9) How Automated Mail Works (No Manual Run Needed)

Current setup:
- Cron runs reminder job every 2 minutes.
- Job command: `manage.py send_rental_remainders`
- Logs:
  - `/tmp/catrent-reminders.out.log`
  - `/tmp/catrent-reminders.err.log`

When email is sent:
1. Rental must be `active=True`
2. Rental due date must be today
3. Operator must have valid email

Important behavior:
- If rental is already checked in (`active=False`), no reminder is sent.
- If no rental is due today, command exits without sending.
- Server does not need to be running for cron mail checks.

Demo proof commands:

```bash
# Check active cron entry
crontab -l

# Watch reminder logs live
tail -f /tmp/catrent-reminders.out.log
tail -f /tmp/catrent-reminders.err.log
```

Narration line:
"Reminder email automation is background-scheduled by cron every 2 minutes, and mail is sent only when an active rental is actually due today."