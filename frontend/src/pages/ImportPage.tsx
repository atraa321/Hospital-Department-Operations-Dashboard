import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  cancelImportBatch,
  clearCaseCostImportData,
  createCaseHomeImportBatch,
  createImportBatch,
  downloadCaseCostBackup,
  downloadImportIssues,
  fetchImportBatches,
  fetchImportIssues,
  restoreCaseCostImportData,
  type ImportBatch,
  type ImportType,
} from '../lib/api';

const importTypeOptions: { label: string; value: ImportType }[] = [
  { label: '病案出院数据', value: 'CASE_INFO' },
  { label: '费用汇总数据', value: 'COST_SUMMARY' },
  { label: '费用明细数据', value: 'COST_DETAIL' },
];

type UploadState = {
  kind: 'case-home' | 'operations';
  fileName: string;
  progress: number;
  phase: 'uploading' | 'queueing';
};

function isActiveBatchStatus(status: string) {
  return ['QUEUED', 'RUNNING', 'PENDING'].includes(status);
}

function statusText(status: string) {
  switch (status) {
    case 'QUEUED':
      return '排队中';
    case 'RUNNING':
      return '处理中';
    case 'PENDING':
      return '准备中';
    case 'SUCCESS':
      return '已完成';
    case 'FAILED':
      return '失败';
    case 'CANCELED':
      return '已取消';
    default:
      return status;
  }
}

