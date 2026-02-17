import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { DashboardPage } from './pages/DashboardPage';
import { DiseasePriorityPage } from './pages/DiseasePriorityPage';
import { DirectorTopicPage } from './pages/DirectorTopicPage';
import { DipStatsPage } from './pages/DipStatsPage';
import { ImportPage } from './pages/ImportPage';
import { ReportsPage } from './pages/ReportsPage';
import { VulnerabilityPage } from './pages/VulnerabilityPage';
import { WorkOrderPage } from './pages/WorkOrderPage';

const links = [
  { to: '/dashboard', label: '病种驾驶舱' },
  { to: '/imports', label: '数据导入中心' },
  { to: '/director-topic', label: '科主任专题' },
  { to: '/dip-stats', label: 'DIP统计' },
  { to: '/disease-priority', label: '病种筛选' },
  { to: '/vulnerability', label: '漏洞分析' },
  { to: '/workorders', label: '预警工单' },
  { to: '/reports', label: '报表中心' },
];

function App() {
  return (
    <div className="app-surface">
      <div className="grain-overlay" />
      <div className="light-shape light-shape--one" />
      <div className="light-shape light-shape--two" />
      <header className="topbar">
        <div className="brand-block">
          <p className="brand-kicker">Intranet Edition</p>
          <h1>病种分析系统</h1>
          <p className="brand-caption">运营前移 · 极致控本 · 质效提升</p>
        </div>
        <nav className="topnav">
          {links.map((item) => (
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
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/imports" element={<ImportPage />} />
          <Route path="/director-topic" element={<DirectorTopicPage />} />
          <Route path="/dip-stats" element={<DipStatsPage />} />
          <Route path="/disease-priority" element={<DiseasePriorityPage />} />
          <Route path="/vulnerability" element={<VulnerabilityPage />} />
          <Route path="/workorders" element={<WorkOrderPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
