# Frontend (React + Vite)

## Run

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Default dev URL: `http://localhost:5173`

The Vite proxy forwards `/api` to `http://127.0.0.1:18080`.

## Dev Auth

可选开发环境变量：

- `VITE_API_BASE_URL=/api/v1`
- `VITE_DEV_AUTH_USER_ID=dev_user`
- `VITE_DEV_AUTH_ROLE=ADMIN`
- `VITE_DEV_AUTH_DEPT=普外科`

说明：

- 开发模式下会自动附带 `X-User-Id`、`X-Role`、`X-Dept-Name`
- 生产模式下前端不再自带角色头，统一依赖后端 `/api/v1/auth/me`