function formatDateTime(value: string | null) {
  if (!value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString('zh-CN', { hour12: false });
}

function upsertBatchList(items: ImportBatch[] | undefined, nextBatch: ImportBatch) {
  const current = items ?? [];
  const filtered = current.filter((item) => item.batch_id !== nextBatch.batch_id);
  return [nextBatch, ...filtered].slice(0, 20);
}

export function ImportPage() {
  const [importType, setImportType] = useState<ImportType>('CASE_INFO');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [caseHomeSourceFile, setCaseHomeSourceFile] = useState<File | null>(null);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [selectedBatchId, setSelectedBatchId] = useState('');
  const [issuePage, setIssuePage] = useState(1);
  const [issueSeverity, setIssueSeverity] = useState('');
  const [issueCode, setIssueCode] = useState('');
  const [errorText, setErrorText] = useState('');
  const [caseHomeErrorText, setCaseHomeErrorText] = useState('');
  const [maintenanceText, setMaintenanceText] = useState('');
  const [queueNotice, setQueueNotice] = useState('');
  const [uploadState, setUploadState] = useState<UploadState | null>(null);
  const queryClient = useQueryClient();
  const batchStatusRef = useRef<Record<string, string>>({});

  const importsQuery = useQuery({
    queryKey: ['imports'],
    queryFn: () => fetchImportBatches(20),
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      return items.some((item) => isActiveBatchStatus(item.status)) ? 2500 : 10000;
    },
    refetchIntervalInBackground: true,
  });

  const selectedBatch = useMemo(
    () => (importsQuery.data ?? []).find((item) => item.batch_id === selectedBatchId) ?? null,
    [importsQuery.data, selectedBatchId],
  );

  const issuesQuery = useQuery({
    queryKey: ['import-issues', selectedBatchId, issuePage, issueSeverity, issueCode],
    queryFn: () =>
      fetchImportIssues({
        batchId: selectedBatchId,
        page: issuePage,
        pageSize: 10,
        severity: issueSeverity || undefined,
        errorCode: issueCode || undefined,
      }),
    enabled: Boolean(selectedBatchId),
    refetchInterval:
      selectedBatch && isActiveBatchStatus(selectedBatch.status)
        ? 3000
        : false,
  });

  const activeBatch = useMemo(() => {
    const items = importsQuery.data ?? [];
    return items.find((item) => isActiveBatchStatus(item.status)) ?? items[0] ?? null;
  }, [importsQuery.data]);

  const queueSummary = useMemo(() => {
    const items = importsQuery.data ?? [];
    const queued = items.filter((item) => item.status === 'QUEUED').length;
    const running = items.filter((item) => item.status === 'RUNNING').length;
    const failed = items.filter((item) => item.status === 'FAILED').length;
    const success = items.filter((item) => item.status === 'SUCCESS').length;
    return { queued, running, failed, success };
  }, [importsQuery.data]);

  useEffect(() => {
    if (!importsQuery.data?.length) {
      return;
    }
    const active = importsQuery.data.find((item) => isActiveBatchStatus(item.status));
    if (active && active.batch_id !== selectedBatchId) {
      setSelectedBatchId(active.batch_id);
      setIssuePage(1);
      return;
    }
    if (!selectedBatchId) {
      setSelectedBatchId(importsQuery.data[0].batch_id);
      setIssuePage(1);
    }
  }, [importsQuery.data, selectedBatchId]);

  useEffect(() => {
    const items = importsQuery.data ?? [];
    const previous = batchStatusRef.current;
    const next: Record<string, string> = {};

    for (const item of items) {
      next[item.batch_id] = item.status;
      const previousStatus = previous[item.batch_id];
      if (previousStatus && previousStatus !== item.status) {
        if (item.status === 'SUCCESS') {
          setQueueNotice(`批次 ${item.batch_id.slice(0, 8)} 已导入完成，数据已在后台更新。`);
        } else if (item.status === 'FAILED') {
          setQueueNotice(`批次 ${item.batch_id.slice(0, 8)} 导入失败，请查看错误明细。`);
        } else if (item.status === 'CANCELED') {
          setQueueNotice(`批次 ${item.batch_id.slice(0, 8)} 已取消。`);
        }
      }
    }

    batchStatusRef.current = next;
  }, [importsQuery.data]);

  const uploadMutation = useMutation({
    mutationFn: (payload: { importType: ImportType; file: File }) =>
      createImportBatch({
        importType: payload.importType,
        file: payload.file,
        onUploadProgress: (progress) => {
          setUploadState({
            kind: 'operations',
            fileName: payload.file.name,
            progress,
            phase: progress >= 100 ? 'queueing' : 'uploading',
          });
        },
      }),
    onSuccess: (result) => {
      setSelectedFile(null);
      setErrorText('');
      setUploadState(null);
      setQueueNotice(`文件已进入后台队列，批次号 ${result.batch.batch_id.slice(0, 8)}，你可以继续操作页面。`);
      setSelectedBatchId(result.batch.batch_id);
      setIssuePage(1);
      queryClient.setQueryData<ImportBatch[]>(['imports'], (items) => upsertBatchList(items, result.batch));
      queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
    onError: (error: unknown) => {
      setUploadState(null);
      setErrorText(error instanceof Error ? error.message : '导入失败，请检查文件格式。');
    },
  });

  const caseHomeUploadMutation = useMutation({
    mutationFn: (payload: { sourceFile: File }) =>
      createCaseHomeImportBatch({
        sourceFile: payload.sourceFile,
        onUploadProgress: (progress) => {
          setUploadState({
            kind: 'case-home',
            fileName: payload.sourceFile.name,
            progress,
            phase: progress >= 100 ? 'queueing' : 'uploading',
          });
        },
      }),
    onSuccess: (result) => {
      setCaseHomeSourceFile(null);
      setCaseHomeErrorText('');
      setUploadState(null);
      setQueueNotice(`病案首页已进入后台队列，批次号 ${result.batch.batch_id.slice(0, 8)}，无需停留等待。`);
      setSelectedBatchId(result.batch.batch_id);
      setIssuePage(1);
      queryClient.setQueryData<ImportBatch[]>(['imports'], (items) => upsertBatchList(items, result.batch));
      queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
    onError: (error: unknown) => {
      setUploadState(null);
      setCaseHomeErrorText(error instanceof Error ? error.message : '病案首页导入失败。');
    },
  });

  const backupMutation = useMutation({
    mutationFn: downloadCaseCostBackup,
    onSuccess: () => setMaintenanceText('备份文件已生成并下载。'),
    onError: () => setMaintenanceText('备份失败，请检查后端服务或数据权限。'),
  });

  const clearMutation = useMutation({
    mutationFn: clearCaseCostImportData,
    onSuccess: (result) => {
      setMaintenanceText(
        `已清除：病案 ${result.deleted_case_info} 条，费用明细 ${result.deleted_cost_detail} 条，导入批次 ${result.deleted_import_batch} 条。`,
      );
      queryClient.invalidateQueries({ queryKey: ['imports'] });
      queryClient.invalidateQueries({ queryKey: ['import-issues'] });
    },
    onError: () => setMaintenanceText('清除失败，请确认口令与权限。'),
  });

  const restoreMutation = useMutation({
    mutationFn: restoreCaseCostImportData,
    onSuccess: (result) => {
      setRestoreFile(null);
      setMaintenanceText(
        `恢复完成：病案 ${result.restored_case_info} 条，费用明细 ${result.restored_cost_detail} 条，导入批次 ${result.restored_import_batch} 条。`,
      );
      queryClient.invalidateQueries({ queryKey: ['imports'] });
      queryClient.invalidateQueries({ queryKey: ['import-issues'] });
    },
    onError: () => setMaintenanceText('恢复失败，请检查备份文件格式、口令和账号权限。'),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelImportBatch,
    onSuccess: (result) => {
      setQueueNotice(`批次 ${result.batch.batch_id.slice(0, 8)} 已提交取消请求。`);
      queryClient.setQueryData<ImportBatch[]>(['imports'], (items) => upsertBatchList(items, result.batch));
      queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
  });

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setErrorText('请先选择导入文件。');
      return;
    }
    setQueueNotice('');
    setErrorText('');
    uploadMutation.mutate({ importType, file: selectedFile });
  };

  const onCaseHomeSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!caseHomeSourceFile) {
      setCaseHomeErrorText('请先选择病案首页文件。');
      return;
    }
    setQueueNotice('');
    setCaseHomeErrorText('');
    caseHomeUploadMutation.mutate({ sourceFile: caseHomeSourceFile });
  };

  const onClear = () => {
    const text = window.prompt('请输入确认口令 CLEAR_CASE_COST_DATA');
    if (!text) return;
    clearMutation.mutate(text.trim());
  };

  const onRestore = () => {
    if (!restoreFile) {
      setMaintenanceText('请先选择恢复文件。');
      return;
    }
    const text = window.prompt('请输入确认口令 CLEAR_CASE_COST_DATA');
    if (!text) return;
    restoreMutation.mutate({ file: restoreFile, confirmText: text.trim() });
  };

  const totalIssuePages = useMemo(
    () => Math.max(1, Math.ceil((issuesQuery.data?.total ?? 0) / (issuesQuery.data?.page_size ?? 10))),
    [issuesQuery.data],
  );

  return (
    <section className="import-layout import-layout--single">
      <div className="import-left-col">
        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>导入队列总览</h2>
            <p>上传文件只负责入队，实际解析与写库在后台完成。导入期间你可以继续停留在本页查看进度，也可以切换到其他页面。</p>
          </header>

          <div className="metrics-row metrics-row--five import-summary-row">
            <div className="metric-card">
              <p className="metric-label">处理中</p>
              <h3 className="metric-value">{queueSummary.running}</h3>
              <p className="metric-trend">后台正在执行的任务</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">排队中</p>
              <h3 className="metric-value">{queueSummary.queued}</h3>
              <p className="metric-trend">等待轮到的批次</p>
            </div>
            <div className="metric-card metric-card--good">
              <p className="metric-label">最近成功</p>
              <h3 className="metric-value">{queueSummary.success}</h3>
              <p className="metric-trend">当前列表内成功批次</p>
            </div>
            <div className="metric-card metric-card--alert">
              <p className="metric-label">最近失败</p>
              <h3 className="metric-value">{queueSummary.failed}</h3>
              <p className="metric-trend">建议查看错误明细</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">自动刷新</p>
              <h3 className="metric-value">{activeBatch ? '开启' : '空闲'}</h3>
              <p className="metric-trend">{activeBatch ? '导入中每 2.5 秒刷新' : '空闲时降低刷新频率'}</p>
            </div>
          </div>

          {uploadState ? (
            <div className="import-live-card">
              <div className="import-live-head">
                <strong>{uploadState.kind === 'case-home' ? '病案首页上传中' : '运营数据上传中'}</strong>
                <span>{uploadState.phase === 'uploading' ? `已上传 ${uploadState.progress}%` : '文件已传完，正在提交到后台队列'}</span>
              </div>
              <div className="import-progress">
                <div className="import-progress-bar" style={{ width: `${Math.max(uploadState.progress, 8)}%` }} />
              </div>
              <p className="import-live-caption">{uploadState.fileName}</p>
            </div>
          ) : null}

          {queueNotice ? <div className="inline-notice inline-notice--success">{queueNotice}</div> : null}

          {activeBatch ? (
            <div className="active-batch-card">
              <div>
                <p className="dashboard-aside-label">当前关注批次</p>
                <strong>{activeBatch.source_filename}</strong>
                <p className="metric-trend">
                  批次 {activeBatch.batch_id.slice(0, 8)} · {statusText(activeBatch.status)}
                </p>
              </div>
              <div className="active-batch-meta">
                <span>创建时间：{formatDateTime(activeBatch.created_at)}</span>
                <span>开始时间：{formatDateTime(activeBatch.started_at)}</span>
                <span>结束时间：{formatDateTime(activeBatch.finished_at)}</span>
              </div>
            </div>
          ) : (
            <p className="empty-hint">当前没有活跃导入任务。</p>
          )}
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>病案首页导入</h2>
            <p>先导入病案首页，再补充出院与费用数据。提交后会立即进入后台队列，不再阻塞页面。</p>
          </header>
          <form className="import-form" onSubmit={onCaseHomeSubmit}>
            <label className="field">
              <span>病案首页文件</span>
              <input accept=".xlsx,.xls,.csv" type="file" onChange={(event) => setCaseHomeSourceFile(event.target.files?.[0] ?? null)} />
            </label>
            <div className="action-row">
              <button className="btn-primary" disabled={!caseHomeSourceFile || caseHomeUploadMutation.isPending} type="submit">
                {caseHomeUploadMutation.isPending ? '正在上传并入队...' : '提交到队列'}
              </button>
              <span>{caseHomeSourceFile?.name || '未选择病案首页文件'}</span>
            </div>
            <p className="helper-text">大文件会先上传到服务器，再转入后台队列处理；上传结束后无需停留等待解析完成。</p>
            {caseHomeErrorText ? <p className="error-text">{caseHomeErrorText}</p> : null}
          </form>
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>运营数据导入</h2>
            <p>仅保留运营分析所需导入类型。导入完成后不再触发阻塞式全屏刷新，你可稍后手动查看驾驶舱数据。</p>
          </header>
          <form className="import-form" onSubmit={onSubmit}>
            <label className="field">
              <span>导入类型</span>
              <select value={importType} onChange={(event) => setImportType(event.target.value as ImportType)}>
                {importTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="dropzone">
              <input accept=".xlsx,.xls,.csv" type="file" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
              <strong>{selectedFile ? selectedFile.name : '拖拽文件到此处或点击选择'}</strong>
              <span>建议单文件不超过 100MB，超大文件会明显增加上传时间</span>
            </label>
            <div className="action-row">
              <button className="btn-primary" disabled={!selectedFile || uploadMutation.isPending} type="submit">
                {uploadMutation.isPending ? '正在上传并入队...' : '提交到队列'}
              </button>
              {errorText ? <p className="error-text">{errorText}</p> : null}
            </div>
            <p className="helper-text">如果批次状态显示“排队中”或“处理中”，说明文件已经安全提交，你可以继续做其他操作。</p>
          </form>
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>数据维护</h2>
            <p>用于做导入前备份、全量清除和一键恢复。</p>
          </header>
          <div className="action-row maintenance-actions">
            <button className="btn-secondary" onClick={() => backupMutation.mutate()} type="button">
              {backupMutation.isPending ? '备份中...' : '备份病案与费用数据'}
            </button>
            <button className="btn-danger" onClick={onClear} type="button">
              {clearMutation.isPending ? '清除中...' : '清除病案与费用导入数据'}
            </button>
          </div>
          <label className="field maintenance-file">
            <span>恢复文件（备份 xlsx）</span>
            <input accept=".xlsx,.xls" type="file" onChange={(event) => setRestoreFile(event.target.files?.[0] ?? null)} />
          </label>
          <div className="action-row maintenance-actions">
            <button className="btn-danger" disabled={!restoreFile} onClick={onRestore} type="button">
              {restoreMutation.isPending ? '恢复中...' : '从备份恢复'}
            </button>
            <span>{restoreFile?.name || '未选择恢复文件'}</span>
          </div>
          {maintenanceText ? <p className="maintenance-text">{maintenanceText}</p> : null}
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>批次问题明细</h2>
            <p>{selectedBatchId ? `当前批次 ${selectedBatchId.slice(0, 8)}` : '请先选择一个导入批次'}</p>
          </header>
          {selectedBatchId ? (
            <>
              <div className="issue-toolbar">
                <label className="field field--compact">
                  <span>级别</span>
                  <select value={issueSeverity} onChange={(event) => setIssueSeverity(event.target.value)}>
                    <option value="">全部</option>
                    <option value="WARN">WARN</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </label>
                <label className="field field--compact">
                  <span>错误码</span>
                  <input value={issueCode} onChange={(event) => setIssueCode(event.target.value.trim().toUpperCase())} placeholder="如 V010" />
                </label>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    downloadImportIssues({
                      batchId: selectedBatchId,
                      format: 'csv',
                      severity: issueSeverity || undefined,
                      errorCode: issueCode || undefined,
                    })
                  }
                  type="button"
                >
                  下载 CSV
                </button>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    downloadImportIssues({
                      batchId: selectedBatchId,
                      format: 'xlsx',
                      severity: issueSeverity || undefined,
                      errorCode: issueCode || undefined,
                    })
                  }
                  type="button"
                >
                  下载 XLSX
                </button>
              </div>
              <div className="table-wrap issue-table">
                <table>
                  <thead>
                    <tr>
                      <th>行号</th>
                      <th>错误码</th>
                      <th>级别</th>
                      <th>字段</th>
                      <th>信息</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(issuesQuery.data?.items ?? []).map((item) => (
                      <tr key={item.id}>
                        <td>{item.row_no}</td>
                        <td>{item.error_code}</td>
                        <td>{item.severity}</td>
                        <td>{item.field_name || '-'}</td>
                        <td title={item.message}>{item.message}</td>
                      </tr>
                    ))}
                    {!issuesQuery.data?.items.length ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center' }}>
                          当前筛选下无问题记录
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
              <div className="pager-row">
                <button className="btn-secondary" disabled={issuePage <= 1} onClick={() => setIssuePage((prev) => prev - 1)} type="button">
                  上一页
                </button>
                <span>
                  第 {issuePage} / {totalIssuePages} 页，共 {issuesQuery.data?.total ?? 0} 条
                </span>
                <button className="btn-secondary" disabled={issuePage >= totalIssuePages} onClick={() => setIssuePage((prev) => prev + 1)} type="button">
                  下一页
                </button>
              </div>
            </>
          ) : (
            <p className="empty-hint">选择批次后可查看错误明细并导出。</p>
          )}
        </article>
      </div>

      <article className="panel">
        <header className="panel-head">
          <h2>批次历史</h2>
          <p>最近 20 条导入批次，导入中的批次会自动置顶显示。</p>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>批次</th>
                <th>类型</th>
                <th>文件</th>
                <th>状态</th>
                <th>行数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {(importsQuery.data ?? []).map((item) => (
                <tr
                  key={item.batch_id}
                  className={selectedBatchId === item.batch_id ? 'is-selected-row' : ''}
                  onClick={() => {
                    setSelectedBatchId(item.batch_id);
                    setIssuePage(1);
                  }}
                >
                  <td>{item.batch_id.slice(0, 8)}</td>
                  <td>{item.import_type}</td>
                  <td title={item.source_filename}>{item.source_filename}</td>
                  <td>
                    <span className={`status-badge status-${item.status.toLowerCase()}`}>{statusText(item.status)}</span>
                  </td>
                  <td>{item.row_count}</td>
                  <td>
                    {isActiveBatchStatus(item.status) ? (
                      <button
                        className="btn-secondary"
                        disabled={cancelMutation.isPending}
                        onClick={(event) => {
                          event.stopPropagation();
                          cancelMutation.mutate(item.batch_id);
                        }}
                        type="button"
                      >
                        取消
                      </button>
                    ) : (
                      '-'
                    )}
                  </td>
                </tr>
              ))}
              {!importsQuery.data?.length ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center' }}>
                    暂无导入记录
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        {selectedBatch ? (
          <div className="batch-detail-card">
            <p className="dashboard-aside-label">批次详情</p>
            <strong>{selectedBatch.source_filename}</strong>
            <div className="batch-detail-grid">
              <span>状态：{statusText(selectedBatch.status)}</span>
              <span>导入类型：{selectedBatch.import_type}</span>
              <span>创建时间：{formatDateTime(selectedBatch.created_at)}</span>
              <span>开始时间：{formatDateTime(selectedBatch.started_at)}</span>
              <span>结束时间：{formatDateTime(selectedBatch.finished_at)}</span>
              <span>导入行数：{selectedBatch.row_count || 0}</span>
            </div>
            {selectedBatch.error_message ? <p className="error-text">{selectedBatch.error_message}</p> : null}
          </div>
        ) : null}
      </article>
    </section>
  );
}
