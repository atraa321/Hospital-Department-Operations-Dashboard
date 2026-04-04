# Hospital Department Operations Dashboard

医院科室运营分析平台 V2，面向院级运营官与科主任，聚焦月度运营数据的可视化、科室综合评分、权限分域查看和运营数据导入。

## 核心能力

- `运营驾驶舱`
  - 全院月度运营总览
  - 科室综合运营评分排行榜
  - 高分 / 低分科室特征与本月建议动作
- `科室分析`
  - 单科月度趋势
  - 效率 / 收益 / 质量分项得分
  - 医师对比、费用结构、异常分类、高金额项目 TOP
- `报表中心`
  - 全院月报与科室月报查看
  - 病例报表导出
  - 非管理员自动按权限范围和姓名脱敏
- `数据导入中心`
  - 仅管理员可见
  - 运营分析所需数据导入、批次追踪、问题导出、备份与恢复

## 权限模型

- `ADMIN`
  - 可查看全院数据
  - 可查看任意科室详情
  - 可进入数据导入中心
- `DIRECTOR`
  - 默认进入本科室经营分析
  - 可查看全院科室排名
  - 不可查看其他科室明细，也不可跨科室导出或查询明细

## 当前产品主线

- 默认主线已升级为“医院科室运营驾驶舱”
- 前台当前保留页面：
  - `运营驾驶舱`
  - `科室分析`
  - `报表中心`
  - `数据导入中心`（仅管理员）
- 旧 `DIP / 病种优先级 / 漏洞分析 / DIP 版科主任专题` 前台主线已移除
- 后端仍暂时保留部分旧接口以兼容历史代码，但已标记为 `deprecated`，不建议继续接入新页面

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

后端数据库在开发环境默认允许启动时自动建表/补列：

- `DB_BOOTSTRAP_ON_STARTUP=true`
- `DB_SCHEMA_GUARDS_ON_STARTUP=true`

生产部署建议改为 Alembic 迁移模式：

```powershell
cd backend
.\.venv312\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

并在 `backend\.env` 中设置：

- `DB_BOOTSTRAP_ON_STARTUP=false`
- `DB_SCHEMA_GUARDS_ON_STARTUP=false`

### 2) 前端

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

前端 `.env` 可选项：

- `VITE_API_BASE_URL=/api/v1`
- `VITE_DEV_AUTH_USER_ID=dev_user`
- `VITE_DEV_AUTH_ROLE=ADMIN`
- `VITE_DEV_AUTH_DEPT=普外科`

说明：

- 开发模式下，前端会在 `import.meta.env.DEV` 时自动附带开发鉴权头
- 生产模式下，前端不再自带角色头，统一通过 `/api/v1/auth/me` 获取可信身份

## 关键接口

- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `GET /api/v1/auth/me`
- `GET /api/v1/operations/overview`
- `GET /api/v1/operations/rankings`
- `GET /api/v1/operations/departments/{dept_name}`
- `POST /api/v1/imports/start?import_type=CASE_INFO`
- `GET /api/v1/imports`
- `GET /api/v1/imports/{batch_id}/issues`
- `GET /api/v1/imports/{batch_id}/issues.csv`
- `GET /api/v1/imports/{batch_id}/issues.xlsx`
- `GET /api/v1/imports/backup/case-cost.xlsx`
- `POST /api/v1/imports/clear/case-cost` (body: `{"confirm_text":"CLEAR_CASE_COST_DATA"}`)
- `POST /api/v1/imports/restore/case-cost` (multipart: `file` + `confirm_text=CLEAR_CASE_COST_DATA`)
- `GET /api/v1/quality/overview`
- `GET /api/v1/reports/executive`
- `GET /api/v1/reports/cases.csv`

## 废弃接口说明

以下接口仍在后端保留，但仅用于平滑迁移，OpenAPI 中已标记为废弃：

- `/api/v1/dip/*`
- `/api/v1/director/topic*`
- `/api/v1/analytics/cost-structure`
- `/api/v1/analytics/cost-trend`
- `/api/v1/analytics/clinical-top`
- `/api/v1/analytics/disease-priority`

## 部署脚本

- `ops/deploy_backend.ps1`
- `ops/deploy_frontend.ps1`
- `ops/backup_db.ps1`
- `ops/restore_db.ps1`
- `ops/部署与回滚说明.md`
- `ops/WinServer内网部署指南.md`
- `ops/WinServer内网部署改造清单.md`
- `ops/服务器上线执行手册.md`
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
- `docs/运营驾驶舱_UAT说明.md`
- `docs/旧接口与旧代码下线计划.md`
