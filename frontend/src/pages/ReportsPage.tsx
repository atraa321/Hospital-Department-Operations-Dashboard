import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import { downloadCaseReportCsv, fetchExecutiveReport, fetchMonthlyReport } from '../lib/api';

export function ReportsPage() {
  const monthlyQuery = useQuery({
    queryKey: ['report-monthly'],
    queryFn: fetchMonthlyReport,
  });
  const execQuery = useQuery({
    queryKey: ['report-exec'],
    queryFn: fetchExecutiveReport,
  });

  const chartOption = useMemo(
    () => ({
      color: ['#0f6f77', '#ea6a41'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['病例数', '规则命中'] },
      grid: { left: 12, right: 12, top: 28, bottom: 12, containLabel: true },
      xAxis: {
        type: 'category',
        data: (monthlyQuery.data?.disease_metrics ?? []).map((x) => x.period),
      },
      yAxis: [{ type: 'value' }, { type: 'value' }],
      series: [
        {
          name: '病例数',
          type: 'bar',
          yAxisIndex: 0,
          data: (monthlyQuery.data?.disease_metrics ?? []).map((x) => x.case_count),
        },
        {
          name: '规则命中',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          data: (monthlyQuery.data?.rule_metrics ?? []).map((x) => x.hit_count),
        },
      ],
    }),
    [monthlyQuery.data],
  );

  return (
    <section className="dashboard-grid">
      <div className="metrics-row">
        <div className="metric-card">
          <p className="metric-label">病例总量</p>
          <p className="metric-value">{execQuery.data?.total_cases ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">次均费用</p>
          <p className="metric-value">{execQuery.data?.avg_cost ?? 0}</p>
        </div>
        <div className="metric-card metric-card--alert">
          <p className="metric-label">待闭环工单</p>
          <p className="metric-value">{execQuery.data?.open_workorders ?? 0}</p>
        </div>
        <div className="metric-card metric-card--good">
          <p className="metric-label">闭环率</p>
          <p className="metric-value">{execQuery.data?.close_rate ?? 0}%</p>
        </div>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>月报趋势</h2>
          <p>病种月报 + 漏洞月报</p>
        </header>
        <ReactECharts option={chartOption} style={{ height: 320 }} />
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>报表导出</h2>
          <p>非管理员导出自动脱敏</p>
        </header>
        <div className="action-row" style={{ marginTop: 12 }}>
          <button className="btn-primary" onClick={() => downloadCaseReportCsv()} type="button">
            导出病例报表 CSV
          </button>
        </div>
      </article>
    </section>
  );
}
