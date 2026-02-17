import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchDipDepartments, fetchDipStats } from '../lib/api';

type MultiplierLevel = '' | 'LOW' | 'NORMAL' | 'HIGH' | 'ULTRA_HIGH' | 'UNKNOWN';
type DipStatsSavedFilter = {
  pointMin: number;
  pointMax: number;
  deptName: string;
};

const DIP_STATS_FILTER_KEY = 'dip_stats_filters_v1';
const DIP_POINT_DEFAULT_MIN = 5;
const DIP_POINT_DEFAULT_MAX = 6;

function loadDipStatsSavedFilter(): DipStatsSavedFilter {
  if (typeof window === 'undefined') {
    return { pointMin: DIP_POINT_DEFAULT_MIN, pointMax: DIP_POINT_DEFAULT_MAX, deptName: '' };
  }
  const raw = window.localStorage.getItem(DIP_STATS_FILTER_KEY);
  if (!raw) {
    return { pointMin: DIP_POINT_DEFAULT_MIN, pointMax: DIP_POINT_DEFAULT_MAX, deptName: '' };
  }
  try {
    const parsed = JSON.parse(raw) as Partial<DipStatsSavedFilter>;
    const pointMin = Number(parsed.pointMin);
    const pointMax = Number(parsed.pointMax);
    const deptName = String(parsed.deptName ?? '').trim();
    if (!Number.isFinite(pointMin) || pointMin <= 0 || !Number.isFinite(pointMax) || pointMax <= 0) {
      return { pointMin: DIP_POINT_DEFAULT_MIN, pointMax: DIP_POINT_DEFAULT_MAX, deptName: '' };
    }
    return { pointMin, pointMax, deptName };
  } catch {
    return { pointMin: DIP_POINT_DEFAULT_MIN, pointMax: DIP_POINT_DEFAULT_MAX, deptName: '' };
  }
}

function saveDipStatsFilter(payload: DipStatsSavedFilter) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(DIP_STATS_FILTER_KEY, JSON.stringify(payload));
}

function levelLabel(level: string) {
  if (level === 'LOW') return '低倍率(<50%)';
  if (level === 'NORMAL') return '正常倍率(50%-110%)';
  if (level === 'HIGH') return '高倍率(110%-200%)';
  if (level === 'ULTRA_HIGH') return '超高倍率(>200%)';
  return '未分层';
}

