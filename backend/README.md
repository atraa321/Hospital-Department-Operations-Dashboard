# Backend (FastAPI + MySQL)

## 1. Setup

```powershell
cd backend
python -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

- `DATABASE_URL=mysql+pymysql://user:password@host:3306/disease_analytics?charset=utf8mb4`

## 2. Run

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload
```

## 3. APIs

- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `POST /api/v1/imports/start?import_type=CASE_INFO` with multipart file
- `GET /api/v1/imports`
- `GET /api/v1/imports/{batch_id}/issues`
- `GET /api/v1/imports/{batch_id}/issues.csv`
- `GET /api/v1/imports/{batch_id}/issues.xlsx`
- `GET /api/v1/imports/backup/case-cost.xlsx`
- `POST /api/v1/imports/clear/case-cost` (body: `{"confirm_text":"CLEAR_CASE_COST_DATA"}`)
- `POST /api/v1/imports/restore/case-cost` (multipart: `file` + `confirm_text=CLEAR_CASE_COST_DATA`)
- `GET /api/v1/quality/overview`
- `GET /api/v1/quality/orphan-patients`
- `POST /api/v1/quality/orphan-patients/{patient_id}/action`
- `GET /api/v1/analytics/cost-structure`
- `GET /api/v1/analytics/cost-trend`
- `GET /api/v1/analytics/clinical-top`
- `GET /api/v1/analytics/disease-priority`
- `GET /api/v1/dip/versions`
- `POST /api/v1/dip/mappings/recalculate`
- `GET /api/v1/dip/mappings`
- `GET /api/v1/dip/unmapped`
- `GET /api/v1/dip/stats`
- `POST /api/v1/dip/unmapped/{patient_id}/manual-fill`
- `GET /api/v1/alerts/rules`
- `PUT /api/v1/alerts/rules/{rule_code}`
- `POST /api/v1/alerts/run-detection`
- `GET /api/v1/alerts/hits`
- `GET /api/v1/workorders`
- `POST /api/v1/workorders/{id}/assign`
- `POST /api/v1/workorders/{id}/status`
- `POST /api/v1/workorders/sla-check`
- `GET /api/v1/workorders/stats`
- `GET /api/v1/reports/monthly`
- `GET /api/v1/reports/executive`
- `GET /api/v1/reports/cases.csv`
- `GET /api/v1/config`
- `PUT /api/v1/config/{config_key}`

## 4. 鉴权头（内网MVP）

- `X-User-Id: your_user_id`
- `X-Role: ADMIN | DIRECTOR | MEDICAL | INSURANCE | FINANCE | VIEWER`
- `X-Dept-Name: 科室名（科室数据域用户建议必传）`
