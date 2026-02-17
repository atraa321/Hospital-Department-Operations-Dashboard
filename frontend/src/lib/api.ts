import axios from 'axios';

export type ImportType =
  | 'CASE_INFO'
  | 'CASE_HOME_FILTERED'
  | 'COST_SUMMARY'
  | 'COST_DETAIL'
  | 'DIP_DICT'
  | 'ICD10_DICT'
  | 'ICD9_DICT';

export interface ImportBatch {
  batch_id: string;
  import_type: string;
  source_filename: string;
  status: string;
  row_count: number;
  column_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportIssue {
  id: number;
  row_no: number;
  field_name: string | null;
  error_code: string;
  severity: string;
  message: string;
  created_at: string;
}

export interface ImportIssueList {
  total: number;
  page: number;
  page_size: number;
  items: ImportIssue[];
}

export interface ImportDataClearResult {
  message: string;
  deleted_case_info: number;
  deleted_cost_detail: number;
  deleted_orphan_fee_action: number;
  deleted_import_batch: number;
  deleted_import_issue: number;
  deleted_upload_files: number;
}

export interface ImportDataRestoreResult extends ImportDataClearResult {
  restored_case_info: number;
  restored_cost_detail: number;
  restored_orphan_fee_action: number;
  restored_import_batch: number;
  restored_import_issue: number;
}

export interface QualityIssueCount {
  error_code: string;
  severity: string;
  count: number;
}

export interface QualityOverview {
  case_total: number;
  cost_detail_total: number;
  batch_total: number;
  batch_failed: number;
  pk_complete_rate: number;
  required_complete_rate: number;
  icd_valid_rate: number;
  orphan_fee_record_rate: number;
  import_failure_rate: number;
  warning_issue_total: number;
  error_issue_total: number;
  issues: QualityIssueCount[];
  generated_at: string;
}

export interface OrphanFeePatient {
  patient_id: string;
  detail_count: number;
  total_amount: number;
  latest_import_batch: string | null;
  status: string;
  note: string | null;
  operator: string | null;
  updated_at: string | null;
}

export interface OrphanFeePatientList {
  total: number;
  page: number;
  page_size: number;
  items: OrphanFeePatient[];
}

export interface CostStructureItem {
  name: string;
  value: number;
}

export interface TrendPoint {
  period: string;
  avg_cost: number;
  avg_drug_ratio: number;
}

export interface ClinicalTopItem {
  diagnosis_code: string;
  diagnosis_name: string | null;
  case_count: number;
}

export interface DiseasePriorityItem {
  diagnosis_code: string;
  diagnosis_name: string | null;
  case_count: number;
  avg_total_cost: number;
  avg_los: number;
  score: number;
  layer: string;
  case_score: number;
  fee_contribution_score: number;
  volatility_score: number;
  reject_risk_score: number;
  los_risk_score: number;
  readmission_risk_score: number;
  variation_risk_score: number;
}

export interface AlertRule {
  id: number;
  rule_code: string;
  name: string;
  metric_type: string;
  yellow_threshold: number;
  orange_threshold: number;
  red_threshold: number;
  description: string | null;
  enabled: boolean;
  updated_at: string;
}

export interface RuleHit {
  id: number;
  rule_code: string;
  patient_id: string;
  diagnosis_code: string | null;
  dept_name: string | null;
  severity: string;
  metric_value: number;
  threshold_value: number | null;
  evidence_json: string | null;
  hit_at: string;
}

export interface RuleHitList {
  total: number;
  page: number;
  page_size: number;
  items: RuleHit[];
}

export interface WorkOrder {
  id: number;
  order_no: string;
  hit_id: number | null;
  rule_code: string | null;
  patient_id: string | null;
  dept_name: string | null;
  severity: string;
  assignee: string | null;
  status: string;
  due_at: string | null;
  closed_at: string | null;
  remark: string | null;
  escalate_count: number;
  updated_at: string;
}

export interface WorkOrderList {
  total: number;
  page: number;
  page_size: number;
  items: WorkOrder[];
}

export interface WorkOrderStats {
  total: number;
  closed: number;
  closed_on_time: number;
  close_rate: number;
  on_time_rate: number;
}

export interface MonthlyMetric {
  period: string;
  case_count: number;
  avg_cost: number;
  avg_drug_ratio: number;
}

export interface RuleMonthlyMetric {
  period: string;
  hit_count: number;
  red_count: number;
}

export interface MonthlyReport {
  disease_metrics: MonthlyMetric[];
  rule_metrics: RuleMonthlyMetric[];
}

export interface ExecutiveBrief {
  total_cases: number;
  avg_cost: number;
  avg_los: number;
  rule_hit_total: number;
  open_workorders: number;
  close_rate: number;
}

export interface DipVersionItem {
  version: string;
  record_count: number;
}

export interface DipVersionInfo {
  icd10_versions: DipVersionItem[];
  icd9_versions: DipVersionItem[];
  dip_versions: DipVersionItem[];
}

export interface DipMappingItem {
  patient_id: string;
  diagnosis_code: string | null;
  surgery_code: string | null;
  mapped_diag_code: string | null;
  mapped_surgery_code: string | null;
  dip_code: string | null;
  dip_weight_score: number | null;
  version: string | null;
  status: string;
  fail_reason: string | null;
  source: string;
  updated_at: string;
}

export interface DipMappingList {
  total: number;
  page: number;
  page_size: number;
  items: DipMappingItem[];
}

export interface DipStatsItem {
  patient_id: string;
  patient_name: string | null;
  dept_name: string | null;
  doctor_name: string | null;
  discharge_date: string | null;
  main_diagnosis_code: string | null;
  main_diagnosis_name: string | null;
  surgery_code: string | null;
  total_cost: number;
  dip_code: string | null;
  dip_weight_score: number | null;
  dip_status: string;
  payment_low: number | null;
  payment_high: number | null;
  payment_mid: number | null;
  cost_ratio_pct: number | null;
  multiplier_level: 'LOW' | 'NORMAL' | 'HIGH' | 'ULTRA_HIGH' | 'UNKNOWN';
}

export interface DipStatsSummary {
  total_cases: number;
  grouped_cases: number;
  ungrouped_cases: number;
  point_value_min: number;
  point_value_max: number;
  expected_pay_min_total: number;
  expected_pay_max_total: number;
  low_count: number;
  normal_count: number;
  high_count: number;
  ultra_high_count: number;
  unknown_count: number;
}

export interface DipStatsResponse {
  summary: DipStatsSummary;
  total: number;
  page: number;
  page_size: number;
  items: DipStatsItem[];
}

export interface DipDepartmentList {
  items: string[];
}

export interface DirectorTopicOverviewSummary {
  total_cases: number;
  total_cost: number;
  avg_total_cost: number;
  avg_los: number;
  dip_sim_income: number;
  dip_sim_balance: number;
  point_value: number;
}

export interface DirectorTopicOverviewDisease {
  diagnosis_code: string;
  diagnosis_name: string | null;
  case_count: number;
  total_cost: number;
  avg_total_cost: number;
  avg_los: number;
  dip_sim_income: number;
  dip_sim_balance: number;
  anomaly_hit_count: number;
}

export interface DirectorMonthlyTrend {
  period: string;
  case_count: number;
  total_cost: number;
  avg_total_cost: number;
  dip_sim_balance: number;
}

export interface DirectorTopicOverviewResponse {
  summary: DirectorTopicOverviewSummary;
  diseases: DirectorTopicOverviewDisease[];
  monthly_trend: DirectorMonthlyTrend[];
}

export interface DirectorCostStructureItem {
  name: string;
  value: number;
  ratio: number;
}

export interface DirectorDipSummary {
  grouped_cases: number;
  ungrouped_cases: number;
  grouped_rate: number;
  point_value: number;
  dip_sim_income: number;
  dip_sim_balance: number;
}

export interface DirectorDoctorCompareItem {
  doctor_name: string;
  case_count: number;
  avg_total_cost: number;
  avg_los: number;
  avg_drug_ratio: number;
  avg_material_ratio: number;
  dip_sim_balance: number;
}

export interface DirectorAnomalyCategory {
  rule_code: string;
  rule_name: string | null;
  hit_count: number;
  red_count: number;
  orange_count: number;
  yellow_count: number;
}

export interface DirectorAnomalySeverity {
  severity: string;
  count: number;
}

export interface DirectorDetailTopItem {
  item_code: string | null;
  item_name: string;
  total_amount: number;
  case_count: number;
  ratio: number;
}

export interface DirectorTopicDetailResponse {
  diagnosis_code: string;
  diagnosis_name: string | null;
  case_count: number;
  total_cost: number;
  avg_total_cost: number;
  avg_los: number;
  monthly_trend: DirectorMonthlyTrend[];
  cost_structure: DirectorCostStructureItem[];
  dip_summary: DirectorDipSummary;
  doctor_compare: DirectorDoctorCompareItem[];
  anomaly_categories: DirectorAnomalyCategory[];
  anomaly_severity: DirectorAnomalySeverity[];
  detail_top_items: DirectorDetailTopItem[];
}

export interface DirectorPdfChartPayload {
  chart_key: string;
  title: string;
  image_base64: string;
  order_no: number;
  width?: number;
  height?: number;
}

interface ImportListResponse {
  items: ImportBatch[];
}

interface ImportStartResponse {
  message: string;
  batch: ImportBatch;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 20_000,
  headers: {
    'X-User-Id': import.meta.env.VITE_USER_ID ?? 'dev_user',
    'X-Role': import.meta.env.VITE_USER_ROLE ?? 'ADMIN',
    'X-Dept-Name': import.meta.env.VITE_USER_DEPT ?? '',
  },
});
// Large data imports may run for a long time; keep request alive until server returns.
const IMPORT_REQUEST_TIMEOUT_MS = 0;

