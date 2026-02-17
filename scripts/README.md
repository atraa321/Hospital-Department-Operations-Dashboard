# scripts 目录说明

- 根目录 `一键启动_病种分析系统.bat`：双击即可启动后端与前端。
- 根目录 `一键停止_病种分析系统.bat`：双击停止后端与前端（按窗口标题+端口兜底）。
- `scripts/start_backend.cmd`：后端初始化并启动（供一键启动调用）。
- `scripts/start_frontend.cmd`：前端初始化并启动（供一键启动调用）。
- `ops/`：部署、备份、回滚脚本。
- `ops/winserver/`：Win Server 内网部署脚本（生产服务化、离线包、静态前端服务）。