export function DipStatsPage() {
  const savedFilter = useMemo(loadDipStatsSavedFilter, []);
  const [page, setPage] = useState(1);
  const [multiplierLevel, setMultiplierLevel] = useState<MultiplierLevel>('');
  const [deptInput, setDeptInput] = useState(savedFilter.deptName);
  const [deptName, setDeptName] = useState(savedFilter.deptName);
  const [pointMinInput, setPointMinInput] = useState(savedFilter.pointMin.toString());
  const [pointMaxInput, setPointMaxInput] = useState(savedFilter.pointMax.toString());
  const [pointMin, setPointMin] = useState(savedFilter.pointMin);
  const [pointMax, setPointMax] = useState(savedFilter.pointMax);
  const [ratioMinInput, setRatioMinInput] = useState('');
  const [ratioMaxInput, setRatioMaxInput] = useState('');
  const [ratioMinPct, setRatioMinPct] = useState<number | undefined>(undefined);
  const [ratioMaxPct, setRatioMaxPct] = useState<number | undefined>(undefined);
  const [ungroupedOnly, setUngroupedOnly] = useState(false);
  const [errorText, setErrorText] = useState('');

  const statsQuery = useQuery({
    queryKey: ['dip-stats', page, multiplierLevel, pointMin, pointMax, deptName, ratioMinPct, ratioMaxPct, ungroupedOnly],
    queryFn: () =>
      fetchDipStats({
        page,
        pageSize: 20,
        multiplierLevel,
        pointValueMin: pointMin,
        pointValueMax: pointMax,
        deptName,
        ratioMinPct,
        ratioMaxPct,
        ungroupedOnly,
      }),
  });
  const deptQuery = useQuery({
    queryKey: ['dip-departments'],
    queryFn: fetchDipDepartments,
  });

  const deptOptions = useMemo(() => {
    const options = deptQuery.data?.items ?? [];
    if (deptInput && !options.includes(deptInput)) {
      return [deptInput, ...options];
    }
    return options;
  }, [deptQuery.data?.items, deptInput]);

  const onApplyPointRange = () => {
    const min = Number(pointMinInput);
    const max = Number(pointMaxInput);
    if (!Number.isFinite(min) || !Number.isFinite(max) || min <= 0 || max <= 0) {
      setErrorText('点值区间需为大于0的数字。');
      return;
    }

    const ratioMin = ratioMinInput.trim() === '' ? undefined : Number(ratioMinInput);
    const ratioMax = ratioMaxInput.trim() === '' ? undefined : Number(ratioMaxInput);
    if (
      (ratioMin !== undefined && (!Number.isFinite(ratioMin) || ratioMin < 0)) ||
      (ratioMax !== undefined && (!Number.isFinite(ratioMax) || ratioMax < 0))
    ) {
      setErrorText('倍率区间需为大于等于0的数字。');
      return;
    }

    setErrorText('');
    setPage(1);
    setPointMin(min);
    setPointMax(max);
    setDeptName(deptInput.trim());
    setRatioMinPct(ratioMin);
    setRatioMaxPct(ratioMax);
    saveDipStatsFilter({
      pointMin: min,
      pointMax: max,
      deptName: deptInput.trim(),
    });
  };

  const summary = statsQuery.data?.summary;
  const totalPages = useMemo(
    () => Math.max(1, Math.ceil((statsQuery.data?.total ?? 0) / (statsQuery.data?.page_size ?? 20))),
    [statsQuery.data],
  );

  return (
    <section className="dashboard-grid">
      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>DIP分组统计</h2>
          <p>按点值区间计算支付区间，并按住院总费用占DIP支付比例进行倍率分层。</p>
        </header>
        <div className="issue-toolbar">
          <label className="field field--compact">
            <span>点值下限</span>
            <input
              type="number"
              step="0.01"
              value={pointMinInput}
              onChange={(event) => setPointMinInput(event.target.value)}
            />
          </label>
          <label className="field field--compact">
            <span>点值上限</span>
            <input
              type="number"
              step="0.01"
              value={pointMaxInput}
              onChange={(event) => setPointMaxInput(event.target.value)}
            />
          </label>
          <label className="field field--compact">
            <span>倍率筛选</span>
            <select
              value={multiplierLevel}
              onChange={(event) => {
                setPage(1);
                setMultiplierLevel(event.target.value as MultiplierLevel);
              }}
            >
              <option value="">全部</option>
              <option value="LOW">低倍率</option>
              <option value="NORMAL">正常倍率</option>
              <option value="HIGH">高倍率</option>
              <option value="ULTRA_HIGH">超高倍率</option>
              <option value="UNKNOWN">未分层</option>
            </select>
          </label>
          <label className="field field--compact">
            <span>科室筛选</span>
            <select value={deptInput} onChange={(event) => setDeptInput(event.target.value)}>
              <option value="">全部科室</option>
              {deptOptions.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </label>
          <label className="field field--compact">
            <span>倍率下限(%)</span>
            <input
              type="number"
              step="0.01"
              placeholder="可空"
              value={ratioMinInput}
              onChange={(event) => setRatioMinInput(event.target.value)}
            />
          </label>
          <label className="field field--compact">
            <span>倍率上限(%)</span>
            <input
              type="number"
              step="0.01"
              placeholder="可空"
              value={ratioMaxInput}
              onChange={(event) => setRatioMaxInput(event.target.value)}
            />
          </label>
          <label className="field field--compact">
            <span>未入组筛选</span>
            <select
              value={ungroupedOnly ? 'YES' : 'NO'}
              onChange={(event) => {
                setPage(1);
                setUngroupedOnly(event.target.value === 'YES');
              }}
            >
              <option value="NO">全部</option>
              <option value="YES">仅未入组</option>
            </select>
          </label>
          <button className="btn-secondary" onClick={onApplyPointRange} type="button">
            应用筛选
          </button>
        </div>
        {errorText ? <p className="error-text">{errorText}</p> : null}
      </article>

      <div className="metrics-row">
        <div className="metric-card">
          <p className="metric-label">病例总数</p>
          <p className="metric-value">{summary?.total_cases ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">已入组</p>
          <p className="metric-value">{summary?.grouped_cases ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">支付区间总额</p>
          <p className="metric-value">
            {(summary?.expected_pay_min_total ?? 0).toFixed(2)} ~ {(summary?.expected_pay_max_total ?? 0).toFixed(2)}
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">当前点值区间</p>
          <p className="metric-value">
            {summary?.point_value_min ?? pointMin} ~ {summary?.point_value_max ?? pointMax}
          </p>
        </div>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>倍率分层统计</h2>
          <p>
            低倍率 {summary?.low_count ?? 0} | 正常倍率 {summary?.normal_count ?? 0} | 高倍率 {summary?.high_count ?? 0} |
            超高倍率 {summary?.ultra_high_count ?? 0} | 未分层 {summary?.unknown_count ?? 0}
          </p>
        </header>
        <div className="table-wrap issue-table">
          <table>
            <thead>
              <tr>
                <th>住院号</th>
                <th>患者</th>
                <th>科室</th>
                <th>主诊断</th>
                <th>DIP组</th>
                <th>入组状态</th>
                <th>入组分值</th>
                <th>DIP付费区间</th>
                <th>住院总费用</th>
                <th>费用占比</th>
                <th>倍率分层</th>
              </tr>
            </thead>
            <tbody>
              {statsQuery.data?.items.map((item) => (
                <tr key={item.patient_id}>
                  <td>{item.patient_id}</td>
                  <td>{item.patient_name || '-'}</td>
                  <td>{item.dept_name || '-'}</td>
                  <td title={item.main_diagnosis_name || ''}>{item.main_diagnosis_code || '-'}</td>
                  <td>{item.dip_code || '-'}</td>
                  <td>{item.dip_status}</td>
                  <td>{item.dip_weight_score?.toFixed(4) || '-'}</td>
                  <td>{item.payment_low !== null ? `${item.payment_low?.toFixed(2)} ~ ${item.payment_high?.toFixed(2)}` : '-'}</td>
                  <td>{item.total_cost.toFixed(2)}</td>
                  <td>{item.cost_ratio_pct !== null ? `${item.cost_ratio_pct.toFixed(2)}%` : '-'}</td>
                  <td>
                    <span className={`status-badge multiplier-${item.multiplier_level.toLowerCase()}`}>
                      {levelLabel(item.multiplier_level)}
                    </span>
                  </td>
                </tr>
              ))}
              {!statsQuery.data?.items.length ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: 'center' }}>
                    当前筛选下暂无数据
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <div className="pager-row">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} type="button">
            上一页
          </button>
          <span>
            第 {page}/{totalPages} 页，共 {statsQuery.data?.total ?? 0} 条
          </span>
          <button
            className="btn-secondary"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            type="button"
          >
            下一页
          </button>
        </div>
      </article>
    </section>
  );
}
