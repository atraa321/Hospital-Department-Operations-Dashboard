import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  assignWorkOrder,
  fetchWorkOrderStats,
  fetchWorkOrders,
  runSlaCheck,
  updateWorkOrderStatus,
} from '../lib/api';

export function WorkOrderPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');

  const listQuery = useQuery({
    queryKey: ['workorders', page, status],
    queryFn: () => fetchWorkOrders({ page, pageSize: 15, status }),
  });
  const statsQuery = useQuery({
    queryKey: ['workorder-stats'],
    queryFn: fetchWorkOrderStats,
  });

  const statusMutation = useMutation({
    mutationFn: updateWorkOrderStatus,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workorders'] });
      queryClient.invalidateQueries({ queryKey: ['workorder-stats'] });
    },
  });
  const assignMutation = useMutation({
    mutationFn: assignWorkOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workorders'] });
    },
  });
  const slaMutation = useMutation({
    mutationFn: runSlaCheck,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workorders'] });
      queryClient.invalidateQueries({ queryKey: ['workorder-stats'] });
    },
  });

  const onAssign = (id: number) => {
    const assignee = window.prompt('指派给（账号）');
    if (!assignee) {
      return;
    }
    assignMutation.mutate({ workOrderId: id, assignee, remark: '手动指派' });
  };

  const onFlow = (id: number, nextStatus: string) => {
    const remark = window.prompt('状态说明（可空）') ?? '';
    statusMutation.mutate({ workOrderId: id, status: nextStatus, remark });
  };

  const totalPages = Math.max(1, Math.ceil((listQuery.data?.total ?? 0) / (listQuery.data?.page_size ?? 15)));

  return (
    <section className="dashboard-grid">
      <div className="metrics-row">
        <div className="metric-card">
          <p className="metric-label">总工单</p>
          <p className="metric-value">{statsQuery.data?.total ?? 0}</p>
        </div>
        <div className="metric-card metric-card--good">
          <p className="metric-label">闭环率</p>
          <p className="metric-value">{statsQuery.data?.close_rate ?? 0}%</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">按期率</p>
          <p className="metric-value">{statsQuery.data?.on_time_rate ?? 0}%</p>
        </div>
      </div>

      <article className="panel panel--wide">
        <header className="panel-head">
          <h2>预警工单看板</h2>
          <p>待处理 / 处理中 / 复核 / 关闭</p>
        </header>
        <div className="issue-toolbar">
          <label className="field field--compact">
            <span>状态</span>
            <select
              value={status}
              onChange={(event) => {
                setPage(1);
                setStatus(event.target.value);
              }}
            >
              <option value="">全部</option>
              <option value="TODO">TODO</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="REVIEW">REVIEW</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </label>
          <button className="btn-secondary" onClick={() => slaMutation.mutate()} type="button">
            SLA检查
          </button>
          <span>{slaMutation.data ? `逾期 ${slaMutation.data.overdue}，升级 ${slaMutation.data.escalated}` : ''}</span>
        </div>
        <div className="table-wrap issue-table">
          <table>
            <thead>
              <tr>
                <th>工单号</th>
                <th>规则</th>
                <th>住院号</th>
                <th>级别</th>
                <th>状态</th>
                <th>责任人</th>
                <th>截止</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {listQuery.data?.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.order_no}</td>
                  <td>{item.rule_code || '-'}</td>
                  <td>{item.patient_id || '-'}</td>
                  <td>{item.severity}</td>
                  <td>{item.status}</td>
                  <td>{item.assignee || '-'}</td>
                  <td>{item.due_at ? new Date(item.due_at).toLocaleDateString() : '-'}</td>
                  <td className="cell-actions">
                    <button className="btn-secondary" onClick={() => onAssign(item.id)} type="button">
                      指派
                    </button>
                    <button className="btn-secondary" onClick={() => onFlow(item.id, 'IN_PROGRESS')} type="button">
                      处理中
                    </button>
                    <button className="btn-secondary" onClick={() => onFlow(item.id, 'REVIEW')} type="button">
                      复核
                    </button>
                    <button className="btn-secondary" onClick={() => onFlow(item.id, 'CLOSED')} type="button">
                      关闭
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pager-row">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} type="button">
            上一页
          </button>
          <span>
            第 {page}/{totalPages} 页，共 {listQuery.data?.total ?? 0} 条
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
