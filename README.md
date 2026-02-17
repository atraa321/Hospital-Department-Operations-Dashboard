# 病种分析系统 V2

## 项目结构

- `backend/` FastAPI + MySQL API
- `frontend/` React + Vite 前端
- `docs/` PRD、任务、追踪、技术方案、UAT与上线文档
- `scripts/` 启动与脚本索引说明
- `基础数据/` 原始Excel数据
- `ops/` 部署、备份、回滚脚本（PowerShell）
- `一键启动_病种分析系统.bat` 根目录一键启动脚本
- `一键停止_病种分析系统.bat` 根目录一键停止脚本

## 本地启动

### 1) 后端

```powershell
cd backend
python -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 18080 --reload
```

### 2) 前端

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

前端 `.env` 可选项：

- `VITE_USER_ID=dev_user`
- `VITE_USER_ROLE=ADMIN`
- `VITE_USER_DEPT=普外科`

## 关键接口

- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `POST /api/v1/imports/start?import_type=CASE_INFO`
- `GET /api/v1/imports`
- `GET /api/v1/imports/{batch_id}/issues`
- `GET /api/v1/imports/{batch_id}/issues.csv`
- `GET /api/v1/imports/{batch_id}/issues.xlsx`
- `GET /api/v1/imports/backup/case-cost.xlsx`
- `POST /api/v1/imports/clear/case-cost` (body: `{"confirm_text":"CLEAR_CASE_COST_DATA"}`)
- `POST /api/v1/imports/restore/case-cost` (multipart: `file` + `confirm_text=CLEAR_CASE_COST_DATA`)
- `GET /api/v1/quality/overview`
- `GET /api/v1/analytics/disease-priority`
- `GET /api/v1/dip/stats`
- `POST /api/v1/alerts/run-detection`
- `GET /api/v1/workorders`
- `GET /api/v1/reports/executive`

## 部署脚本

- `ops/deploy_backend.ps1`
- `ops/deploy_frontend.ps1`
- `ops/backup_db.ps1`
- `ops/restore_db.ps1`
- `ops/部署与回滚说明.md`
- `ops/WinServer内网部署指南.md`
- `ops/winserver/deploy_winserver.ps1`
- `ops/winserver/make_offline_bundle.ps1`
- `ops/winserver/make_oneclick_bundle.ps1`
- `ops/winserver/deploy_from_bundle.ps1`
- `ops/winserver/oneclick_install.ps1`
- `ops/winserver/oneclick_install.bat`
- `ops/winserver/install_services.ps1`
- `ops/winserver/uninstall_services.ps1`

## 文档入口

- `docs/README.md`
- `docs/PRD_病种分析系统.md`
- `docs/开发任务清单_病种分析系统.md`
- `docs/项目开发追踪_病种分析系统.md`
- `docs/技术开发方案_病种分析系统.md`
- `docs/UAT验收清单_病种分析系统.md`
- `docs/上线检查清单_病种分析系统.md`
