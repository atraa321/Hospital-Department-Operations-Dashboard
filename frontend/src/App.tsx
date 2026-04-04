import { Suspense, lazy, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { fetchCurrentUser, type CurrentUser } from './lib/api';

const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const DirectorTopicPage = lazy(() =>
  import('./pages/DirectorTopicPage').then((module) => ({ default: module.DirectorTopicPage })),
);
const ImportPage = lazy(() => import('./pages/ImportPage').then((module) => ({ default: module.ImportPage })));
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((module) => ({ default: module.ReportsPage })));

type NavItem = {
  to: string;
  label: string;
  roles?: string[];
};

const links: NavItem[] = [
  { to: '/dashboard', label: '运营驾驶舱' },
  { to: '/department-analysis', label: '科室分析' },
  { to: '/reports', label: '报表中心' },
  { to: '/imports', label: '数据导入中心', roles: ['ADMIN'] },
];

function roleLabel(currentUser: CurrentUser | undefined) {
  if (!currentUser) return '';
  if (currentUser.role === 'ADMIN') return '管理员';
  if (currentUser.role === 'DIRECTOR') return '科主任';
  return currentUser.role;
}

function defaultRoute(currentUser: CurrentUser | undefined) {
  if (currentUser?.role === 'DIRECTOR') {
    return '/department-analysis';
  }
  return '/dashboard';
}

function routeFallback() {
  return (
    <section className="panel panel--wide">
      <header className="panel-head">
        <h2>页面加载中</h2>
        <p>正在按需加载当前模块，请稍候。</p>
      </header>
    </section>
  );
}

function App() {
  const currentUserQuery = useQuery({
    queryKey: ['current-user'],
    queryFn: fetchCurrentUser,
    retry: false,
  });

  const currentUser = currentUserQuery.data;
  const navItems = useMemo(
    () => links.filter((item) => !item.roles || item.roles.includes(currentUser?.role ?? '')),
    [currentUser?.role],
  );
  const homePath = defaultRoute(currentUser);

  return (
    <div className="app-surface">
      <div className="grain-overlay" />
      <div className="light-shape light-shape--one" />
      <div className="light-shape light-shape--two" />
      <header className="topbar">
        <div className="brand-block">
          <p className="brand-kicker">Hospital Operations Cockpit</p>
          <h1>科室运营分析平台</h1>
          <p className="brand-caption">月度运营对标 · 科室复盘 · 数据驱动改进</p>
        </div>
        <nav className="topnav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              className={({ isActive }) => (isActive ? 'topnav-link is-active' : 'topnav-link')}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="content-shell">
        <section className="status-ribbon">
          <strong>
            {currentUser
              ? `当前用户：${currentUser.display_name || currentUser.user_id}`
              : currentUserQuery.isError
                ? '当前用户：未通过认证'
                : '当前用户：身份加载中'}
          </strong>
          <span>
            {currentUser
              ? `${roleLabel(currentUser)}${currentUser.dept_name ? ` · ${currentUser.dept_name}` : ''}`
              : currentUserQuery.isError
                ? '请检查 IIS Windows 身份认证或开发鉴权配置'
                : '正在从后端获取可信身份'}
          </span>
        </section>
        <Suspense fallback={routeFallback()}>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage currentUser={currentUser} />} />
            <Route path="/department-analysis" element={<DirectorTopicPage currentUser={currentUser} />} />
            <Route path="/reports" element={<ReportsPage currentUser={currentUser} />} />
            <Route
              path="/imports"
              element={currentUser?.role === 'ADMIN' ? <ImportPage /> : <Navigate to={homePath} replace />}
            />
            <Route path="*" element={<Navigate to={homePath} replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}

export default App;
