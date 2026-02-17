import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import ReactECharts from 'echarts-for-react';
import {
  fetchClinicalTop,
  fetchCostStructure,
  fetchCostTrend,
  fetchDiseasePriority,
  fetchHealth,
  fetchQualityOverview,
} from '../lib/api';
import { MetricCard } from '../components/MetricCard';

export function DashboardPage() {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  });
  const qualityQuery = useQuery({
    queryKey: ['quality-overview'],
    queryFn: fetchQualityOverview,
  });
  const costStructureQuery = useQuery({
    queryKey: ['cost-structure'],
    queryFn: () => fetchCostStructure(),
  });
  const costTrendQuery = useQuery({
    queryKey: ['cost-trend'],
    queryFn: () => fetchCostTrend(),
  });
  const clinicalTopQuery = useQuery({
    queryKey: ['clinical-top'],
    queryFn: () => fetchClinicalTop({ limit: 8 }),
  });
  const priorityQuery = useQuery({
    queryKey: ['disease-priority-top'],
    queryFn: () => fetchDiseasePriority({ limit: 8 }),
  });

  const costOption = useMemo(
    () => ({
      color: ['#0f6f77', '#f7934c', '#53b55a', '#2289c9', '#c74b4b', '#5e8f48', '#2d9a8f'],
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['45%', '72%'],
          label: { color: '#253238' },
          data: costStructureQuery.data?.items ?? [],
        },
      ],
    }),
    [costStructureQuery.data?.items],
  );

  const trendOption = useMemo(
    () => ({
      color: ['#0f6f77', '#ef5f5f'],
      tooltip: { trigger: 'axis' },
      grid: { left: 12, right: 12, top: 28, bottom: 12, containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: (costTrendQuery.data?.items ?? []).map((x) => x.period),
      },
      yAxis: { type: 'value' },
      series: [
        {
          name: '次均费用',
          type: 'line',
          smooth: true,
          data: (costTrendQuery.data?.items ?? []).map((x) => x.avg_cost),
          areaStyle: { opacity: 0.12 },
        },
        {
          name: '非草药药占比',
          type: 'line',
          smooth: true,
          data: (costTrendQuery.data?.items ?? []).map((x) => x.avg_drug_ratio),
        },
      ],
    }),
    [costTrendQuery.data?.items],
  );

  return (
    <section className="dashboard-grid">
      <motion.div
        className="status-ribbon"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <span>系统联通状态</span>
        <strong>{healthQuery.data?.status === 'ok' ? '正常' : '待检查'}</strong>
      </motion.div>

      <motion.div
        className="metrics-row"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <MetricCard
          label="病案总记录"
          value={String(qualityQuery.data?.case_total ?? 0)}
          trend="当前入库病例总数"
        />
        <MetricCard
          label="主键完整率"
          value={`${qualityQuery.data?.pk_complete_rate ?? 0}%`}
          trend="住院号完整性"
          tone="good"
        />
        <MetricCard
          label="孤儿费用率"
          value={`${qualityQuery.data?.orphan_fee_record_rate ?? 0}%`}
          trend="费用明细无病案匹配"
          tone="alert"
        />
        <MetricCard
          label="导入失败率"
          value={`${qualityQuery.data?.import_failure_rate ?? 0}%`}
          trend={`告警 ${qualityQuery.data?.warning_issue_total ?? 0} / 错误 ${
            qualityQuery.data?.error_issue_total ?? 0
          }`}
        />
      </motion.div>

      <motion.article
        className="panel panel--emphasis"
        initial={{ opacity: 0, x: -18 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1, duration: 0.45 }}
      >
        <header className="panel-head">
          <h2>费用结构快照</h2>
          <p>病种聚合口径（最近30天）</p>
        </header>
        <ReactECharts option={costOption} style={{ height: 280 }} />
      </motion.article>

      <motion.article
        className="panel panel--wide"
        initial={{ opacity: 0, x: 18 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.15, duration: 0.45 }}
      >
        <header className="panel-head">
          <h2>趋势监控</h2>
          <p>次均费用与非草药药占比波动</p>
        </header>
        <ReactECharts option={trendOption} style={{ height: 280 }} />
      </motion.article>

      <motion.article
        className="panel panel--wide"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.45 }}
      >
        <header className="panel-head">
          <h2>临床特征画像 TOP</h2>
          <p>主诊断分布（按病例数）</p>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>诊断编码</th>
                <th>诊断名称</th>
                <th>病例数</th>
              </tr>
            </thead>
            <tbody>
              {clinicalTopQuery.data?.items.map((item) => (
                <tr key={item.diagnosis_code}>
                  <td>{item.diagnosis_code}</td>
                  <td>{item.diagnosis_name || '-'}</td>
                  <td>{item.case_count}</td>
                </tr>
              ))}
              {!clinicalTopQuery.data?.items.length ? (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center' }}>
                    暂无数据
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </motion.article>

      <motion.article
        className="panel panel--wide"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.24, duration: 0.45 }}
      >
        <header className="panel-head">
          <h2>病种优先级快照</h2>
          <p>综合评分 Top8（进入病种筛选页查看全量）</p>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>诊断编码</th>
                <th>病例数</th>
                <th>次均费用</th>
                <th>平均住院日</th>
                <th>评分</th>
              </tr>
            </thead>
            <tbody>
              {priorityQuery.data?.items.map((item) => (
                <tr key={item.diagnosis_code}>
                  <td>{item.diagnosis_code}</td>
                  <td>{item.case_count}</td>
                  <td>{item.avg_total_cost.toFixed(2)}</td>
                  <td>{item.avg_los.toFixed(1)}</td>
                  <td>{item.score.toFixed(2)}</td>
                </tr>
              ))}
              {!priorityQuery.data?.items.length ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center' }}>
                    暂无数据
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </motion.article>
    </section>
  );
}
