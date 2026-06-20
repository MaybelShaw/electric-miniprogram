import { useEffect, useRef, useState } from 'react';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ModalForm, ProFormTextArea, ProTable } from '@ant-design/pro-components';
import { Button, Result, Spin, Tag, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import {
  getCurrentStoreContext,
  getProfitSharingEntries,
  getStores,
  markProfitSharingEntriesAvailable,
  markProfitSharingEntryManualSettled,
} from '@/services/api';
import type { CurrentStoreContext, Store, StoreProfitSharingEntry } from '@/services/types';
import { getSelectedStoreId } from '@/utils/store';

const entryStatusMap: Record<string, { text: string; color: string }> = {
  platform_retained: { text: '平台留存', color: 'default' },
  pending_receiver_config: { text: '待补充信息', color: 'orange' },
  frozen: { text: '冻结中', color: 'blue' },
  available: { text: '可结算', color: 'green' },
  available_for_manual_share: { text: '可结算', color: 'green' },
  processing: { text: '处理中', color: 'processing' },
  shared: { text: '已结算', color: 'success' },
  failed: { text: '结算失败', color: 'error' },
  manual_settled: { text: '人工已结算', color: 'purple' },
  manual_settlement_required: { text: '需人工结算', color: 'red' },
  cancelled: { text: '已取消', color: 'default' },
};

const manualSettleStatuses = new Set([
  'available',
  'available_for_manual_share',
  'failed',
  'manual_settlement_required',
  'pending_receiver_config',
  'cancelled',
]);

const formatMoney = (value: string | number | null | undefined) => {
  const amount = Number(value || 0);
  return `¥${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const getTotal = (response: any, fallbackLength: number) =>
  response?.pagination?.total || response?.total || response?.count || fallbackLength;

export default function ProfitSharing() {
  const entryActionRef = useRef<ActionType>();
  const [storeContext, setStoreContext] = useState<CurrentStoreContext | null>(null);
  const [contextLoaded, setContextLoaded] = useState(false);
  const [manualSettleEntry, setManualSettleEntry] = useState<StoreProfitSharingEntry | null>(null);

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

  const reloadEntries = () => {
    entryActionRef.current?.reload();
  };

  const handleMarkAvailable = async () => {
    try {
      const response = await markProfitSharingEntriesAvailable();
      message.success(`已更新 ${response.updated || 0} 条到期流水`);
      reloadEntries();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新到期流水失败');
    }
  };

  const entryColumns: ProColumns<StoreProfitSharingEntry>[] = [
    { title: 'ID', dataIndex: 'id', width: 80, search: false },
    {
      title: '结算单ID',
      dataIndex: 'checkout_order',
      width: 110,
      fieldProps: { precision: 0, placeholder: '输入结算单ID' },
    },
    { title: '结算单号', dataIndex: 'checkout_number', width: 180, search: false, copyable: true },
    { title: '子单号', dataIndex: 'suborder_number', width: 180, search: false, copyable: true },
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
      title: '平台抽佣',
      dataIndex: 'commission_amount',
      width: 100,
      search: false,
      render: (_, record) => formatMoney(record.commission_amount),
    },
    {
      title: '店铺应结算',
      dataIndex: 'sharing_amount',
      width: 120,
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
    { title: '收款账号', dataIndex: 'receiver_account', width: 170, search: false, ellipsis: true },
    { title: '收款方名称', dataIndex: 'receiver_name_snapshot', width: 150, search: false, ellipsis: true },
    { title: '可结算时间', dataIndex: 'available_at', width: 170, valueType: 'dateTime', search: false },
    { title: '结算时间', dataIndex: 'shared_at', width: 170, valueType: 'dateTime', search: false },
    { title: '失败原因', dataIndex: 'failure_reason', width: 200, search: false, ellipsis: true },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, record) => [
        manualSettleStatuses.has(record.status) && (
          <a key="manual-settle" onClick={() => setManualSettleEntry(record)}>
            标记已结算
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
        subTitle="店铺分账仅平台管理员可操作。"
      />
    );
  }

  if (currentStore?.is_main !== true) {
    return (
      <Result
        status="403"
        title="无权访问"
        subTitle="店铺分账仅主店铺可操作。"
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
        headerTitle="店铺分账"
        toolBarRender={() => [
          <Button key="available" icon={<ReloadOutlined />} onClick={handleMarkAvailable}>
            更新到期流水
          </Button>,
        ]}
        scroll={{ x: 1900 }}
      />

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
            reloadEntries();
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
          placeholder="填写人工结算凭证、线下转账信息或处理说明"
          fieldProps={{ rows: 4 }}
        />
      </ModalForm>
    </>
  );
}
