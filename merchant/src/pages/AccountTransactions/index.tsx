import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { Tag, Button, message } from 'antd';
import { useRef, useState } from 'react';
import { getAccountTransactions, exportAccountTransactions } from '@/services/api';
import { useLocation } from 'react-router-dom';
import { DownloadOutlined } from '@ant-design/icons';
import { downloadBlob } from '@/utils/download';
import ExportLoadingModal from '@/components/ExportLoadingModal';

export default function AccountTransactions() {
  const actionRef = useRef<ActionType>();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const creditAccountId = queryParams.get('credit_account');
  const [exportParams, setExportParams] = useState<Record<string, any>>({});
  const [exporting, setExporting] = useState(false);
  const exportLockRef = useRef(false);

  const handleExport = async () => {
    if (exportLockRef.current) return;
    exportLockRef.current = true;
    setExporting(true);
    try {
      const res: any = await exportAccountTransactions(exportParams);
      const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
      downloadBlob(res, `transactions_${timestamp}.xlsx`);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    } finally {
      exportLockRef.current = false;
      setExporting(false);
    }
  };

  const columns: ProColumns<any>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      search: false,
    },
    {
      title: '经销商',
      dataIndex: 'user_name',
      width: 150,
      render: (_, record) => record.credit_account_info?.user_name || '-',
    },
    {
      title: '公司名称',
      dataIndex: 'company_name',
      width: 200,
      render: (_, record) => record.credit_account_info?.company_name || '-',
    },
    {
      title: '交易类型',
      dataIndex: 'transaction_type',
      width: 100,
      valueType: 'select',
      valueEnum: {
        purchase: { text: '采购', status: 'Processing' },
        payment: { text: '付款', status: 'Success' },
        refund: { text: '退款', status: 'Warning' },
        adjustment: { text: '调整', status: 'Default' },
      },
    },
    {
      title: '金额',
      dataIndex: 'amount',
      width: 120,
      search: false,
      render: (_, record) => (
        <span style={{ color: ['payment', 'refund'].includes(record.transaction_type) ? '#52c41a' : '#ff4d4f' }}>
          {['payment', 'refund'].includes(record.transaction_type) ? '+' : '-'}{Number(record.amount).toLocaleString()}
        </span>
      ),
    },
    {
      title: '变动后余额',
      dataIndex: 'balance_after',
      width: 120,
      search: false,
      render: (_, record) => `¥${Number(record.balance_after).toLocaleString()}`,
    },
    {
      title: '订单ID',
      dataIndex: 'order_id',
      width: 100,
    },
    {
      title: '付款状态',
      dataIndex: 'payment_status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        unpaid: { text: '未付款', status: 'Warning' },
        paid: { text: '已付款', status: 'Success' },
        overdue: { text: '已逾期', status: 'Error' },
      },
      render: (_, record) => {
        if (record.transaction_type !== 'purchase') return '-';
        const colorMap: any = {
          unpaid: 'orange',
          paid: 'green',
          overdue: 'red',
        };
        const textMap: any = {
          unpaid: '未付款',
          paid: '已付款',
          overdue: '已逾期',
        };
        return <Tag color={colorMap[record.payment_status]}>{textMap[record.payment_status]}</Tag>;
      },
    },
    {
      title: '应付日期',
      dataIndex: 'due_date',
      width: 120,
      valueType: 'date',
      search: false,
    },
    {
      title: '交易时间',
      dataIndex: 'created_at',
      width: 180,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '备注',
      dataIndex: 'description',
      width: 200,
      search: false,
    },
  ];

  return (
    <>
      <ProTable<any>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const requestParams: any = {
            page: params.current,
            page_size: params.pageSize,
            transaction_type: params.transaction_type,
            payment_status: params.payment_status,
            search: params.user_name || params.company_name,
          };
          
          if (creditAccountId) {
            requestParams.credit_account = creditAccountId;
          }
          
          if (params.user_name) requestParams.search = params.user_name;
          if (params.company_name) requestParams.search = params.company_name;

          const exportQuery = { ...requestParams };
          delete exportQuery.page;
          delete exportQuery.page_size;
          setExportParams(exportQuery);

          const response: any = await getAccountTransactions(requestParams);
          return {
            data: response.results,
            success: true,
            total: response.pagination?.total || response.total || response.count || 0,
          };
        }}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
        toolBarRender={() => [
          <Button key="export" icon={<DownloadOutlined />} onClick={handleExport} loading={exporting} disabled={exporting}>
            导出
          </Button>,
        ]}
        dateFormatter="string"
        headerTitle={creditAccountId ? "交易记录 (特定账户)" : "交易记录管理"}
        scroll={{ x: 1500 }}
      />
      <ExportLoadingModal open={exporting} />
    </>
  );
}
