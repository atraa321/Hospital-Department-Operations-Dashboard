# Backend (FastAPI + MySQL)

## Current API Direction

- 主线 API 已切到 `operations/*`，服务院级运营驾驶舱与科室经营分析
- `imports/*` 当前仅面向管理员前台开放
- `dip/*`、`director/topic*`、`analytics/*` 中的旧病种/DIP 端点仍保留以兼容历史代码，但已标记为 `deprecated`

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
- `DB_BOOTSTRAP_ON_STARTUP=true` and `DB_SCHEMA_GUARDS_ON_STARTUP=true` are development defaults

## 2. Migrate

Recommended production flow:

```powershell
cd backend
.\.venv312\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

Recommended production `.env`:

- `DB_BOOTSTRAP_ON_STARTUP=false`
- `DB_SCHEMA_GUARDS_ON_STARTUP=false`

## 3. Run

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload
```

## 4. APIs

- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `GET /api/v1/auth/me`
- `GET /api/v1/operations/overview`
- `GET /api/v1/operations/rankings`
- `GET /api/v1/operations/departments/{dept_name}`
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

## 4.1 Deprecated APIs

以下端点仍保留，但仅用于平滑迁移，不建议给新页面继续接入：

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
- `GET /api/v1/director/topic`
- `GET /api/v1/director/topic/{diagnosis_code}`
- `POST /api/v1/director/topic/{diagnosis_code}/export/pdf`

## 5. 鉴权头（内网MVP）

开发模式：

- `AUTH_MODE=dev_header`
- `X-User-Id: your_user_id`
- `X-Role: ADMIN | DIRECTOR | MEDICAL | INSURANCE | FINANCE | VIEWER`
- `X-Dept-Name: 科室名（科室数据域用户建议必传）`

生产模式：

- `AUTH_MODE=trusted_header`
- IIS Windows 身份认证开启
- IIS 反向代理写入 `X-Remote-User`
- 角色/科室从 `AUTH_USER_MAP_FILE` 映射，不再信任前端自带角色头
