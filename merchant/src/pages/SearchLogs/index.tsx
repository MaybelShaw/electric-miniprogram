import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { getSearchLogs } from '@/services/api';
import type { SearchLog } from '@/services/types';

export default function SearchLogs() {
  const columns: ProColumns<SearchLog>[] = [
    { title: 'ID', dataIndex: 'id', width: 70, hideInSearch: true },
    { title: '关键词', dataIndex: 'keyword' },
    { title: '用户', dataIndex: 'username', hideInSearch: true, renderText: (text, record) => text || (record.user_id ? `用户 #${record.user_id}` : '匿名') },
    { title: '搜索时间', dataIndex: 'created_at', valueType: 'dateTime', width: 170, hideInSearch: true },
  ];

  return (
    <ProTable<SearchLog>
      headerTitle="搜索日志"
      columns={columns}
      rowKey="id"
      request={async (params) => {
        const { current, pageSize, ...rest } = params;
        const res: any = await getSearchLogs({ page: current, page_size: pageSize, ...rest });
        const data = Array.isArray(res) ? res : res.results || [];
        return { data, success: true, total: res.count || data.length };
      }}
    />
  );
}
