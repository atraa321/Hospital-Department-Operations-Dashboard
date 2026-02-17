import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  clearCaseCostImportData,
  createCaseHomeImportBatch,
  createImportBatch,
  downloadCaseCostBackup,
  downloadImportIssues,
  fetchDipMappings,
  fetchDipVersions,
  fetchOrphanFeePatients,
  fetchImportBatches,
  fetchImportIssues,
  manualFillDip,
  recalculateDipMappings,
  restoreCaseCostImportData,
  type ImportType,
  updateOrphanFeePatientAction,
} from '../lib/api';

const importTypeOptions: { label: string; value: ImportType }[] = [
  { label: '病案出院数据', value: 'CASE_INFO' },
  { label: '费用汇总数据', value: 'COST_SUMMARY' },
  { label: '费用明细数据', value: 'COST_DETAIL' },
  { label: 'DIP目录', value: 'DIP_DICT' },
  { label: 'ICD10映射', value: 'ICD10_DICT' },
  { label: 'ICD9映射', value: 'ICD9_DICT' },
];

export function ImportPage() {
  const [importType, setImportType] = useState<ImportType>('CASE_INFO');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorText, setErrorText] = useState<string>('');
  const [caseHomeSourceFile, setCaseHomeSourceFile] = useState<File | null>(null);
  const [caseHomeErrorText, setCaseHomeErrorText] = useState('');
  const [selectedBatchId, setSelectedBatchId] = useState<string>('');
  const [issuePage, setIssuePage] = useState(1);
  const [issueSeverity, setIssueSeverity] = useState('');
  const [issueCode, setIssueCode] = useState('');
  const [orphanPage, setOrphanPage] = useState(1);
  const [dipPage, setDipPage] = useState(1);
  const [maintenanceText, setMaintenanceText] = useState('');
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const queryClient = useQueryClient();

  const importsQuery = useQuery({
    queryKey: ['imports'],
    queryFn: () => fetchImportBatches(20),
  });

  const uploadMutation = useMutation({
    mutationFn: createImportBatch,
    onSuccess: () => {
      setSelectedFile(null);
      setErrorText('');
      queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
    onError: (error: unknown) => {
      if (error instanceof Error) {
        if (error.message.toLowerCase().includes('timeout')) {
          setErrorText('导入连接超时，请重试或检查网络/网关超时配置。');
          return;
        }
        setErrorText(error.message);
      } else {
        setErrorText('导入失败，请检查网络或文件格式。');
      }
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
      if (error instanceof Error) {
        if (error.message.toLowerCase().includes('timeout')) {
          setCaseHomeErrorText('病案首页导入连接超时，请重试或检查网络/网关超时配置。');
          return;
        }
        setCaseHomeErrorText(error.message);
      } else {
        setCaseHomeErrorText('病案首页导入失败，请检查文件格式。');
      }
    },
  });

  const issuesQuery = useQuery({
    queryKey: ['import-issues', selectedBatchId, issuePage, issueSeverity, issueCode],
    queryFn: () =>
      fetchImportIssues({
        batchId: selectedBatchId,
        page: issuePage,
        pageSize: 10,
        severity: issueSeverity,
        errorCode: issueCode,
      }),
    enabled: Boolean(selectedBatchId),
  });

  const orphanQuery = useQuery({
    queryKey: ['orphan-fee-patients', orphanPage],
    queryFn: () => fetchOrphanFeePatients(orphanPage, 8),
  });

  const dipVersionQuery = useQuery({
    queryKey: ['dip-versions'],
    queryFn: fetchDipVersions,
  });

  const dipUnmappedQuery = useQuery({
    queryKey: ['dip-unmapped', dipPage],
    queryFn: () => fetchDipMappings({ page: dipPage, pageSize: 8, status: 'UNMAPPED' }),
  });

  const orphanActionMutation = useMutation({
    mutationFn: updateOrphanFeePatientAction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orphan-fee-patients'] });
    },
  });

  const dipRecalcMutation = useMutation({
    mutationFn: () => recalculateDipMappings(5000),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dip-unmapped'] });
    },
  });

  const dipManualMutation = useMutation({
    mutationFn: manualFillDip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dip-unmapped'] });
    },
  });

  const backupMutation = useMutation({
    mutationFn: downloadCaseCostBackup,
    onSuccess: () => {
      setMaintenanceText('备份文件已生成并下载。');
    },
    onError: (error: unknown) => {
      if (error instanceof Error && error.message.toLowerCase().includes('timeout')) {
        setMaintenanceText('备份超时，请稍后重试或减少历史数据后再备份。');
        return;
      }
      setMaintenanceText('备份失败，请检查后端服务、权限或网络连接。');
    },
  });

  const clearMutation = useMutation({
    mutationFn: clearCaseCostImportData,
    onSuccess: (result) => {
      setSelectedBatchId('');
      setIssuePage(1);
      setMaintenanceText(
        `已清除：病案${result.deleted_case_info}条，费用明细${result.deleted_cost_detail}条，导入批次${result.deleted_import_batch}条。`,
      );
      queryClient.invalidateQueries({ queryKey: ['imports'] });
      queryClient.invalidateQueries({ queryKey: ['import-issues'] });
      queryClient.invalidateQueries({ queryKey: ['orphan-fee-patients'] });
      queryClient.invalidateQueries({ queryKey: ['dip-unmapped'] });
      queryClient.invalidateQueries({ queryKey: ['quality-overview'] });
    },
    onError: () => {
      setMaintenanceText('清除失败，请确认口令与账号权限。');
    },
  });

  const restoreMutation = useMutation({
    mutationFn: restoreCaseCostImportData,
    onSuccess: (result) => {
      setSelectedBatchId('');
      setIssuePage(1);
      setRestoreFile(null);
      setMaintenanceText(
        `恢复完成：病案${result.restored_case_info}条，费用明细${result.restored_cost_detail}条，导入批次${result.restored_import_batch}条。`,
      );
      queryClient.invalidateQueries({ queryKey: ['imports'] });
      queryClient.invalidateQueries({ queryKey: ['import-issues'] });
      queryClient.invalidateQueries({ queryKey: ['orphan-fee-patients'] });
      queryClient.invalidateQueries({ queryKey: ['dip-unmapped'] });
      queryClient.invalidateQueries({ queryKey: ['quality-overview'] });
    },
    onError: () => {
      setMaintenanceText('恢复失败，请检查备份文件格式、口令和账号权限。');
    },
  });

  const canSubmit = useMemo(() => Boolean(selectedFile) && !uploadMutation.isPending, [selectedFile, uploadMutation.isPending]);
  const canCaseHomeSubmit = useMemo(
    () => Boolean(caseHomeSourceFile) && !caseHomeUploadMutation.isPending,
    [caseHomeSourceFile, caseHomeUploadMutation.isPending],
  );

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setErrorText('请先选择 Excel/CSV 文件。');
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
    caseHomeUploadMutation.mutate({
      sourceFile: caseHomeSourceFile,
    });
  };

  const onSelectBatch = (batchId: string) => {
    setSelectedBatchId(batchId);
    setIssuePage(1);
    setIssueSeverity('');
    setIssueCode('');
  };

  const totalIssuePages = Math.max(
    1,
    Math.ceil((issuesQuery.data?.total ?? 0) / (issuesQuery.data?.page_size ?? 10)),
  );

  const totalOrphanPages = Math.max(
    1,
    Math.ceil((orphanQuery.data?.total ?? 0) / (orphanQuery.data?.page_size ?? 8)),
  );

  const totalDipPages = Math.max(
    1,
    Math.ceil((dipUnmappedQuery.data?.total ?? 0) / (dipUnmappedQuery.data?.page_size ?? 8)),
  );

  const onOrphanAction = (patientId: string, status: 'MARKED' | 'REJECTED' | 'SUPPLEMENTED') => {
    const note = window.prompt('请输入处理说明（可空）：') ?? '';
    orphanActionMutation.mutate({
      patientId,
      status,
      note,
      operator: 'current_user',
    });
  };

  const onDipManualFill = (patientId: string) => {
    const dipCode = window.prompt('请输入DIP编码（如 G45.9:88.4101）');
    if (!dipCode) {
      return;
    }
    const note = window.prompt('回填说明（可空）') ?? '';
    dipManualMutation.mutate({
      patientId,
      dipCode: dipCode.trim().toUpperCase(),
      note,
      operator: 'current_user',
    });
  };

  const onClearCaseCostData = () => {
    const text = window.prompt(
      '该操作将清除病案和费用导入数据，且不可恢复。请输入确认口令：CLEAR_CASE_COST_DATA',
    );
    if (!text) {
      return;
    }
    clearMutation.mutate(text.trim());
  };

  const onRestoreCaseCostData = () => {
    if (!restoreFile) {
      setMaintenanceText('请先选择备份文件后再恢复。');
      return;
    }
    const text = window.prompt(
      '该操作将先清空现有病案和费用数据，再从备份恢复。请输入确认口令：CLEAR_CASE_COST_DATA',
    );
    if (!text) {
      return;
    }
    restoreMutation.mutate({ file: restoreFile, confirmText: text.trim() });
  };

  return (
    <section className="import-layout">
      <div className="import-left-col">
        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>病案首页导入</h2>
            <p>上传全院病案首页文件，仅导入患者基础信息（性别、年龄、职业、现住址等，缺失留空）。</p>
          </header>
          <form className="import-form" onSubmit={onCaseHomeSubmit}>
            <label className="field">
              <span>病案首页文件（如 2024-2025病案信息.xlsx）</span>
              <input
                accept=".xlsx,.xls,.csv"
                type="file"
                onChange={(event) => setCaseHomeSourceFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <div className="action-row">
              <button className="btn-primary" disabled={!canCaseHomeSubmit} type="submit">
                {caseHomeUploadMutation.isPending ? '导入中...' : '开始导入'}
              </button>
              <span>{caseHomeSourceFile?.name || '未选择病案首页文件'}</span>
            </div>
            {caseHomeErrorText ? <p className="error-text">{caseHomeErrorText}</p> : null}
          </form>
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>导入执行台</h2>
            <p>支持 `.xlsx/.xls/.csv`，按批次记录导入结果。</p>
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
              <input
                accept=".xlsx,.xls,.csv"
                type="file"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
              <strong>{selectedFile ? selectedFile.name : '拖拽文件到此处或点击选择'}</strong>
              <span>建议单文件不超过 100MB</span>
            </label>

            <div className="action-row">
              <button className="btn-primary" disabled={!canSubmit} type="submit">
                {uploadMutation.isPending ? '导入中...' : '开始导入'}
              </button>
              {errorText ? <p className="error-text">{errorText}</p> : null}
            </div>
          </form>
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>数据维护</h2>
            <p>建议先备份，再执行清除。清除仅删除病案和费用导入数据。</p>
          </header>
          <div className="action-row maintenance-actions">
            <button
              className="btn-secondary"
              disabled={backupMutation.isPending || clearMutation.isPending || restoreMutation.isPending}
              onClick={() => backupMutation.mutate()}
              type="button"
            >
              {backupMutation.isPending ? '备份中...' : '备份病案+费用数据'}
            </button>
            <button
              className="btn-danger"
              disabled={backupMutation.isPending || clearMutation.isPending || restoreMutation.isPending}
              onClick={onClearCaseCostData}
              type="button"
            >
              {clearMutation.isPending ? '清除中...' : '清除病案+费用导入数据'}
            </button>
          </div>
          <label className="field maintenance-file">
            <span>恢复文件（备份xlsx）</span>
            <input
              accept=".xlsx,.xls"
              type="file"
              onChange={(event) => setRestoreFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="action-row maintenance-actions">
            <button
              className="btn-danger"
              disabled={!restoreFile || backupMutation.isPending || clearMutation.isPending || restoreMutation.isPending}
              onClick={onRestoreCaseCostData}
              type="button"
            >
              {restoreMutation.isPending ? '恢复中...' : '从备份一键恢复'}
            </button>
            <span>{restoreFile ? restoreFile.name : '未选择恢复文件'}</span>
          </div>
          {maintenanceText ? <p className="maintenance-text">{maintenanceText}</p> : null}
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>批次问题明细</h2>
            <p>{selectedBatchId ? `批次 ${selectedBatchId.slice(0, 8)}` : '请先在右侧选择一个批次'}</p>
          </header>
          {selectedBatchId ? (
            <>
              <div className="issue-toolbar">
                <label className="field field--compact">
                  <span>级别</span>
                  <select
                    value={issueSeverity}
                    onChange={(event) => {
                      setIssuePage(1);
                      setIssueSeverity(event.target.value);
                    }}
                  >
                    <option value="">全部</option>
                    <option value="WARN">WARN</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </label>
                <label className="field field--compact">
                  <span>错误码</span>
                  <input
                    placeholder="如 V010"
                    value={issueCode}
                    onChange={(event) => {
                      setIssuePage(1);
                      setIssueCode(event.target.value.trim().toUpperCase());
                    }}
                  />
                </label>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    downloadImportIssues({
                      batchId: selectedBatchId,
                      format: 'csv',
                      severity: issueSeverity,
                      errorCode: issueCode,
                    })
                  }
                  type="button"
                >
                  下载CSV
                </button>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    downloadImportIssues({
                      batchId: selectedBatchId,
                      format: 'xlsx',
                      severity: issueSeverity,
                      errorCode: issueCode,
                    })
                  }
                  type="button"
                >
                  下载XLSX
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
                    {issuesQuery.data?.items.map((it) => (
                      <tr key={it.id}>
                        <td>{it.row_no}</td>
                        <td>{it.error_code}</td>
                        <td>{it.severity}</td>
                        <td>{it.field_name || '-'}</td>
                        <td title={it.message}>{it.message}</td>
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
                <button
                  className="btn-secondary"
                  disabled={issuePage <= 1}
                  onClick={() => setIssuePage((p) => Math.max(1, p - 1))}
                  type="button"
                >
                  上一页
                </button>
                <span>
                  第 {issuePage} / {totalIssuePages} 页，共 {issuesQuery.data?.total ?? 0} 条
                </span>
                <button
                  className="btn-secondary"
                  disabled={issuePage >= totalIssuePages}
                  onClick={() => setIssuePage((p) => Math.min(totalIssuePages, p + 1))}
                  type="button"
                >
                  下一页
                </button>
              </div>
            </>
          ) : (
            <p className="empty-hint">选择批次后可查看错误明细并导出。</p>
          )}
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>孤儿费用处理池</h2>
            <p>有费用明细但无病案主记录，可标注/驳回/补录</p>
          </header>
          <div className="table-wrap issue-table">
            <table>
              <thead>
                <tr>
                  <th>住院号</th>
                  <th>明细数</th>
                  <th>总金额</th>
                  <th>状态</th>
                  <th>说明</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {orphanQuery.data?.items.map((item) => (
                  <tr key={item.patient_id}>
                    <td>{item.patient_id}</td>
                    <td>{item.detail_count}</td>
                    <td>{item.total_amount.toFixed(2)}</td>
                    <td>{item.status}</td>
                    <td title={item.note || ''}>{item.note || '-'}</td>
                    <td className="cell-actions">
                      <button
                        className="btn-secondary"
                        disabled={orphanActionMutation.isPending}
                        onClick={() => onOrphanAction(item.patient_id, 'MARKED')}
                        type="button"
                      >
                        标注
                      </button>
                      <button
                        className="btn-secondary"
                        disabled={orphanActionMutation.isPending}
                        onClick={() => onOrphanAction(item.patient_id, 'REJECTED')}
                        type="button"
                      >
                        驳回
                      </button>
                      <button
                        className="btn-secondary"
                        disabled={orphanActionMutation.isPending}
                        onClick={() => onOrphanAction(item.patient_id, 'SUPPLEMENTED')}
                        type="button"
                      >
                        补录
                      </button>
                    </td>
                  </tr>
                ))}
                {!orphanQuery.data?.items.length ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center' }}>
                      当前无孤儿费用记录
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
          <div className="pager-row">
            <button
              className="btn-secondary"
              disabled={orphanPage <= 1}
              onClick={() => setOrphanPage((p) => Math.max(1, p - 1))}
              type="button"
            >
              上一页
            </button>
            <span>
              第 {orphanPage} / {totalOrphanPages} 页，共 {orphanQuery.data?.total ?? 0} 条
            </span>
            <button
              className="btn-secondary"
              disabled={orphanPage >= totalOrphanPages}
              onClick={() => setOrphanPage((p) => Math.min(totalOrphanPages, p + 1))}
              type="button"
            >
              下一页
            </button>
          </div>
        </article>

        <article className="panel panel--wide">
          <header className="panel-head">
            <h2>DIP待映射池</h2>
            <p>
              当前版本 ICD10 {dipVersionQuery.data?.icd10_versions?.[0]?.version || '-'} / ICD9{' '}
              {dipVersionQuery.data?.icd9_versions?.[0]?.version || '-'} / DIP{' '}
              {dipVersionQuery.data?.dip_versions?.[0]?.version || '-'}
            </p>
          </header>
          <div className="action-row" style={{ marginTop: 12 }}>
            <button className="btn-secondary" onClick={() => dipRecalcMutation.mutate()} type="button">
              {dipRecalcMutation.isPending ? '重算中...' : '重算DIP映射'}
            </button>
            <span>
              {dipRecalcMutation.data
                ? `总计 ${dipRecalcMutation.data.total}，已映射 ${dipRecalcMutation.data.mapped}，未映射 ${dipRecalcMutation.data.unmapped}`
                : ''}
            </span>
          </div>
          <div className="table-wrap issue-table">
            <table>
              <thead>
                <tr>
                  <th>住院号</th>
                  <th>诊断编码</th>
                  <th>手术编码</th>
                  <th>失败原因</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {dipUnmappedQuery.data?.items.map((item) => (
                  <tr key={item.patient_id}>
                    <td>{item.patient_id}</td>
                    <td>{item.mapped_diag_code || item.diagnosis_code || '-'}</td>
                    <td>{item.mapped_surgery_code || item.surgery_code || '-'}</td>
                    <td>{item.fail_reason || '-'}</td>
                    <td>
                      <button className="btn-secondary" onClick={() => onDipManualFill(item.patient_id)} type="button">
                        人工回填
                      </button>
                    </td>
                  </tr>
                ))}
                {!dipUnmappedQuery.data?.items.length ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center' }}>
                      当前无待映射记录
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
          <div className="pager-row">
            <button
              className="btn-secondary"
              disabled={dipPage <= 1}
              onClick={() => setDipPage((p) => Math.max(1, p - 1))}
              type="button"
            >
              上一页
            </button>
            <span>
              第 {dipPage} / {totalDipPages} 页，共 {dipUnmappedQuery.data?.total ?? 0} 条
            </span>
            <button
              className="btn-secondary"
              disabled={dipPage >= totalDipPages}
              onClick={() => setDipPage((p) => Math.min(totalDipPages, p + 1))}
              type="button"
            >
              下一页
            </button>
          </div>
        </article>
      </div>

      <article className="panel">
        <header className="panel-head">
          <h2>批次历史</h2>
          <p>最近20条导入批次</p>
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
              </tr>
            </thead>
            <tbody>
              {importsQuery.data?.map((item) => (
                <tr
                  key={item.batch_id}
                  className={selectedBatchId === item.batch_id ? 'is-selected-row' : ''}
                  onClick={() => onSelectBatch(item.batch_id)}
                >
                  <td>{item.batch_id.slice(0, 8)}</td>
                  <td>{item.import_type}</td>
                  <td title={item.source_filename}>{item.source_filename}</td>
                  <td>
                    <span className={`status-badge status-${item.status.toLowerCase()}`}>{item.status}</span>
                  </td>
                  <td>{item.row_count}</td>
                </tr>
              ))}
              {!importsQuery.data?.length ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center' }}>
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
