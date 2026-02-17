import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import {
  exportDirectorTopicPdf,
  fetchDipDepartments,
  fetchDirectorTopicDetail,
  fetchDirectorTopicOverview,
} from '../lib/api';

type ChartRefMap = Record<string, ReactECharts | null>;
type DirectorTopicSavedFilter = {
  pointValueInput: string;
};

const DIRECTOR_TOPIC_FILTER_KEY = 'director_topic_filters_v1';
const DIRECTOR_POINT_DEFAULT = '5.5';
const SEVERITY_COLORS = {
  RED: '#e53935',
  ORANGE: '#fb8c00',
  YELLOW: '#fdd835',
} as const;

function parseNumberInput(input: string): number | undefined {
  if (!input.trim()) return undefined;
  const value = Number(input);
  if (!Number.isFinite(value) || value <= 0) return undefined;
  return value;
}

function loadDirectorTopicSavedFilter(): DirectorTopicSavedFilter {
  if (typeof window === 'undefined') {
    return { pointValueInput: DIRECTOR_POINT_DEFAULT };
  }
  const raw = window.localStorage.getItem(DIRECTOR_TOPIC_FILTER_KEY);
  if (!raw) {
    return { pointValueInput: DIRECTOR_POINT_DEFAULT };
  }
  try {
    const parsed = JSON.parse(raw) as Partial<DirectorTopicSavedFilter>;
    const pointValueInput = String(parsed.pointValueInput ?? '').trim();
    const point = parseNumberInput(pointValueInput);
    if (!point) {
      return { pointValueInput: DIRECTOR_POINT_DEFAULT };
    }
    return { pointValueInput };
  } catch {
    return { pointValueInput: DIRECTOR_POINT_DEFAULT };
  }
}

function saveDirectorTopicSavedFilter(payload: DirectorTopicSavedFilter) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(DIRECTOR_TOPIC_FILTER_KEY, JSON.stringify(payload));
}

function downloadDataUrl(name: string, dataUrl: string) {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = `${name}_${Date.now()}.png`;
  link.click();
}

