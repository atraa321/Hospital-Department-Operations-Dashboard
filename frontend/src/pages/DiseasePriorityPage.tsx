import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchDiseasePriority } from '../lib/api';

type SortKey = 'score' | 'case_count' | 'avg_total_cost' | 'avg_los';

export function DiseasePriorityPage() {
  const [keyword, setKeyword] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [desc, setDesc] = useState(true);

  const priorityQuery = useQuery({
    queryKey: ['disease-priority-all'],
    queryFn: () => fetchDiseasePriority({ limit: 200 }),
  });

  const rows = useMemo(() => {
    const key = keyword.trim().toUpperCase();
    const raw = priorityQuery.data?.items ?? [];
    const filtered = raw.filter((item) => {
      if (item.score < minScore) {
        return false;
      }
      if (!key) {
        return true;
      }
      const text = `${item.diagnosis_code} ${item.diagnosis_name ?? ''}`.toUpperCase();
      return text.includes(key);
    });
    return filtered.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      return desc ? Number(bv) - Number(av) : Number(av) - Number(bv);
    });
  }, [priorityQuery.data?.items, keyword, minScore, sortKey, desc]);

  const layered = useMemo(() => {
    let major = 0;
    let key = 0;
    let watch = 0;
    rows.forEach((item) => {
      if (item.layer === '主力病种') {
        major += 1;
      } else if (item.layer === '重点病种') {
        key += 1;
      } else {
        watch += 1;
      }
    });
    return { major, key, watch };
  }, [rows]);

  return (
    <section className="dashboard-grid">
      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>病种优先级筛选</h2>
          <p>按评分规则自动分层：主力病种 / 重点病种 / 常规监测</p>
        </header>
        <div className="issue-toolbar">
          <label className="field field--compact">
            <span>关键词</span>
            <input
              placeholder="诊断编码/名称"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
          </label>
          <label className="field field--compact">
            <span>最低评分</span>
            <input
              max={100}
              min={0}
              type="number"
              value={minScore}
              onChange={(event) => setMinScore(Math.max(0, Math.min(100, Number(event.target.value) || 0)))}
            />
          </label>
          <label className="field field--compact">
            <span>排序字段</span>
            <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
              <option value="score">综合评分</option>
              <option value="case_count">病例数</option>
              <option value="avg_total_cost">次均费用</option>
              <option value="avg_los">平均住院日</option>
            </select>
          </label>
          <button className="btn-secondary" onClick={() => setDesc((v) => !v)} type="button">
            {desc ? '降序' : '升序'}
          </button>
        </div>
      </article>

      <div className="metrics-row">
        <div className="metric-card metric-card--good">
          <p className="metric-label">主力病种 (&gt;=75)</p>
          <p className="metric-value">{layered.major}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">重点病种 (60-74)</p>
          <p className="metric-value">{layered.key}</p>
        </div>
        <div className="metric-card metric-card--alert">
          <p className="metric-label">常规监测 (&lt;60)</p>
          <p className="metric-value">{layered.watch}</p>
        </div>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>病种分层清单</h2>
          <p>共 {rows.length} 条</p>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>诊断编码</th>
                <th>诊断名称</th>
                <th>病例数</th>
                <th>次均费用</th>
                <th>平均住院日</th>
                <th>综合评分</th>
                <th>分层</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => {
                return (
                  <tr key={item.diagnosis_code}>
                    <td>{item.diagnosis_code}</td>
                    <td>{item.diagnosis_name || '-'}</td>
                    <td>{item.case_count}</td>
                    <td>{item.avg_total_cost.toFixed(2)}</td>
                    <td>{item.avg_los.toFixed(1)}</td>
                    <td>{item.score.toFixed(2)}</td>
                    <td>{item.layer}</td>
                  </tr>
                );
              })}
              {!rows.length ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center' }}>
                    暂无符合条件的数据
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