export async function fetchHealth() {
  const response = await api.get<{ status: string }>('/health');
  return response.data;
}

export async function fetchQualityOverview() {
  const response = await api.get<QualityOverview>('/quality/overview');
  return response.data;
}

export async function fetchOrphanFeePatients(page = 1, pageSize = 50) {
  const response = await api.get<OrphanFeePatientList>('/quality/orphan-patients', {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function updateOrphanFeePatientAction(payload: {
  patientId: string;
  status: 'MARKED' | 'REJECTED' | 'SUPPLEMENTED' | 'PENDING';
  note?: string;
  operator?: string;
}) {
  const response = await api.post(`/quality/orphan-patients/${payload.patientId}/action`, {
    status: payload.status,
    note: payload.note || undefined,
    operator: payload.operator || undefined,
  });
  return response.data;
}

export async function fetchCostStructure(params?: {
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<{ items: CostStructureItem[] }>('/analytics/cost-structure', {
    params: {
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
    },
  });
  return response.data;
}

export async function fetchCostTrend(params?: {
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<{ items: TrendPoint[] }>('/analytics/cost-trend', {
    params: {
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
    },
  });
  return response.data;
}

export async function fetchClinicalTop(params?: {
  limit?: number;
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<{ items: ClinicalTopItem[] }>('/analytics/clinical-top', {
    params: {
      limit: params?.limit ?? 10,
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
    },
  });
  return response.data;
}

export async function fetchDiseasePriority(params?: {
  limit?: number;
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<{ items: DiseasePriorityItem[] }>('/analytics/disease-priority', {
    params: {
      limit: params?.limit ?? 20,
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
    },
  });
  return response.data;
}

export async function fetchAlertRules() {
  const response = await api.get<{ items: AlertRule[] }>('/alerts/rules');
  return response.data.items;
}

export async function updateAlertRule(payload: {
  ruleCode: string;
  name: string;
  metricType: string;
  yellowThreshold: number;
  orangeThreshold: number;
  redThreshold: number;
  description?: string;
  enabled?: boolean;
}) {
  const response = await api.put<AlertRule>(`/alerts/rules/${payload.ruleCode}`, {
    name: payload.name,
    metric_type: payload.metricType,
    yellow_threshold: payload.yellowThreshold,
    orange_threshold: payload.orangeThreshold,
    red_threshold: payload.redThreshold,
    description: payload.description || undefined,
    enabled: payload.enabled ?? true,
  });
  return response.data;
}

export async function runDetection(limit = 3000) {
  const response = await api.post('/alerts/run-detection', null, { params: { limit } });
  return response.data;
}

export async function fetchRuleHits(payload?: {
  page?: number;
  pageSize?: number;
  severity?: string;
  ruleCode?: string;
}) {
  const response = await api.get<RuleHitList>('/alerts/hits', {
    params: {
      page: payload?.page ?? 1,
      page_size: payload?.pageSize ?? 20,
      severity: payload?.severity || undefined,
      rule_code: payload?.ruleCode || undefined,
    },
  });
  return response.data;
}

export async function fetchWorkOrders(payload?: {
  page?: number;
  pageSize?: number;
  status?: string;
  severity?: string;
}) {
  const response = await api.get<WorkOrderList>('/workorders', {
    params: {
      page: payload?.page ?? 1,
      page_size: payload?.pageSize ?? 20,
      status: payload?.status || undefined,
      severity: payload?.severity || undefined,
    },
  });
  return response.data;
}

export async function assignWorkOrder(payload: { workOrderId: number; assignee: string; remark?: string }) {
  const response = await api.post<WorkOrder>(`/workorders/${payload.workOrderId}/assign`, {
    assignee: payload.assignee,
    remark: payload.remark || undefined,
  });
  return response.data;
}

export async function updateWorkOrderStatus(payload: { workOrderId: number; status: string; remark?: string }) {
  const response = await api.post<WorkOrder>(`/workorders/${payload.workOrderId}/status`, {
    status: payload.status,
    remark: payload.remark || undefined,
  });
  return response.data;
}

export async function runSlaCheck() {
  const response = await api.post('/workorders/sla-check');
  return response.data as { overdue: number; escalated: number };
}

export async function fetchWorkOrderStats() {
  const response = await api.get<WorkOrderStats>('/workorders/stats');
  return response.data;
}

export async function fetchMonthlyReport() {
  const response = await api.get<MonthlyReport>('/reports/monthly');
  return response.data;
}

export async function fetchExecutiveReport() {
  const response = await api.get<ExecutiveBrief>('/reports/executive');
  return response.data;
}

export async function downloadCaseReportCsv() {
  const response = await api.get('/reports/cases.csv', { responseType: 'blob' });
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `cases_${Date.now()}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function fetchDipVersions() {
  const response = await api.get<DipVersionInfo>('/dip/versions');
  return response.data;
}

export async function recalculateDipMappings(limit = 5000) {
  const response = await api.post('/dip/mappings/recalculate', null, { params: { limit } });
  return response.data as { total: number; mapped: number; unmapped: number };
}

export async function fetchDipMappings(payload?: {
  page?: number;
  pageSize?: number;
  status?: string;
}) {
  const path = payload?.status === 'UNMAPPED' ? '/dip/unmapped' : '/dip/mappings';
  const response = await api.get<DipMappingList>(path, {
    params: {
      page: payload?.page ?? 1,
      page_size: payload?.pageSize ?? 20,
      status: payload?.status && payload.status !== 'UNMAPPED' ? payload.status : undefined,
    },
  });
  return response.data;
}

export async function fetchDipStats(payload?: {
  page?: number;
  pageSize?: number;
  pointValueMin?: number;
  pointValueMax?: number;
  multiplierLevel?: 'LOW' | 'NORMAL' | 'HIGH' | 'ULTRA_HIGH' | 'UNKNOWN' | '';
  deptName?: string;
  ratioMinPct?: number;
  ratioMaxPct?: number;
  ungroupedOnly?: boolean;
}) {
  const response = await api.get<DipStatsResponse>('/dip/stats', {
    params: {
      page: payload?.page ?? 1,
      page_size: payload?.pageSize ?? 20,
      point_value_min: payload?.pointValueMin ?? 5,
      point_value_max: payload?.pointValueMax ?? 6,
      multiplier_level: payload?.multiplierLevel || undefined,
      dept_name: payload?.deptName?.trim() || undefined,
      ratio_min_pct: payload?.ratioMinPct ?? undefined,
      ratio_max_pct: payload?.ratioMaxPct ?? undefined,
      ungrouped_only: payload?.ungroupedOnly ? true : undefined,
    },
  });
  return response.data;
}

export async function fetchDipDepartments() {
  const response = await api.get<DipDepartmentList>('/dip/departments');
  return response.data;
}

export async function fetchDirectorTopicOverview(params?: {
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
  topN?: number;
  pointValue?: number;
}) {
  const response = await api.get<DirectorTopicOverviewResponse>('/director/topic', {
    params: {
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
      top_n: params?.topN ?? 5,
      point_value: params?.pointValue ?? undefined,
    },
  });
  return response.data;
}

export async function fetchDirectorTopicDetail(params: {
  diagnosisCode: string;
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
  pointValue?: number;
  doctorMinCases?: number;
  detailTopN?: number;
}) {
  const response = await api.get<DirectorTopicDetailResponse>(`/director/topic/${encodeURIComponent(params.diagnosisCode)}`, {
    params: {
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
      point_value: params?.pointValue ?? undefined,
      doctor_min_cases: params?.doctorMinCases ?? 5,
      detail_top_n: params?.detailTopN ?? 20,
    },
  });
  return response.data;
}

export async function exportDirectorTopicPdf(payload: {
  diagnosisCode: string;
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
  pointValue?: number;
  doctorMinCases?: number;
  charts: DirectorPdfChartPayload[];
}) {
  const response = await api.post(
    `/director/topic/${encodeURIComponent(payload.diagnosisCode)}/export/pdf`,
    {
      dept_name: payload.deptName || undefined,
      date_from: payload.dateFrom || undefined,
      date_to: payload.dateTo || undefined,
      point_value: payload.pointValue ?? undefined,
      doctor_min_cases: payload.doctorMinCases ?? 5,
      charts: payload.charts,
    },
    { responseType: 'blob', timeout: 120000 },
  );
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `director_topic_${payload.diagnosisCode}_${Date.now()}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function manualFillDip(payload: {
  patientId: string;
  dipCode: string;
  note?: string;
  operator?: string;
}) {
  const response = await api.post(`/dip/unmapped/${payload.patientId}/manual-fill`, {
    dip_code: payload.dipCode,
    note: payload.note || undefined,
    operator: payload.operator || undefined,
  });
  return response.data;
}

export async function fetchImportBatches(limit = 20) {
  const response = await api.get<ImportListResponse>('/imports', {
    params: { limit },
  });
  return response.data.items;
}

export async function fetchImportIssues(payload: {
  batchId: string;
  page?: number;
  pageSize?: number;
  severity?: string;
  errorCode?: string;
}) {
  const response = await api.get<ImportIssueList>(`/imports/${payload.batchId}/issues`, {
    params: {
      page: payload.page ?? 1,
      page_size: payload.pageSize ?? 20,
      severity: payload.severity || undefined,
      error_code: payload.errorCode || undefined,
    },
  });
  return response.data;
}

export async function downloadImportIssues(payload: {
  batchId: string;
  format: 'csv' | 'xlsx';
  severity?: string;
  errorCode?: string;
}) {
  const response = await api.get(`/imports/${payload.batchId}/issues.${payload.format}`, {
    params: {
      severity: payload.severity || undefined,
      error_code: payload.errorCode || undefined,
    },
    responseType: 'blob',
  });

  const blob = new Blob([response.data], {
    type:
      payload.format === 'csv'
        ? 'text/csv;charset=utf-8'
        : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `issues_${payload.batchId}.${payload.format}`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function createImportBatch(payload: { importType: ImportType; file: File }) {
  const formData = new FormData();
  formData.append('file', payload.file);
  const response = await api.post<ImportStartResponse>('/imports/start', formData, {
    params: { import_type: payload.importType },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: IMPORT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function createCaseHomeImportBatch(payload: { sourceFile: File }) {
  const formData = new FormData();
  formData.append('source_file', payload.sourceFile);
  const response = await api.post<ImportStartResponse>('/imports/case-home/start', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: IMPORT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function createCaseHomeFilteredImportBatch(payload: { sourceFile: File; filterFile?: File }) {
  return createCaseHomeImportBatch({ sourceFile: payload.sourceFile });
}

export async function downloadCaseCostBackup() {
  const response = await api.get('/imports/backup/case-cost.xlsx', {
    responseType: 'blob',
    timeout: 10 * 60 * 1000,
  });
  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `case_cost_backup_${Date.now()}.xlsx`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function clearCaseCostImportData(confirmText: string) {
  const response = await api.post<ImportDataClearResult>('/imports/clear/case-cost', {
    confirm_text: confirmText,
  });
  return response.data;
}

export async function restoreCaseCostImportData(payload: { file: File; confirmText: string }) {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('confirm_text', payload.confirmText);
  const response = await api.post<ImportDataRestoreResult>('/imports/restore/case-cost', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 10 * 60 * 1000,
  });
  return response.data;
}