export function DirectorTopicPage() {
  const savedFilter = useMemo(loadDirectorTopicSavedFilter, []);
  const [deptInput, setDeptInput] = useState('');
  const [dateFromInput, setDateFromInput] = useState('');
  const [dateToInput, setDateToInput] = useState('');
  const [pointValueInput, setPointValueInput] = useState(savedFilter.pointValueInput);
  const [deptName, setDeptName] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [pointValue, setPointValue] = useState<number | undefined>(parseNumberInput(savedFilter.pointValueInput));
  const [selectedDiagnosis, setSelectedDiagnosis] = useState('');
  const [exportChartKey, setExportChartKey] = useState('disease-rank');
  const [errorText, setErrorText] = useState('');
  const chartRefs = useRef<ChartRefMap>({});

  const overviewQuery = useQuery({
    queryKey: ['director-topic-overview', deptName, dateFrom, dateTo, pointValue],
    queryFn: () =>
      fetchDirectorTopicOverview({
        deptName: deptName || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        topN: 5,
        pointValue,
      }),
  });
  const deptQuery = useQuery({
    queryKey: ['dip-departments'],
    queryFn: fetchDipDepartments,
  });

  useEffect(() => {
    const first = overviewQuery.data?.diseases?.[0]?.diagnosis_code || '';
    if (!first) {
      setSelectedDiagnosis('');
      return;
    }
    const exists = overviewQuery.data?.diseases?.some((item) => item.diagnosis_code === selectedDiagnosis);
    if (!selectedDiagnosis || !exists) {
      setSelectedDiagnosis(first);
    }
  }, [overviewQuery.data?.diseases, selectedDiagnosis]);

  const detailQuery = useQuery({
    queryKey: ['director-topic-detail', selectedDiagnosis, deptName, dateFrom, dateTo, pointValue],
    queryFn: () =>
      fetchDirectorTopicDetail({
        diagnosisCode: selectedDiagnosis,
        deptName: deptName || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        pointValue,
        doctorMinCases: 5,
        detailTopN: 20,
      }),
    enabled: Boolean(selectedDiagnosis),
  });

  const pdfMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDiagnosis) return;
      const chartPayload = chartCatalog
        .map((item, idx) => {
          const chart = chartRefs.current[item.key]?.getEchartsInstance?.();
          if (!chart) return null;
          const imageBase64 = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' });
          return {
            chart_key: item.key,
            title: item.title,
            image_base64: imageBase64,
            order_no: idx + 1,
          };
        })
        .filter((item): item is NonNullable<typeof item> => Boolean(item));

      if (!chartPayload.length) {
        throw new Error('当前没有可导出的图表。');
      }

      await exportDirectorTopicPdf({
        diagnosisCode: selectedDiagnosis,
        deptName: deptName || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        pointValue,
        doctorMinCases: 5,
        charts: chartPayload,
      });
    },
    onError: (error: unknown) => {
      if (error instanceof Error) {
        setErrorText(error.message);
      } else {
        setErrorText('PDF导出失败。');
      }
    },
  });

  const chartCatalog = [
    { key: 'disease-rank', title: 'TOP5病种排名' },
    { key: 'overview-trend', title: '病种趋势监控' },
    { key: 'cost-structure', title: '费用结构环图' },
    { key: 'cost-ratio', title: '费用占比柱图' },
    { key: 'dip-waterfall', title: 'DIP模拟收支' },
    { key: 'dip-gauge', title: 'DIP入组率' },
    { key: 'doctor-bar', title: '医师次均费用对比' },
    { key: 'doctor-scatter', title: '医师住院日-结余散点' },
    { key: 'anomaly-category', title: '异常规则分布' },
    { key: 'anomaly-severity', title: '异常级别构成' },
    { key: 'detail-pareto', title: '明细TOP帕累托' },
  ];

  const onApplyFilter = () => {
    const point = parseNumberInput(pointValueInput);
    if (pointValueInput.trim() && point === undefined) {
      setErrorText('DIP点值需为大于0的数字。');
      return;
    }
    setDeptName(deptInput.trim());
    setDateFrom(dateFromInput.trim());
    setDateTo(dateToInput.trim());
    setPointValue(point);
    if (point !== undefined) {
      saveDirectorTopicSavedFilter({ pointValueInput: pointValueInput.trim() });
    }
    setErrorText('');
  };

  const onExportPng = () => {
    const chart = chartRefs.current[exportChartKey]?.getEchartsInstance?.();
    if (!chart) {
      setErrorText('请先等待图表加载完成后再导出PNG。');
      return;
    }
    const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' });
    downloadDataUrl(exportChartKey, url);
    setErrorText('');
  };

  const registerChartRef =
    (key: string) =>
    (ref: ReactECharts | null): void => {
      chartRefs.current[key] = ref;
    };

  const diseases = overviewQuery.data?.diseases ?? [];
  const trend = overviewQuery.data?.monthly_trend ?? [];
  const deptOptions = useMemo(() => {
    const options = deptQuery.data?.items ?? [];
    if (deptInput && !options.includes(deptInput)) {
      return [deptInput, ...options];
    }
    return options;
  }, [deptInput, deptQuery.data?.items]);
  const detail = detailQuery.data;
  const doctors = detail?.doctor_compare ?? [];
  const detailItems = detail?.detail_top_items ?? [];
  const anomalyCategories = detail?.anomaly_categories ?? [];
  const anomalySeverity = detail?.anomaly_severity ?? [];

  const diseaseRankOption = useMemo(
    () => ({
      tooltip: { trigger: 'axis' },
      grid: { left: 120, right: 20, top: 20, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: diseases.map((d) => d.diagnosis_code) },
      series: [{ type: 'bar', data: diseases.map((d) => d.case_count), itemStyle: { color: '#1f7f89' } }],
    }),
    [diseases],
  );

  const overviewTrendOption = useMemo(
    () => ({
      tooltip: { trigger: 'axis' },
      legend: { data: ['总费用', 'DIP模拟结余'] },
      grid: { left: 40, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: trend.map((x) => x.period) },
      yAxis: [{ type: 'value' }, { type: 'value' }],
      series: [
        { name: '总费用', type: 'line', smooth: true, data: trend.map((x) => x.total_cost) },
        { name: 'DIP模拟结余', type: 'bar', yAxisIndex: 1, data: trend.map((x) => x.dip_sim_balance) },
      ],
    }),
    [trend],
  );

  const costStructureOption = useMemo(
    () => ({
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['45%', '75%'],
          data: (detail?.cost_structure ?? []).map((x) => ({ name: x.name, value: x.value })),
        },
      ],
    }),
    [detail?.cost_structure],
  );

  const costRatioOption = useMemo(
    () => ({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: (detail?.cost_structure ?? []).map((x) => x.name), axisLabel: { rotate: 20 } },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: (detail?.cost_structure ?? []).map((x) => x.ratio), itemStyle: { color: '#2a8a95' } }],
    }),
    [detail?.cost_structure],
  );

  const dipWaterfallOption = useMemo(
    () => ({
      tooltip: { trigger: 'item' },
      xAxis: { type: 'category', data: ['模拟收入', '实际费用', '模拟结余'] },
      yAxis: { type: 'value' },
      series: [
        {
          type: 'bar',
          data: [
            detail?.dip_summary?.dip_sim_income ?? 0,
            -(detail?.total_cost ?? 0),
            detail?.dip_summary?.dip_sim_balance ?? 0,
          ],
          itemStyle: {
            color: (p: { dataIndex: number }) => (p.dataIndex === 1 ? '#d05b5b' : '#1d8a70'),
          },
        },
      ],
    }),
    [detail?.dip_summary?.dip_sim_balance, detail?.dip_summary?.dip_sim_income, detail?.total_cost],
  );

  const dipGaugeOption = useMemo(
    () => ({
      series: [
        {
          type: 'gauge',
          min: 0,
          max: 100,
          detail: { formatter: '{value}%' },
          data: [{ value: detail?.dip_summary?.grouped_rate ?? 0, name: '入组率' }],
        },
      ],
    }),
    [detail?.dip_summary?.grouped_rate],
  );

  const doctorBarOption = useMemo(
    () => ({
      tooltip: { trigger: 'axis' },
      grid: { left: 140, right: 20, top: 20, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: doctors.map((d) => d.doctor_name) },
      series: [{ type: 'bar', data: doctors.map((d) => d.avg_total_cost), itemStyle: { color: '#f7934c' } }],
    }),
    [doctors],
  );

  const doctorScatterOption = useMemo(
    () => ({
      tooltip: {
        formatter: (params: { data: [number, number, number, string] }) =>
          `${params.data[3]}<br/>平均住院日: ${params.data[0]}<br/>DIP模拟结余: ${params.data[1]}<br/>病例数: ${params.data[2]}`,
      },
      xAxis: { type: 'value', name: '平均住院日' },
      yAxis: { type: 'value', name: 'DIP模拟结余' },
      series: [
        {
          type: 'scatter',
          symbolSize: (value: [number, number, number, string]) => Math.max(10, Math.min(40, value[2] * 2)),
          data: doctors.map((d) => [d.avg_los, d.dip_sim_balance, d.case_count, d.doctor_name]),
          itemStyle: { color: '#3b78be' },
        },
      ],
    }),
    [doctors],
  );

  const anomalyCategoryOption = useMemo(
    () => ({
      color: [SEVERITY_COLORS.RED, SEVERITY_COLORS.ORANGE, SEVERITY_COLORS.YELLOW],
      tooltip: { trigger: 'axis' },
      legend: { data: ['RED', 'ORANGE', 'YELLOW'] },
      grid: { left: 40, right: 20, top: 40, bottom: 40 },
      xAxis: { type: 'category', data: anomalyCategories.map((x) => x.rule_name || x.rule_code), axisLabel: { rotate: 25 } },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'RED',
          type: 'bar',
          stack: 'total',
          itemStyle: { color: SEVERITY_COLORS.RED },
          data: anomalyCategories.map((x) => x.red_count),
        },
        {
          name: 'ORANGE',
          type: 'bar',
          stack: 'total',
          itemStyle: { color: SEVERITY_COLORS.ORANGE },
          data: anomalyCategories.map((x) => x.orange_count),
        },
        {
          name: 'YELLOW',
          type: 'bar',
          stack: 'total',
          itemStyle: { color: SEVERITY_COLORS.YELLOW },
          data: anomalyCategories.map((x) => x.yellow_count),
        },
      ],
    }),
    [anomalyCategories],
  );

  const anomalySeverityOption = useMemo(
    () => ({
      color: [SEVERITY_COLORS.RED, SEVERITY_COLORS.ORANGE, SEVERITY_COLORS.YELLOW],
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['40%', '72%'],
          data: anomalySeverity.map((x) => ({
            name: x.severity,
            value: x.count,
            itemStyle: { color: SEVERITY_COLORS[x.severity as keyof typeof SEVERITY_COLORS] || '#9e9e9e' },
          })),
        },
      ],
    }),
    [anomalySeverity],
  );

  const detailParetoOption = useMemo(() => {
    const sorted = detailItems;
    const sum = sorted.reduce((acc, item) => acc + item.total_amount, 0);
    let running = 0;
    const cumulative = sorted.map((x) => {
      running += x.total_amount;
      return sum > 0 ? Number(((running / sum) * 100).toFixed(2)) : 0;
    });
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['金额', '累计占比'] },
      grid: { left: 40, right: 50, top: 40, bottom: 40 },
      xAxis: { type: 'category', data: sorted.map((x) => x.item_name), axisLabel: { rotate: 25 } },
      yAxis: [{ type: 'value' }, { type: 'value', min: 0, max: 100 }],
      series: [
        { name: '金额', type: 'bar', data: sorted.map((x) => x.total_amount), itemStyle: { color: '#1f7f89' } },
        { name: '累计占比', type: 'line', yAxisIndex: 1, data: cumulative, smooth: true },
      ],
    };
  }, [detailItems]);

  return (
    <section className="dashboard-grid">
      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>科主任专题（高密度分析版）</h2>
          <p>TOP5病种、费用结构、DIP模拟、医师对比、异常分析全模块图表化。</p>
        </header>
        <div className="issue-toolbar">
          <label className="field field--compact">
            <span>科室</span>
            <select value={deptInput} onChange={(e) => setDeptInput(e.target.value)}>
              <option value="">全部科室</option>
              {deptOptions.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </label>
          <label className="field field--compact">
            <span>开始日期</span>
            <input type="date" value={dateFromInput} onChange={(e) => setDateFromInput(e.target.value)} />
          </label>
          <label className="field field--compact">
            <span>结束日期</span>
            <input type="date" value={dateToInput} onChange={(e) => setDateToInput(e.target.value)} />
          </label>
          <label className="field field--compact">
            <span>DIP点值</span>
            <input value={pointValueInput} onChange={(e) => setPointValueInput(e.target.value)} placeholder="建议 5~6" />
          </label>
          <button className="btn-secondary" onClick={onApplyFilter} type="button">
            应用筛选
          </button>
          <label className="field field--compact">
            <span>PNG图表</span>
            <select value={exportChartKey} onChange={(e) => setExportChartKey(e.target.value)}>
              {chartCatalog.map((x) => (
                <option key={x.key} value={x.key}>
                  {x.title}
                </option>
              ))}
            </select>
          </label>
          <button className="btn-secondary" onClick={onExportPng} type="button">
            导出PNG
          </button>
          <button className="btn-secondary" onClick={() => pdfMutation.mutate()} type="button" disabled={pdfMutation.isPending}>
            {pdfMutation.isPending ? 'PDF导出中...' : '导出PDF（病种报告）'}
          </button>
        </div>
        {errorText ? <p className="error-text">{errorText}</p> : null}
      </article>

      <div className="metrics-row">
        <div className="metric-card">
          <p className="metric-label">病例总数</p>
          <p className="metric-value">{overviewQuery.data?.summary.total_cases ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">总费用</p>
          <p className="metric-value">{(overviewQuery.data?.summary.total_cost ?? 0).toFixed(2)}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">DIP模拟收入</p>
          <p className="metric-value">{(overviewQuery.data?.summary.dip_sim_income ?? 0).toFixed(2)}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">DIP模拟结余</p>
          <p className="metric-value">{(overviewQuery.data?.summary.dip_sim_balance ?? 0).toFixed(2)}</p>
        </div>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>TOP5病种与趋势</h2>
          <p>左侧排名，右侧月度总费用与模拟结余趋势。</p>
        </header>
        <div className="import-layout">
          <ReactECharts ref={registerChartRef('disease-rank')} option={diseaseRankOption} style={{ height: 320 }} />
          <ReactECharts ref={registerChartRef('overview-trend')} option={overviewTrendOption} style={{ height: 320 }} />
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>病种编码</th>
                <th>病种名称</th>
                <th>病例数</th>
                <th>次均费用</th>
                <th>DIP模拟结余</th>
              </tr>
            </thead>
            <tbody>
              {diseases.map((item) => (
                <tr key={item.diagnosis_code} onClick={() => setSelectedDiagnosis(item.diagnosis_code)}>
                  <td>{item.diagnosis_code}</td>
                  <td>{item.diagnosis_name || '-'}</td>
                  <td>{item.case_count}</td>
                  <td>{item.avg_total_cost.toFixed(2)}</td>
                  <td>{item.dip_sim_balance.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>病种详情：{selectedDiagnosis || '-'}</h2>
          <p>{detail?.diagnosis_name || '请选择病种查看'} </p>
        </header>
        <div className="import-layout">
          <ReactECharts ref={registerChartRef('cost-structure')} option={costStructureOption} style={{ height: 280 }} />
          <ReactECharts ref={registerChartRef('cost-ratio')} option={costRatioOption} style={{ height: 280 }} />
        </div>
        <div className="import-layout">
          <ReactECharts ref={registerChartRef('dip-waterfall')} option={dipWaterfallOption} style={{ height: 280 }} />
          <ReactECharts ref={registerChartRef('dip-gauge')} option={dipGaugeOption} style={{ height: 280 }} />
        </div>
        <div className="import-layout">
          <ReactECharts ref={registerChartRef('doctor-bar')} option={doctorBarOption} style={{ height: 320 }} />
          <ReactECharts ref={registerChartRef('doctor-scatter')} option={doctorScatterOption} style={{ height: 320 }} />
        </div>
        <div className="import-layout">
          <ReactECharts ref={registerChartRef('anomaly-category')} option={anomalyCategoryOption} style={{ height: 320 }} />
          <ReactECharts ref={registerChartRef('anomaly-severity')} option={anomalySeverityOption} style={{ height: 320 }} />
        </div>
        <ReactECharts ref={registerChartRef('detail-pareto')} option={detailParetoOption} style={{ height: 320 }} />
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>医师对比明细</h2>
          <p>病例数门槛：5</p>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>医师</th>
                <th>病例数</th>
                <th>次均费用</th>
                <th>平均住院日</th>
                <th>非草药药占比%</th>
                <th>耗占比%</th>
                <th>DIP模拟结余</th>
              </tr>
            </thead>
            <tbody>
              {doctors.map((item) => (
                <tr key={item.doctor_name}>
                  <td>{item.doctor_name}</td>
                  <td>{item.case_count}</td>
                  <td>{item.avg_total_cost.toFixed(2)}</td>
                  <td>{item.avg_los.toFixed(2)}</td>
                  <td>{item.avg_drug_ratio.toFixed(2)}</td>
                  <td>{item.avg_material_ratio.toFixed(2)}</td>
                  <td>{item.dip_sim_balance.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>明细TOP项目</h2>
          <p>用于耗材/药品等异常高金额项目定位。</p>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>项目编码</th>
                <th>项目名称</th>
                <th>总金额</th>
                <th>病例数</th>
                <th>占比%</th>
              </tr>
            </thead>
            <tbody>
              {detailItems.map((item, idx) => (
                <tr key={`${item.item_code || 'NA'}-${idx}`}>
                  <td>{item.item_code || '-'}</td>
                  <td>{item.item_name}</td>
                  <td>{item.total_amount.toFixed(2)}</td>
                  <td>{item.case_count}</td>
                  <td>{item.ratio.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
