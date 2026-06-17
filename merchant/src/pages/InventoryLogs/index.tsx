import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { getInventoryLogs, getProducts } from '@/services/api';
import type { InventoryLog, Product } from '@/services/types';
import { fetchAllPaginated } from '@/utils/request';

export default function InventoryLogs() {
  const columns: ProColumns<InventoryLog>[] = [
    { title: 'ID', dataIndex: 'id', width: 70, hideInSearch: true },
    {
      title: '商品',
      dataIndex: 'product',
      valueType: 'select',
      request: async () => {
        const products = await fetchAllPaginated<Product>(getProducts, {}, 100);
        return products.map(product => ({ label: `${product.name} (#${product.id})`, value: product.id }));
      },
      render: (_, record) => record.product_name,
    },
    { title: 'SKU', dataIndex: 'sku_name', hideInSearch: true, renderText: (text, record) => text || (record.sku ? `SKU #${record.sku}` : '-') },
    {
      title: '变更类型',
      dataIndex: 'change_type',
      valueType: 'select',
      valueEnum: {
        lock: { text: '锁定', status: 'Processing' },
        release: { text: '释放', status: 'Default' },
        adjust: { text: '调整', status: 'Warning' },
      },
      width: 110,
    },
    { title: '数量', dataIndex: 'quantity', width: 90, hideInSearch: true },
    { title: '原因', dataIndex: 'reason', hideInSearch: true },
    { title: '操作人', dataIndex: 'created_by_username', hideInSearch: true },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', width: 170, hideInSearch: true },
  ];

  return (
    <ProTable<InventoryLog>
      headerTitle="库存日志"
      columns={columns}
      rowKey="id"
      request={async (params) => {
        const { current, pageSize, ...rest } = params;
        const res: any = await getInventoryLogs({ page: current, page_size: pageSize, ...rest });
        const data = Array.isArray(res) ? res : res.results || [];
        return { data, success: true, total: res.count || data.length };
      }}
    />
  );
}
