import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { EChart } from '../components/EChart';
import { MetricCard } from '../components/MetricCard';
import { fetchOperationsOverview, type CurrentUser } from '../lib/api';

interface DashboardPageProps {
  currentUser?: CurrentUser;
}

export function DashboardPage({ currentUser }: DashboardPageProps) {
  const [dateFromInput, setDateFromInput] = useState('');
  const [dateToInput, setDateToInput] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [errorText, setErrorText] = useState('');

  const overviewQuery = useQuery({
    queryKey: ['operations-overview', dateFrom, dateTo],
    queryFn: () =>
      fetchOperationsOverview({
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        limit: 12,
      }),
  });

  const trendOption = useMemo(
    () => ({
      color: ['#1b7f87', '#f08a48', '#cb5c54'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['出院人次', '平均住院日', '异常命中'] },
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
          name: '平均住院日',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: (overviewQuery.data?.monthly_trend ?? []).map((item) => item.avg_los),
        },
        {
          name: '异常命中',
          type: 'line',
          smooth: true,
          data: (overviewQuery.data?.monthly_trend ?? []).map((item) => item.issue_count),
        },
      ],
    }),
    [overviewQuery.data?.monthly_trend],
  );

  const scoreOption = useMemo(
    () => ({
      color: ['#1b7f87'],
      tooltip: { trigger: 'axis' },
      grid: { left: 70, right: 20, top: 16, bottom: 32 },
      xAxis: {
        type: 'category',
        data: (overviewQuery.data?.rankings ?? []).map((item) => item.dept_name),
        axisLabel: { rotate: 20 },
      },
      yAxis: { type: 'value', max: 100 },
      series: [
        {
          type: 'bar',
          data: (overviewQuery.data?.rankings ?? []).map((item) => item.total_score),
          label: { show: true, position: 'top' },
        },
      ],
    }),
    [overviewQuery.data?.rankings],
  );

  const handleApply = () => {
    if (dateFromInput && dateToInput && dateFromInput > dateToInput) {
      setErrorText('开始日期不能晚于结束日期。');
      return;
    }
    setErrorText('');
    setDateFrom(dateFromInput);
    setDateTo(dateToInput);
  };

  const handleReset = () => {
    setDateFromInput('');
    setDateToInput('');
    setDateFrom('');
    setDateTo('');
    setErrorText('');
  };

  const summary = overviewQuery.data?.summary;
  const rankings = overviewQuery.data?.rankings ?? [];
  const highlights = overviewQuery.data?.highlights ?? [];
  const suggestions = overviewQuery.data?.suggestions ?? [];

  return (
    <section className="dashboard-grid">
      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>院级运营驾驶舱</h2>
          <p>
            默认面向院运营官，先看科室综合运营评分，再定位月度波动与重点改进动作。
            {currentUser?.role === 'DIRECTOR' && currentUser.dept_name ? ` 当前默认科室视角为 ${currentUser.dept_name}。` : ''}
          </p>
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
          <button className="btn-secondary" onClick={handleApply} type="button">
            应用筛选
          </button>
          <button className="btn-ghost" onClick={handleReset} type="button">
            重置
          </button>
        </div>
        {errorText ? <p className="error-text">{errorText}</p> : null}
      </article>

      <div className="metrics-row metrics-row--five">
        <MetricCard label="出院人次" value={String(summary?.total_cases ?? 0)} trend="全院月度出院规模" />
        <MetricCard label="综合运营均分" value={`${summary?.average_score ?? 0}`} trend="效率50% / 收益30% / 质量20%" tone="good" />
        <MetricCard label="平均住院日" value={`${summary?.avg_los ?? 0} 天`} trend="用于衡量科室周转效率" />
        <MetricCard label="周转指数" value={String(summary?.turnover_index ?? 0)} trend="按出院量与住院日折算" />
        <MetricCard label="风险科室数" value={String(summary?.risk_department_count ?? 0)} trend="低分或质量偏弱的科室" tone="alert" />
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>科室综合运营评分排行榜</h2>
          <p>综合评分越高，说明效率、收益和质量表现越均衡。</p>
        </header>
        <div className="cockpit-grid">
          <div>
            <EChart option={scoreOption} style={{ height: 320 }} />
          </div>
          <div className="dashboard-aside">
            <div className="dashboard-aside-card">
              <p className="dashboard-aside-label">本期焦点</p>
              {highlights.map((item) => (
                <div key={`${item.label}-${item.dept_name}`} className="highlight-item">
                  <strong>{item.label}</strong>
                  <span>{item.dept_name}</span>
                  <p>{item.detail}</p>
                </div>
              ))}
              {!highlights.length ? <p className="empty-hint">当前暂无高亮提示。</p> : null}
            </div>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>排名</th>
                <th>科室</th>
                <th>综合评分</th>
                <th>效率分</th>
                <th>收益分</th>
                <th>质量分</th>
                <th>出院人次</th>
                <th>平均住院日</th>
                <th>主要问题</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((item, index) => (
                <tr key={item.dept_name}>
                  <td>{index + 1}</td>
                  <td>{item.dept_name}</td>
                  <td>{item.total_score}</td>
                  <td>{item.efficiency_score}</td>
                  <td>{item.revenue_score}</td>
                  <td>{item.quality_score}</td>
                  <td>{item.case_count}</td>
                  <td>{item.avg_los}</td>
                  <td>{item.summary_issue}</td>
                </tr>
              ))}
              {!rankings.length ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center' }}>
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
          <h2>月度趋势与异常联动</h2>
          <p>用于判断月度规模、周转和异常命中是否同步波动。</p>
        </header>
        <EChart option={trendOption} style={{ height: 320 }} />
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>本月建议动作</h2>
          <p>把评分、趋势和异常信息转成院运营官可直接下发的动作建议。</p>
        </header>
        <div className="suggestion-list">
          {suggestions.map((item) => (
            <div key={item} className="suggestion-item">
              {item}
            </div>
          ))}
          {!suggestions.length ? <p className="empty-hint">当前暂无建议动作。</p> : null}
        </div>
      </article>
    </section>
  );
}
