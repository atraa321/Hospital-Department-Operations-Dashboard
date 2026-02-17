# Win Server 内网部署指南

适用场景：
- 部署机器为 Windows Server。
- 系统在局域网内访问。
- 支持在线安装依赖、离线包部署、以及“一键包拷贝后直接部署”。

基础依赖：
- Python 3.12（必须，后端运行与前端静态服务都使用 Python）
- MySQL 8.x（必须，业务数据库）
- Node.js 20+（仅在线构建前端时需要；离线包部署可不安装）
- 管理员权限 PowerShell（安装服务与放行防火墙时需要）

---

## 1. 端口规划

默认端口：
- 后端 API：`18080`
- 前端页面：`5173`

局域网访问地址：
- 前端：`http://<服务器IP>:5173`
- 后端健康检查：`http://<服务器IP>:18080/api/v1/health`

---

## 2. 推荐方案：一键部署包（拷贝到目标机后单次执行）

### 2.1 在可联网机器制作一键包（仅系统）

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\winserver\make_oneclick_bundle.ps1 `
  -ProjectRoot "D:\病种分析V2" `
  -OutputDir "D:\deploy\oneclick-bundles" `
  -ApiBaseUrl "http://10.10.10.20:18080/api/v1" `
  -IncludeSeedData $true
```

输出目录示例：
- `disease_analytics_oneclick_20260226_xxxxxx\`
- `disease_analytics_oneclick_20260226_xxxxxx.zip`

包内关键文件：
- `oneclick_install.ps1`：一键部署入口
- `oneclick_install.bat` / `一键部署_病种分析系统.bat`：双击部署入口
- `deploy.config.psd1`：部署配置文件
- `project_source/`：后端/前端/运维脚本源码
- `python_wheels/`：后端离线依赖
- `frontend_dist/`：前端已构建产物
- `seed_data/`：基础初始化数据（可选）

### 2.2 最可靠方案：制作“系统 + 现有数据”一键包（推荐）

如果你要把当前服务器的业务数据一起迁移到目标 Win Server，建议直接在源机器执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\winserver\make_oneclick_bundle.ps1 `
  -ProjectRoot "D:\病种分析V2" `
  -OutputDir "D:\deploy\oneclick-bundles" `
  -ApiBaseUrl "http://10.10.10.20:18080/api/v1" `
  -IncludeCurrentData $true `
  -CurrentDatabaseUrl "mysql+pymysql://root:你的密码@127.0.0.1:3306/disease_analytics?charset=utf8mb4" `
  -MySqlBinDir "C:\Program Files\MySQL\MySQL Server 8.0\bin" `
  -IncludeUploads $true `
  -CurrentUploadsDir "D:\病种分析V2\backend\data\uploads"
```

说明：
- `IncludeCurrentData=$true`：打包时自动执行 `mysqldump`，生成 `data_snapshot/database.sql`。
- `IncludeUploads=$true`：把上传文件目录镜像到 `data_snapshot/uploads`。
- 如你已提前导出 `.sql` 文件，可改用 `-CurrentDataSqlFile "D:\backup\xxx.sql"`，无需 `CurrentDatabaseUrl`。
- 打包脚本会把 `deploy.config.psd1` 里的 `RestoreSnapshot` 自动设置为 `$true`。

### 2.3 在目标服务器一键运行

1. 将 zip 解压到目标机任意目录（例如 `D:\offline\disease_analytics_oneclick_20260226_123000`）。
2. 编辑 `deploy.config.psd1`，至少修改 `DatabaseUrl`，并确认：
   - `RestoreSnapshot = $true`（迁移现有数据时）
   - `SnapshotSqlRelativePath = "data_snapshot\database.sql"`
   - `RestoreUploads = $true`（如需迁移上传文件）
   - `MySqlBinDir`（当 `mysql.exe` 不在 PATH 时需要填写）
3. 管理员权限运行：

```powershell
cd D:\offline\disease_analytics_oneclick_20260226_123000
.\oneclick_install.bat
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File .\oneclick_install.ps1
```

一键部署会自动完成：
- 同步代码到 `ProjectRoot`
- 安装 Python 依赖（离线 wheels）
- 创建/更新 `backend\.env`
- 自动创建数据库（`InitDatabase = $true`）
- 可选导入基础数据（`SeedData = $true`）
- 可选恢复快照 SQL（`RestoreSnapshot = $true`）
- 可选恢复上传目录（`RestoreUploads = $true`）
- 安装并启动 Windows 服务（恢复完成后启动）
- 放行防火墙端口

---

## 3. 在线部署（服务器可联网）

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\winserver\deploy_winserver.ps1 `
  -ProjectRoot "D:\病种分析V2" `
  -DatabaseUrl "mysql+pymysql://root:你的密码@127.0.0.1:3306/disease_analytics?charset=utf8mb4" `
  -BackendPort 18080 `
  -FrontendPort 5173 `
  -InitDatabase $true `
  -SeedData $false `
  -InstallServices $true `
  -OpenFirewall $true
```

说明：
- 脚本会创建 `backend\.venv312` 并安装后端依赖。
- 自动生成/更新 `backend\.env`（生产参数、端口、CORS）。
- 自动构建 `frontend\dist`，并写入生产 API 地址。
- 自动安装 Windows 服务并启动：
  - `DiseaseAnalyticsBackend`
  - `DiseaseAnalyticsFrontend`

---

## 4. 轻量离线包制作（在可联网机器）

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\winserver\make_offline_bundle.ps1 `
  -ProjectRoot "D:\病种分析V2" `
  -OutputDir "D:\deploy\offline-bundles" `
  -ApiBaseUrl "http://10.10.10.20:18080/api/v1"
```

输出：
- `python_wheels/`：后端离线依赖
- `frontend_dist/`：前端构建产物
- `ops_winserver/`：部署脚本副本
- `*.zip`：离线部署压缩包

---

## 5. 轻量离线部署（服务器不可联网）

先将离线包解压到服务器（例如 `D:\offline\disease_analytics_bundle_时间戳`），再执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\winserver\deploy_from_bundle.ps1 `
  -BundleDir "D:\offline\disease_analytics_bundle_20260225_210000" `
  -ProjectRoot "D:\病种分析V2" `
  -DatabaseUrl "mysql+pymysql://root:你的密码@127.0.0.1:3306/disease_analytics?charset=utf8mb4" `
  -BackendPort 18080 `
  -FrontendPort 5173 `
  -InstallServices $true `
  -OpenFirewall $true
```

---

## 6. 服务运维

安装服务脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\winserver\install_services.ps1 `
  -ProjectRoot "D:\病种分析V2" `
  -BackendPort 18080 `
  -FrontendPort 5173
```

卸载服务脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\winserver\uninstall_services.ps1
```

日志目录：
- `D:\病种分析V2\logs\backend.stdout.log`
- `D:\病种分析V2\logs\backend.stderr.log`
- `D:\病种分析V2\logs\frontend.stdout.log`
- `D:\病种分析V2\logs\frontend.stderr.log`

---

## 7. 首次验收清单

1. 访问 `http://127.0.0.1:18080/api/v1/health` 返回 200。
2. 浏览器访问 `http://127.0.0.1:5173` 页面可打开。
3. 局域网其他机器访问 `http://<服务器IP>:5173` 可打开。
4. 前端页面可正常调用后端接口（无跨域报错）。
5. Windows 服务状态为 `Running`，重启服务器后可自动拉起。
