import { useEffect, useRef, useState } from 'react';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ModalForm, ProFormSwitch, ProFormTextArea, ProTable } from '@ant-design/pro-components';
import { Button, Modal, Result, Space, Spin, Tag, message } from 'antd';
import { CheckCircleOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons';
import {
  getCurrentStoreContext,
  getProfitSharingEntries,
  getStores,
  getWechatProfitSharingOrders,
  markProfitSharingEntriesAvailable,
  markProfitSharingEntryManualSettled,
  markWechatProfitSharingOrderFailed,
  markWechatProfitSharingOrderSucceeded,
  shareProfitSharingEntries,
} from '@/services/api';
import type {
  CurrentStoreContext,
  Store,
  StoreProfitSharingEntry,
  WechatProfitSharingOrder,
} from '@/services/types';
import { getSelectedStoreId } from '@/utils/store';

const entryStatusMap: Record<string, { text: string; color: string }> = {
  platform_retained: { text: '平台留存', color: 'default' },
  pending_receiver_config: { text: '待配置接收方', color: 'orange' },
  frozen: { text: '冻结中', color: 'blue' },
  available: { text: '可分账', color: 'green' },
  available_for_manual_share: { text: '可手动分账', color: 'green' },
  processing: { text: '处理中', color: 'processing' },
  shared: { text: '分账成功', color: 'success' },
  failed: { text: '分账失败', color: 'error' },
  manual_settled: { text: '人工结算', color: 'purple' },
  manual_settlement_required: { text: '需人工结算', color: 'red' },
  cancelled: { text: '已取消', color: 'default' },
};

const shareOrderStatusMap: Record<string, { text: string; color: string }> = {
  processing: { text: '处理中', color: 'processing' },
  shared: { text: '分账成功', color: 'success' },
  failed: { text: '分账失败', color: 'error' },
  closed: { text: '已关闭', color: 'default' },
};

const shareableStatuses = new Set(['available', 'available_for_manual_share', 'failed']);
const manualSettleStatuses = new Set(['failed', 'manual_settlement_required', 'pending_receiver_config', 'cancelled']);

const formatMoney = (value: string | number | null | undefined) => {
  const amount = Number(value || 0);
  return `¥${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const getTotal = (response: any, fallbackLength: number) =>
  response?.pagination?.total || response?.total || response?.count || fallbackLength;

export default function ProfitSharing() {
  const entryActionRef = useRef<ActionType>();
  const orderActionRef = useRef<ActionType>();
  const [storeContext, setStoreContext] = useState<CurrentStoreContext | null>(null);
  const [contextLoaded, setContextLoaded] = useState(false);
  const [selectedRows, setSelectedRows] = useState<StoreProfitSharingEntry[]>([]);
  const [shareEntryIds, setShareEntryIds] = useState<number[]>([]);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [manualSettleEntry, setManualSettleEntry] = useState<StoreProfitSharingEntry | null>(null);
  const [failShareOrder, setFailShareOrder] = useState<WechatProfitSharingOrder | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCurrentStoreContext()
      .then((context) => {
        if (!cancelled) {
          setStoreContext(context);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStoreContext(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setContextLoaded(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const reloadTables = () => {
    entryActionRef.current?.reload();
    orderActionRef.current?.reload();
  };

  const openShareModal = (entryIds: number[]) => {
    setShareEntryIds(entryIds);
    setShareModalOpen(true);
  };

  const handleMarkAvailable = async () => {
    try {
      const response = await markProfitSharingEntriesAvailable();
      message.success(`已更新 ${response.updated || 0} 条到期流水`);
      entryActionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新可分账流水失败');
    }
  };

  const handleBatchShare = () => {
    if (selectedRows.length === 0) {
      message.warning('请选择可分账流水');
      return;
    }
    const paymentIds = new Set(selectedRows.map((row) => row.payment));
    if (paymentIds.size > 1) {
      message.error('一次只能处理同一支付单下的分账流水');
      return;
    }
    openShareModal(selectedRows.map((row) => row.id));
  };

  const entryColumns: ProColumns<StoreProfitSharingEntry>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    {
      title: '结算单ID',
      dataIndex: 'checkout_order',
      width: 110,
      fieldProps: { precision: 0, placeholder: '输入结算单ID' },
    },
    {
      title: '结算单号',
      dataIndex: 'checkout_number',
      width: 180,
      search: false,
      copyable: true,
    },
    {
      title: '子单号',
      dataIndex: 'suborder_number',
      width: 180,
      search: false,
      copyable: true,
    },
    {
      title: '店铺',
      dataIndex: 'store',
      width: 160,
      valueType: 'select',
      request: async () => {
        const response: any = await getStores({ page: 1, page_size: 200 });
        const stores: Store[] = Array.isArray(response) ? response : response.results || [];
        return stores.map((store) => ({ label: store.name, value: store.id }));
      },
      render: (_, record) => record.store_name || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 130,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(entryStatusMap).map(([key, item]) => [key, { text: item.text }]),
      ),
      render: (_, record) => {
        const item = entryStatusMap[record.status] || { text: record.status, color: 'default' };
        return <Tag color={item.color}>{item.text}</Tag>;
      },
    },
    {
      title: '子单实付',
      dataIndex: 'gross_amount',
      width: 110,
      search: false,
      render: (_, record) => formatMoney(record.gross_amount),
    },
    {
      title: '抽佣比例',
      dataIndex: 'commission_rate_snapshot',
      width: 100,
      search: false,
      render: (_, record) => `${Number(record.commission_rate_snapshot || 0).toFixed(2)}%`,
    },
    {
      title: '抽佣',
      dataIndex: 'commission_amount',
      width: 100,
      search: false,
      render: (_, record) => formatMoney(record.commission_amount),
    },
    {
      title: '分账金额',
      dataIndex: 'sharing_amount',
      width: 110,
      search: false,
      render: (_, record) => formatMoney(record.sharing_amount),
    },
    {
      title: '平台留存',
      dataIndex: 'retained_amount',
      width: 110,
      search: false,
      render: (_, record) => formatMoney(record.retained_amount),
    },
    { title: '接收方账号', dataIndex: 'receiver_account', width: 170, search: false, ellipsis: true },
    { title: '接收方名称', dataIndex: 'receiver_name_snapshot', width: 150, search: false, ellipsis: true },
    { title: '可分账时间', dataIndex: 'available_at', width: 170, valueType: 'dateTime', search: false },
    { title: '分账成功时间', dataIndex: 'shared_at', width: 170, valueType: 'dateTime', search: false },
    {
      title: '失败原因',
      dataIndex: 'failure_reason',
      width: 200,
      search: false,
      ellipsis: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => [
        shareableStatuses.has(record.status) && (
          <a key="share" onClick={() => openShareModal([record.id])}>
            发起分账
          </a>
        ),
        manualSettleStatuses.has(record.status) && (
          <a key="manual-settle" onClick={() => setManualSettleEntry(record)}>
            人工结算
          </a>
        ),
      ],
    },
  ];

  const shareOrderColumns: ProColumns<WechatProfitSharingOrder>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    { title: '分账单号', dataIndex: 'out_order_no', width: 220, search: false, copyable: true },
    { title: '支付记录ID', dataIndex: 'payment', width: 110, search: false },
    { title: '结算单ID', dataIndex: 'checkout_order', width: 110, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(shareOrderStatusMap).map(([key, item]) => [key, { text: item.text }]),
      ),
      render: (_, record) => {
        const item = shareOrderStatusMap[record.status] || { text: record.status, color: 'default' };
        return <Tag color={item.color}>{item.text}</Tag>;
      },
    },
    {
      title: '分账金额',
      dataIndex: 'amount',
      width: 120,
      search: false,
      render: (_, record) => formatMoney(record.amount),
    },
    {
      title: '解冻剩余资金',
      dataIndex: 'unfreeze_unsplit',
      width: 120,
      search: false,
      render: (_, record) => (record.unfreeze_unsplit ? <Tag color="orange">是</Tag> : <Tag>否</Tag>),
    },
    { title: '关联流水', dataIndex: 'entry_ids', width: 150, search: false, render: (_, record) => record.entry_ids.join(', ') },
    { title: '微信交易号', dataIndex: 'transaction_id', width: 190, search: false, copyable: true, ellipsis: true },
    { title: '错误信息', dataIndex: 'error_message', width: 220, search: false, ellipsis: true },
    { title: '创建时间', dataIndex: 'created_at', width: 170, valueType: 'dateTime', search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      fixed: 'right',
      render: (_, record) => [
        record.status !== 'shared' && (
          <a
            key="success"
            onClick={() => {
              Modal.confirm({
                title: '确认标记为分账成功？',
                content: '仅在已确认微信侧分账成功或联调环境需要手动同步时使用。',
                onOk: async () => {
                  await markWechatProfitSharingOrderSucceeded(record.id);
                  message.success('已标记分账成功');
                  reloadTables();
                },
              });
            }}
          >
            标记成功
          </a>
        ),
        record.status === 'processing' && (
          <a key="failed" onClick={() => setFailShareOrder(record)}>
            标记失败
          </a>
        ),
      ],
    },
  ];

  const selectedStoreId = getSelectedStoreId();
  const currentStore = storeContext?.stores.find((store) => store.id === selectedStoreId)
    || storeContext?.default_store
    || storeContext?.stores[0];

  if (!contextLoaded) {
    return <Spin />;
  }

  if (!storeContext?.is_platform_admin) {
    return (
      <Result
        status="403"
        title="无权访问"
        subTitle="手动分账仅平台管理员可操作。"
      />
    );
  }

  if (currentStore?.is_main !== true) {
    return (
      <Result
        status="403"
        title="无权访问"
        subTitle="手动分账仅主店铺可操作。"
      />
    );
  }

  return (
    <>
      <ProTable<StoreProfitSharingEntry>
        columns={entryColumns}
        actionRef={entryActionRef}
        rowKey="id"
        request={async (params) => {
          const requestParams: Record<string, any> = {
            page: params.current,
            page_size: params.pageSize,
            status: params.status,
            checkout_order: params.checkout_order,
            store: params.store,
          };
          const response: any = await getProfitSharingEntries(requestParams);
          const data = Array.isArray(response) ? response : response.results || [];
          return { data, success: true, total: getTotal(response, data.length) };
        }}
        rowSelection={{
          selectedRowKeys: selectedRows.map((row) => row.id),
          preserveSelectedRowKeys: false,
          getCheckboxProps: (record) => ({ disabled: !shareableStatuses.has(record.status) }),
          onChange: (_, rows) => setSelectedRows(rows),
        }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
          collapseRender: false,
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
        dateFormatter="string"
        headerTitle="手动分账"
        toolBarRender={() => [
          <Button key="available" icon={<ReloadOutlined />} onClick={handleMarkAvailable}>
            更新到期流水
          </Button>,
          <Button key="batch-share" type="primary" icon={<SendOutlined />} onClick={handleBatchShare}>
            批量发起分账
          </Button>,
        ]}
        scroll={{ x: 2100 }}
      />

      <ProTable<WechatProfitSharingOrder>
        columns={shareOrderColumns}
        actionRef={orderActionRef}
        rowKey="id"
        request={async (params) => {
          const response: any = await getWechatProfitSharingOrders({
            page: params.current,
            page_size: params.pageSize,
            status: params.status,
          });
          const data = Array.isArray(response) ? response : response.results || [];
          return { data, success: true, total: getTotal(response, data.length) };
        }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
          collapseRender: false,
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
        dateFormatter="string"
        headerTitle="微信分账请求记录"
        toolBarRender={() => [
          <Button key="reload" icon={<CheckCircleOutlined />} onClick={reloadTables}>
            刷新
          </Button>,
        ]}
        scroll={{ x: 1600 }}
        style={{ marginTop: 24 }}
      />

      <ModalForm
        title="发起微信分账"
        open={shareModalOpen}
        width={520}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={(open) => {
          setShareModalOpen(open);
          if (!open) {
            setShareEntryIds([]);
          }
        }}
        onFinish={async (values) => {
          try {
            await shareProfitSharingEntries({
              entry_ids: shareEntryIds,
              unfreeze_unsplit: Boolean(values.unfreeze_unsplit),
            });
            message.success('已发起微信分账');
            setShareModalOpen(false);
            setSelectedRows([]);
            reloadTables();
            return true;
          } catch (error: any) {
            message.error(error?.response?.data?.detail || '发起分账失败');
            return false;
          }
        }}
      >
        <Space direction="vertical" size={12}>
          <span>将对 {shareEntryIds.length} 条流水发起微信分账。一次只能处理同一支付单下的流水。</span>
          <ProFormSwitch
            name="unfreeze_unsplit"
            label="同时解冻剩余未分资金"
            initialValue={false}
          />
        </Space>
      </ModalForm>

      <ModalForm
        title="标记人工结算"
        open={Boolean(manualSettleEntry)}
        width={520}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={(open) => {
          if (!open) {
            setManualSettleEntry(null);
          }
        }}
        onFinish={async (values) => {
          if (!manualSettleEntry) return false;
          try {
            await markProfitSharingEntryManualSettled(manualSettleEntry.id, { note: values.note });
            message.success('已标记人工结算');
            setManualSettleEntry(null);
            reloadTables();
            return true;
          } catch (error: any) {
            message.error(error?.response?.data?.detail || '标记人工结算失败');
            return false;
          }
        }}
      >
        <ProFormTextArea
          name="note"
          label="处理备注"
          placeholder="填写人工结算原因、凭证或线下处理说明"
          fieldProps={{ rows: 4 }}
        />
      </ModalForm>

      <ModalForm
        title="标记分账失败"
        open={Boolean(failShareOrder)}
        width={520}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={(open) => {
          if (!open) {
            setFailShareOrder(null);
          }
        }}
        onFinish={async (values) => {
          if (!failShareOrder) return false;
          try {
            await markWechatProfitSharingOrderFailed(failShareOrder.id, { error_message: values.error_message });
            message.success('已标记分账失败');
            setFailShareOrder(null);
            reloadTables();
            return true;
          } catch (error: any) {
            message.error(error?.response?.data?.detail || '标记分账失败失败');
            return false;
          }
        }}
      >
        <ProFormTextArea
          name="error_message"
          label="失败原因"
          rules={[{ required: true, message: '请输入失败原因' }]}
          fieldProps={{ rows: 4 }}
        />
      </ModalForm>
    </>
  );
}
