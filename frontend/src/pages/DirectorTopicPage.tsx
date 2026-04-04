import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { EChart } from '../components/EChart';
import {
  fetchDepartmentOperationDetail,
  fetchDepartmentRankings,
  type CurrentUser,
} from '../lib/api';

interface DirectorTopicPageProps {
  currentUser?: CurrentUser;
}

export function DirectorTopicPage({ currentUser }: DirectorTopicPageProps) {
  const isDirector = currentUser?.role === 'DIRECTOR';
  const defaultDept = isDirector ? currentUser?.dept_name ?? '' : '';
  const [deptInput, setDeptInput] = useState(defaultDept);
  const [deptName, setDeptName] = useState(defaultDept);
  const [dateFromInput, setDateFromInput] = useState('');
  const [dateToInput, setDateToInput] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [errorText, setErrorText] = useState('');

  useEffect(() => {
    if (defaultDept) {
      setDeptInput(defaultDept);
      setDeptName(defaultDept);
    }
  }, [defaultDept]);

  const rankingsQuery = useQuery({
    queryKey: ['department-rankings-lite', dateFrom, dateTo],
    queryFn: () => fetchDepartmentRankings({ dateFrom: dateFrom || undefined, dateTo: dateTo || undefined, limit: 50 }),
  });

  const detailQuery = useQuery({
    queryKey: ['department-operation-detail', deptName, dateFrom, dateTo],
    queryFn: () =>
      fetchDepartmentOperationDetail({
        deptName,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
      }),
    enabled: Boolean(deptName),
  });

  const deptOptions = useMemo(() => rankingsQuery.data?.map((item) => item.dept_name) ?? [], [rankingsQuery.data]);

  const trendOption = useMemo(
    () => ({
      color: ['#1b7f87', '#f08a48', '#cb5c54'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['出院人次', '平均住院日', '异常命中'] },
      grid: { left: 40, right: 20, top: 36, bottom: 24 },
      xAxis: { type: 'category', data: (detailQuery.data?.monthly_trend ?? []).map((item) => item.period) },
      yAxis: [{ type: 'value' }, { type: 'value' }],
      series: [
        {
          name: '出院人次',
          type: 'bar',
          data: (detailQuery.data?.monthly_trend ?? []).map((item) => item.case_count),
        },
        {
          name: '平均住院日',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: (detailQuery.data?.monthly_trend ?? []).map((item) => item.avg_los),
        },
        {
          name: '异常命中',
          type: 'line',
          smooth: true,
          data: (detailQuery.data?.monthly_trend ?? []).map((item) => item.issue_count),
        },
      ],
    }),
    [detailQuery.data?.monthly_trend],
  );

  const costOption = useMemo(
    () => ({
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['42%', '72%'],
          data: (detailQuery.data?.cost_structure ?? []).map((item) => ({ name: item.name, value: item.value })),
        },
      ],
    }),
    [detailQuery.data?.cost_structure],
  );

  const doctorOption = useMemo(
    () => ({
      color: ['#1b7f87', '#ef7c49'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['次均费用', '异常命中'] },
      grid: { left: 120, right: 20, top: 36, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: {
        type: 'category',
        data: (detailQuery.data?.doctor_compare ?? []).slice(0, 8).map((item) => item.doctor_name),
      },
      series: [
        {
          name: '次均费用',
          type: 'bar',
          data: (detailQuery.data?.doctor_compare ?? []).slice(0, 8).map((item) => item.avg_total_cost),
        },
        {
          name: '异常命中',
          type: 'bar',
          data: (detailQuery.data?.doctor_compare ?? []).slice(0, 8).map((item) => item.issue_count),
        },
      ],
    }),
    [detailQuery.data?.doctor_compare],
  );

  const anomalyOption = useMemo(
    () => ({
      color: ['#cb5c54', '#f08a48', '#d8ba4d'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['RED', 'ORANGE', 'YELLOW'] },
      grid: { left: 40, right: 20, top: 36, bottom: 36 },
      xAxis: {
        type: 'category',
        data: (detailQuery.data?.anomaly_categories ?? []).map((item) => item.rule_name || item.rule_code),
        axisLabel: { rotate: 20 },
      },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'RED',
          type: 'bar',
          stack: 'severity',
          data: (detailQuery.data?.anomaly_categories ?? []).map((item) => item.red_count),
        },
        {
          name: 'ORANGE',
          type: 'bar',
          stack: 'severity',
          data: (detailQuery.data?.anomaly_categories ?? []).map((item) => item.orange_count),
        },
        {
          name: 'YELLOW',
          type: 'bar',
          stack: 'severity',
          data: (detailQuery.data?.anomaly_categories ?? []).map((item) => item.yellow_count),
        },
      ],
    }),
    [detailQuery.data?.anomaly_categories],
  );

  const handleApply = () => {
    if (dateFromInput && dateToInput && dateFromInput > dateToInput) {
      setErrorText('开始日期不能晚于结束日期。');
      return;
    }
    if (!deptInput.trim()) {
      setErrorText('请先选择科室。');
      return;
    }
    setErrorText('');
    setDeptName(deptInput.trim());
    setDateFrom(dateFromInput);
    setDateTo(dateToInput);
  };

  const summary = detailQuery.data?.summary;

  return (
    <section className="dashboard-grid">
      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>科室经营分析</h2>
          <p>围绕单科的月度运营得分、费用结构、医师差异和异常项目做复盘。</p>
        </header>
        <div className="issue-toolbar">
          <label className="field field--compact">
            <span>科室</span>
            <select value={deptInput} onChange={(event) => setDeptInput(event.target.value)} disabled={isDirector}>
              <option value="">请选择科室</option>
              {deptOptions.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </label>
          <label className="field field--compact">
            <span>统计开始</span>
            <input type="date" value={dateFromInput} onChange={(event) => setDateFromInput(event.target.value)} />
          </label>
          <label className="field field--compact">
            <span>统计结束</span>
            <input type="date" value={dateToInput} onChange={(event) => setDateToInput(event.target.value)} />
          </label>
          <button className="btn-secondary" onClick={handleApply} type="button">
            查看科室分析
          </button>
        </div>
        {errorText ? <p className="error-text">{errorText}</p> : null}
      </article>

      <div className="metrics-row metrics-row--five">
        <div className="metric-card">
          <p className="metric-label">综合评分</p>
          <h3 className="metric-value">{summary?.score.total_score ?? 0}</h3>
          <p className="metric-trend">效率 {summary?.score.efficiency_score ?? 0} / 收益 {summary?.score.revenue_score ?? 0} / 质量 {summary?.score.quality_score ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">出院人次</p>
          <h3 className="metric-value">{summary?.case_count ?? 0}</h3>
          <p className="metric-trend">{summary?.dept_name || '未选择科室'}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">次均费用</p>
          <h3 className="metric-value">{summary?.avg_cost ?? 0}</h3>
          <p className="metric-trend">用于衡量单科成本结构</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">平均住院日</p>
          <h3 className="metric-value">{summary?.avg_los ?? 0}</h3>
          <p className="metric-trend">周转效率核心指标</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">异常命中</p>
          <h3 className="metric-value">{summary?.issue_count ?? 0}</h3>
          <p className="metric-trend">需要结合规则分类排查</p>
        </div>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>月度趋势</h2>
          <p>用同一页面同时看出院规模、住院日和异常波动。</p>
        </header>
        <EChart option={trendOption} style={{ height: 320 }} />
      </article>

      <div className="analysis-grid">
        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>费用结构</h2>
            <p>识别药品、材料、检查等费用是否挤压收益得分。</p>
          </header>
          <EChart option={costOption} style={{ height: 300 }} />
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>医师对比</h2>
            <p>优先复盘次均费用高且异常命中多的医生组。</p>
          </header>
          <EChart option={doctorOption} style={{ height: 300 }} />
        </article>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>评分驱动因素</h2>
          <p>解释为什么这次分数高或低，便于直接拿去做月度复盘。</p>
        </header>
        <div className="driver-grid">
          {(detailQuery.data?.score_drivers ?? []).map((item) => (
            <div key={item.title} className={`driver-card driver-card--${item.tone}`}>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
            </div>
          ))}
          {!detailQuery.data?.score_drivers.length ? <p className="empty-hint">暂无评分解释。</p> : null}
        </div>
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>异常规则分布</h2>
          <p>把高频异常规则聚焦到可执行整改项。</p>
        </header>
        <EChart option={anomalyOption} style={{ height: 320 }} />
      </article>

      <div className="analysis-grid">
        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>高金额项目 TOP</h2>
            <p>重点查看对科室收益和结构影响最大的项目。</p>
          </header>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>项目</th>
                  <th>总金额</th>
                  <th>病例数</th>
                  <th>占比</th>
                </tr>
              </thead>
              <tbody>
                {(detailQuery.data?.detail_top_items ?? []).map((item, index) => (
                  <tr key={`${item.item_name}-${index}`}>
                    <td>{item.item_name}</td>
                    <td>{item.total_amount}</td>
                    <td>{item.case_count}</td>
                    <td>{item.ratio}%</td>
                  </tr>
                ))}
                {!detailQuery.data?.detail_top_items.length ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center' }}>
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
            <h2>建议动作</h2>
            <p>给科主任和运营官的下一步动作建议。</p>
          </header>
          <div className="suggestion-list">
            {(detailQuery.data?.suggestions ?? []).map((item) => (
              <div key={item} className="suggestion-item">
                {item}
              </div>
            ))}
            {!detailQuery.data?.suggestions.length ? <p className="empty-hint">暂无建议。</p> : null}
          </div>
        </article>
      </div>
    </section>
  );
}
