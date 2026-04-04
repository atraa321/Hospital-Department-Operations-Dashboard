import { useMemo, useState } from 'react';
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
  type ImportType,
} from '../lib/api';

const importTypeOptions: { label: string; value: ImportType }[] = [
  { label: '病案出院数据', value: 'CASE_INFO' },
  { label: '费用汇总数据', value: 'COST_SUMMARY' },
  { label: '费用明细数据', value: 'COST_DETAIL' },
];

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
  const queryClient = useQueryClient();

  const importsQuery = useQuery({
    queryKey: ['imports'],
    queryFn: () => fetchImportBatches(20),
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      return items.some((item) => ['QUEUED', 'RUNNING', 'PENDING'].includes(item.status)) ? 5000 : false;
    },
  });

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
  });

  const uploadMutation = useMutation({
    mutationFn: createImportBatch,
    onSuccess: () => {
      setSelectedFile(null);
      setErrorText('');
      queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
    onError: (error: unknown) => {
      setErrorText(error instanceof Error ? error.message : '导入失败，请检查文件格式。');
    },
  });

  const caseHomeUploadMutation = useMutation({
    mutationFn: createCaseHomeImportBatch,
    onSuccess: () => {
      setCaseHomeSourceFile(null);
      setCaseHomeErrorText('');
      queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
    onError: (error: unknown) => {
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
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['imports'] }),
  });

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setErrorText('请先选择导入文件。');
      return;
    }
    uploadMutation.mutate({ importType, file: selectedFile });
  };

  const onCaseHomeSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!caseHomeSourceFile) {
      setCaseHomeErrorText('请先选择病案首页文件。');
      return;
    }
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
            <h2>病案首页导入</h2>
            <p>先导入病案首页，再补充出院与费用数据，保证运营分析口径完整。</p>
          </header>
          <form className="import-form" onSubmit={onCaseHomeSubmit}>
            <label className="field">
              <span>病案首页文件</span>
              <input accept=".xlsx,.xls,.csv" type="file" onChange={(event) => setCaseHomeSourceFile(event.target.files?.[0] ?? null)} />
            </label>
            <div className="action-row">
              <button className="btn-primary" disabled={!caseHomeSourceFile || caseHomeUploadMutation.isPending} type="submit">
                {caseHomeUploadMutation.isPending ? '提交中...' : '提交到队列'}
              </button>
              <span>{caseHomeSourceFile?.name || '未选择病案首页文件'}</span>
            </div>
            {caseHomeErrorText ? <p className="error-text">{caseHomeErrorText}</p> : null}
          </form>
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>运营数据导入</h2>
            <p>仅保留运营分析所需导入类型，DIP 字典与映射维护已从前台移除。</p>
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
              <span>建议单文件不超过 100MB</span>
            </label>
            <div className="action-row">
              <button className="btn-primary" disabled={!selectedFile || uploadMutation.isPending} type="submit">
                {uploadMutation.isPending ? '提交中...' : '提交到队列'}
              </button>
              {errorText ? <p className="error-text">{errorText}</p> : null}
            </div>
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
                <button className="btn-secondary" onClick={() => downloadImportIssues({ batchId: selectedBatchId, format: 'csv', severity: issueSeverity || undefined, errorCode: issueCode || undefined })} type="button">
                  下载 CSV
                </button>
                <button className="btn-secondary" onClick={() => downloadImportIssues({ batchId: selectedBatchId, format: 'xlsx', severity: issueSeverity || undefined, errorCode: issueCode || undefined })} type="button">
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
          <p>最近 20 条导入批次</p>
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
                <tr key={item.batch_id} className={selectedBatchId === item.batch_id ? 'is-selected-row' : ''} onClick={() => setSelectedBatchId(item.batch_id)}>
                  <td>{item.batch_id.slice(0, 8)}</td>
                  <td>{item.import_type}</td>
                  <td title={item.source_filename}>{item.source_filename}</td>
                  <td>
                    <span className={`status-badge status-${item.status.toLowerCase()}`}>{item.status}</span>
                  </td>
                  <td>{item.row_count}</td>
                  <td>
                    {['QUEUED', 'RUNNING', 'PENDING'].includes(item.status) ? (
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
      </article>
    </section>
  );
}
