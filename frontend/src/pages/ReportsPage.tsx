import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { EChart } from '../components/EChart';
import {
  downloadCaseReportCsv,
  fetchDepartmentRankings,
  fetchOperationsOverview,
  type CurrentUser,
} from '../lib/api';

interface ReportsPageProps {
  currentUser?: CurrentUser;
}

export function ReportsPage({ currentUser }: ReportsPageProps) {
  const [dateFromInput, setDateFromInput] = useState('');
  const [dateToInput, setDateToInput] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const overviewQuery = useQuery({
    queryKey: ['operations-overview-report', dateFrom, dateTo],
    queryFn: () => fetchOperationsOverview({ dateFrom: dateFrom || undefined, dateTo: dateTo || undefined, limit: 12 }),
  });

  const rankingsQuery = useQuery({
    queryKey: ['operations-rankings-report', dateFrom, dateTo],
    queryFn: () => fetchDepartmentRankings({ dateFrom: dateFrom || undefined, dateTo: dateTo || undefined, limit: 50 }),
  });

  const chartOption = useMemo(
    () => ({
      color: ['#1b7f87', '#f08a48'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['出院人次', '次均费用'] },
      grid: { left: 40, right: 20, top: 36, bottom: 24 },
      xAxis: { type: 'category', data: (overviewQuery.data?.monthly_trend ?? []).map((item) => item.period) },
      yAxis: [{ type: 'value' }, { type: 'value' }],
      series: [
        {
          name: '出院人次',
          type: 'bar',
          data: (overviewQuery.data?.monthly_trend ?? []).map((item) => item.case_count),
        },
        {
          name: '次均费用',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: (overviewQuery.data?.monthly_trend ?? []).map((item) => item.avg_cost),
        },
      ],
    }),
    [overviewQuery.data?.monthly_trend],
  );

  const applyFilter = () => {
    setDateFrom(dateFromInput);
    setDateTo(dateToInput);
  };

  return (
    <section className="dashboard-grid">
      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>运营月报中心</h2>
          <p>统一查看全院趋势、科室评分榜以及脱敏后的病例导出能力。</p>
        </header>
        <div className="issue-toolbar">
          <label className="field field--compact">
            <span>统计开始</span>
            <input type="date" value={dateFromInput} onChange={(event) => setDateFromInput(event.target.value)} />
          </label>
          <label className="field field--compact">
            <span>统计结束</span>
            <input type="date" value={dateToInput} onChange={(event) => setDateToInput(event.target.value)} />
          </label>
          <button className="btn-secondary" onClick={applyFilter} type="button">
            更新月报
          </button>
        </div>
      </article>

      <div className="metrics-row">
        <div className="metric-card">
          <p className="metric-label">全院出院人次</p>
          <p className="metric-value">{overviewQuery.data?.summary.total_cases ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">全院次均费用</p>
          <p className="metric-value">{overviewQuery.data?.summary.avg_cost ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">平均住院日</p>
          <p className="metric-value">{overviewQuery.data?.summary.avg_los ?? 0}</p>
        </div>
        <div className="metric-card metric-card--good">
          <p className="metric-label">综合运营均分</p>
          <p className="metric-value">{overviewQuery.data?.summary.average_score ?? 0}</p>
        </div>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>全院月度趋势</h2>
          <p>用于汇总运营月报中的核心趋势图。</p>
        </header>
        <EChart option={chartOption} style={{ height: 320 }} />
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>科室评分月报</h2>
          <p>{currentUser?.role === 'ADMIN' ? '管理员可查看全院完整月报。' : '科主任可查看全院排名与脱敏导出。'}</p>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>科室</th>
                <th>综合评分</th>
                <th>效率分</th>
                <th>收益分</th>
                <th>质量分</th>
                <th>出院人次</th>
                <th>主要问题</th>
              </tr>
            </thead>
            <tbody>
              {(rankingsQuery.data ?? []).map((item) => (
                <tr key={item.dept_name}>
                  <td>{item.dept_name}</td>
                  <td>{item.total_score}</td>
                  <td>{item.efficiency_score}</td>
                  <td>{item.revenue_score}</td>
                  <td>{item.quality_score}</td>
                  <td>{item.case_count}</td>
                  <td>{item.summary_issue}</td>
                </tr>
              ))}
              {!rankingsQuery.data?.length ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center' }}>
                    暂无数据
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>报表导出</h2>
          <p>管理员导出全量病例明细，非管理员自动按权限范围与姓名脱敏。</p>
        </header>
        <div className="action-row" style={{ marginTop: 12 }}>
          <button className="btn-primary" onClick={() => downloadCaseReportCsv()} type="button">
            导出运营病例报表 CSV
          </button>
        </div>
      </article>
    </section>
  );
}
