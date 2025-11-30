import { useRef } from 'react';
import { ProTable, ProDescriptions, ModalForm, ProFormText } from '@ant-design/pro-components';
import { Tag, Button, message, Space, Popconfirm, Drawer, Modal, Form, Input } from 'antd';
import { EyeOutlined, SendOutlined, CheckOutlined, CloseOutlined, CloudUploadOutlined, CarOutlined } from '@ant-design/icons';
import { getOrders, getOrder, shipOrder, completeOrder, cancelOrder, pushToHaier, getHaierLogistics } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { useState } from 'react';
import type { Order } from '@/services/types';

const statusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '待支付', color: 'orange' },
  paid: { text: '已支付', color: 'blue' },
  shipped: { text: '已发货', color: 'cyan' },
  completed: { text: '已完成', color: 'green' },
  cancelled: { text: '已取消', color: 'red' },
  refunding: { text: '退款中', color: 'purple' },
  refunded: { text: '已退款', color: 'magenta' },
};

export default function Orders() {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentOrder, setCurrentOrder] = useState<Order | null>(null);
  const [pushModalVisible, setPushModalVisible] = useState(false);
  const [pushForm] = Form.useForm();
  const [pushing, setPushing] = useState(false);
  const [logisticsModalVisible, setLogisticsModalVisible] = useState(false);
  const [logisticsData, setLogisticsData] = useState<any>(null);
  const [loadingLogistics, setLoadingLogistics] = useState(false);
  const [shipModalVisible, setShipModalVisible] = useState(false);
  const [shippingOrder, setShippingOrder] = useState<Order | null>(null);

  const handleShip = (record: Order) => {
    setShippingOrder(record);
    setShipModalVisible(true);
  };

  const handleShipSubmit = async (values: any) => {
    try {
      if (!shippingOrder) return false;
      await shipOrder(shippingOrder.id, values);
      message.success('发货成功');
      setShipModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
      return false;
    }
  };

  const handleComplete = async (id: number) => {
    try {
      await completeOrder(id);
      message.success('完成订单');
      actionRef.current?.reload();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await cancelOrder(id);
      message.success('取消成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleViewDetail = async (record: Order) => {
    try {
      const res: any = await getOrder(record.id);
      setCurrentOrder(res);
      setDetailVisible(true);
    } catch (error) {
      message.error('获取订单详情失败');
    }
  };

  const handlePushToHaier = (record: Order) => {
    setCurrentOrder(record);
    pushForm.setFieldsValue({
      source_system: 'MERCHANT_ADMIN',
      shop_name: '默认店铺',
    });
    setPushModalVisible(true);
  };

  const handlePushSubmit = async () => {
    try {
      const values = await pushForm.validateFields();
      setPushing(true);
      if (currentOrder) {
        await pushToHaier(currentOrder.id, values);
        message.success('推送成功');
        setPushModalVisible(false);
        actionRef.current?.reload();
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '推送失败');
    } finally {
      setPushing(false);
    }
  };

  const handleViewLogistics = async (record: Order) => {
    try {
      setLoadingLogistics(true);
      setLogisticsModalVisible(true);
      const res: any = await getHaierLogistics(record.id);
      setLogisticsData(res.logistics_info);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '查询物流失败');
      setLogisticsModalVisible(false);
    } finally {
      setLoadingLogistics(false);
    }
  };

  const columns: ProColumns<Order>[] = [
    { 
      title: '订单号', 
      dataIndex: 'order_number', 
      width: 180,
      copyable: true,
      ellipsis: true,
    },
    { 
      title: '用户名', 
      dataIndex: 'user_username', 
      width: 120,
    },
    { 
      title: '商品名称', 
      dataIndex: ['product', 'name'],
      ellipsis: true,
      hideInSearch: true,
    },
    {
      title: '商品搜索',
      dataIndex: 'product_name',
      hideInTable: true,
    },
    { 
      title: '数量', 
      dataIndex: 'quantity', 
      hideInSearch: true, 
      width: 80,
    },
    { 
      title: '总金额', 
      dataIndex: 'total_amount', 
      hideInSearch: true, 
      width: 120,
      render: (amount) => `¥${amount}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        pending: { text: '待支付' },
        paid: { text: '已支付' },
        shipped: { text: '已发货' },
        completed: { text: '已完成' },
        cancelled: { text: '已取消' },
        refunding: { text: '退款中' },
        refunded: { text: '已退款' },
      },
      render: (_, record) => {
        const status = statusMap[record.status];
        return <Tag color={status?.color}>{status?.text}</Tag>;
      },
    },
    {
      title: '海尔订单',
      dataIndex: 'is_haier_order',
      width: 100,
      hideInSearch: true,
      render: (_, record) => {
        if (!record.is_haier_order) return <Tag>否</Tag>;
        const hasPushed = record.haier_order_info?.haier_so_id;
        return (
          <Space direction="vertical" size={0}>
            <Tag color="blue">是</Tag>
            {hasPushed ? (
              <Tag color="green" style={{ fontSize: 11 }}>已推送</Tag>
            ) : (
              <Tag color="orange" style={{ fontSize: 11 }}>未推送</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: '收货人',
      dataIndex: 'snapshot_contact_name',
      width: 100,
      hideInSearch: true,
    },
    {
      title: '联系电话',
      dataIndex: 'snapshot_phone',
      width: 120,
      hideInSearch: true,
    },
    {
      title: '收货地址',
      dataIndex: 'snapshot_address',
      ellipsis: true,
      hideInSearch: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      valueType: 'dateTime',
      hideInSearch: true,
    },
    {
      title: '创建时间范围',
      dataIndex: 'created_at',
      valueType: 'dateRange',
      hideInTable: true,
      search: {
        transform: (value: any) => {
          return {
            created_after: value[0],
            created_before: value[1],
          };
        },
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 280,
      fixed: 'right',
      render: (_, record) => {
        const actions = [
          <Button
            key="view"
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            查看
          </Button>
        ];
        
        // 海尔订单相关操作
        const isHaierOrder = record.is_haier_order;
        const hasPushed = record.haier_order_info?.haier_so_id;
        
        if (isHaierOrder && !hasPushed && record.status === 'paid') {
          actions.push(
            <Button
              key="push"
              type="link"
              size="small"
              icon={<CloudUploadOutlined />}
              onClick={() => handlePushToHaier(record)}
            >
              推送海尔
            </Button>
          );
        }
        
        if (isHaierOrder && hasPushed) {
          actions.push(
            <Button
              key="logistics"
              type="link"
              size="small"
              icon={<CarOutlined />}
              onClick={() => handleViewLogistics(record)}
            >
              查询物流
            </Button>
          );
        }
        
        if (record.status === 'paid') {
          actions.push(
            <Button
              key="ship"
              type="link"
              size="small"
              icon={<SendOutlined />}
              onClick={() => handleShip(record)}
            >
              发货
            </Button>
          );
        }
        
        if (record.status === 'shipped') {
          actions.push(
            <Popconfirm
              key="complete"
              title="确认完成订单?"
              onConfirm={() => handleComplete(record.id)}
            >
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
              >
                完成
              </Button>
            </Popconfirm>
          );
        }
        
        if (['pending', 'paid'].includes(record.status)) {
          actions.push(
            <Popconfirm
              key="cancel"
              title="确认取消订单?"
              description="取消后无法恢复"
              onConfirm={() => handleCancel(record.id)}
            >
              <Button
                type="link"
                size="small"
                danger
                icon={<CloseOutlined />}
              >
                取消
              </Button>
            </Popconfirm>
          );
        }
        
        return <Space size={0}>{actions}</Space>;
      },
    },
  ];

  return (
    <>
      <ProTable
        headerTitle="订单列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params: any) => {
          try {
            const queryParams: any = {
              page: params.current || 1,
              page_size: params.pageSize || 20,
            };

            // 订单号搜索
            if (params.order_number) {
              queryParams.order_number = params.order_number;
            }

            // 用户名搜索
            if (params.user_username) {
              queryParams.username = params.user_username;
            }

            // 商品名称搜索
            if (params.product_name) {
              queryParams.product_name = params.product_name;
            }

            // 状态筛选
            if (params.status) {
              queryParams.status = params.status;
            }

            // 创建时间范围
            if (params.created_after) {
              queryParams.created_after = params.created_after;
            }
            if (params.created_before) {
              queryParams.created_before = params.created_before;
            }

            const res: any = await getOrders(queryParams);
            
            // 处理分页响应
            if (res.results) {
              return {
                data: res.results,
                total: res.pagination?.total || res.total || res.count || 0,
                success: true,
              };
            }
            
            // 处理数组响应
            const data = Array.isArray(res) ? res : [];
            return {
              data: data,
              total: data.length,
              success: true,
            };
          } catch (error) {
            message.error('加载订单列表失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        rowKey="id"
        scroll={{ x: 1800 }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total: number) => `共 ${total} 条`,
        }}
        options={{
          reload: true,
          density: true,
          setting: true,
        }}
      />

      <Drawer
        title="订单详情"
        width={720}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {currentOrder && (
          <ProDescriptions
            column={2}
            dataSource={currentOrder}
          >
            <ProDescriptions.Item label="订单号" span={2} copyable>
              {currentOrder.order_number}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="用户名" span={2}>
              {currentOrder.user_username}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="商品名称" span={2}>
              {currentOrder.product?.name}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="数量">
              {currentOrder.quantity}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="单价">
              ¥{currentOrder.product?.price}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="总金额" span={2}>
              <span style={{ fontSize: 18, fontWeight: 'bold', color: '#ff4d4f' }}>
                ¥{currentOrder.total_amount}
              </span>
            </ProDescriptions.Item>
            <ProDescriptions.Item label="订单状态" span={2}>
              <Tag color={statusMap[currentOrder.status]?.color}>
                {statusMap[currentOrder.status]?.text}
              </Tag>
            </ProDescriptions.Item>
            {currentOrder.is_haier_order && (
              <>
                <ProDescriptions.Item label="海尔订单" span={2}>
                  <Tag color="blue">是</Tag>
                </ProDescriptions.Item>
                {currentOrder.haier_order_info?.haier_order_no && (
                  <ProDescriptions.Item label="海尔订单号" span={2} copyable>
                    {currentOrder.haier_order_info.haier_order_no}
                  </ProDescriptions.Item>
                )}
                {currentOrder.haier_order_info?.haier_so_id && (
                  <ProDescriptions.Item label="海尔子订单号" span={2} copyable>
                    {currentOrder.haier_order_info.haier_so_id}
                  </ProDescriptions.Item>
                )}
              </>
            )}
            <ProDescriptions.Item label="收货人">
              {currentOrder.snapshot_contact_name}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="联系电话">
              {currentOrder.snapshot_phone}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="收货地址" span={2}>
              {currentOrder.snapshot_address}
            </ProDescriptions.Item>
            {currentOrder.logistics_info && (
              <>
                <ProDescriptions.Item label="物流公司">
                  {currentOrder.logistics_info.logistics_company}
                </ProDescriptions.Item>
                <ProDescriptions.Item label="物流单号" copyable>
                  {currentOrder.logistics_info.logistics_no}
                </ProDescriptions.Item>
              </>
            )}
            <ProDescriptions.Item label="创建时间" span={2} valueType="dateTime">
              {currentOrder.created_at}
            </ProDescriptions.Item>
          </ProDescriptions>
        )}
      </Drawer>

      <Modal
        title="推送订单到海尔"
        open={pushModalVisible}
        onOk={handlePushSubmit}
        onCancel={() => setPushModalVisible(false)}
        confirmLoading={pushing}
        width={500}
      >
        <Form
          form={pushForm}
          layout="vertical"
          style={{ marginTop: 20 }}
        >
          <Form.Item
            label="订单来源系统"
            name="source_system"
            rules={[{ required: true, message: '请输入订单来源系统' }]}
          >
            <Input placeholder="例如: MERCHANT_ADMIN" />
          </Form.Item>
          <Form.Item
            label="店铺名称"
            name="shop_name"
            rules={[{ required: true, message: '请输入店铺名称' }]}
          >
            <Input placeholder="例如: XX旗舰店" />
          </Form.Item>
        </Form>
        <div style={{ marginTop: 16, padding: 12, background: '#f0f2f5', borderRadius: 4 }}>
          <div style={{ marginBottom: 8, fontWeight: 'bold' }}>订单信息：</div>
          <div>订单号: {currentOrder?.order_number}</div>
          <div>商品: {currentOrder?.product?.name}</div>
          <div>数量: {currentOrder?.quantity}</div>
          <div>金额: ¥{currentOrder?.total_amount}</div>
        </div>
      </Modal>

      <Modal
        title="海尔物流信息"
        open={logisticsModalVisible}
        onCancel={() => setLogisticsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setLogisticsModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {loadingLogistics ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : logisticsData ? (
          <div>
            {logisticsData.getAllLogisticsInfoByOrderCode && logisticsData.getAllLogisticsInfoByOrderCode.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <h4>统仓云仓物流</h4>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
                  {JSON.stringify(logisticsData.getAllLogisticsInfoByOrderCode, null, 2)}
                </pre>
              </div>
            )}
            {logisticsData.getStockDeliveryLogisticsRecord && logisticsData.getStockDeliveryLogisticsRecord.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <h4>智汇宝物流</h4>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
                  {JSON.stringify(logisticsData.getStockDeliveryLogisticsRecord, null, 2)}
                </pre>
              </div>
            )}
            {logisticsData.getStockDeliveryLogisticsRecordThirdparty && logisticsData.getStockDeliveryLogisticsRecordThirdparty.length > 0 && (
              <div>
                <h4>第三方快递</h4>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
                  {JSON.stringify(logisticsData.getStockDeliveryLogisticsRecordThirdparty, null, 2)}
                </pre>
              </div>
            )}
            {!logisticsData.getAllLogisticsInfoByOrderCode && 
             !logisticsData.getStockDeliveryLogisticsRecord && 
             !logisticsData.getStockDeliveryLogisticsRecordThirdparty && (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                暂无物流信息
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            暂无物流信息
          </div>
        )}
      </Modal>

      <ModalForm
        title="发货"
        open={shipModalVisible}
        onOpenChange={setShipModalVisible}
        onFinish={handleShipSubmit}
        modalProps={{
          destroyOnClose: true,
        }}
      >
        <ProFormText
          name="logistics_company"
          label="物流公司"
          placeholder="请输入物流公司"
        />
        <ProFormText
          name="tracking_number"
          label="快递单号"
          placeholder="请输入快递单号"
          rules={[{ required: true, message: '请输入快递单号' }]}
        />
        <ProFormText
          name="note"
          label="备注"
          placeholder="选填"
        />
      </ModalForm>
    </>
  );
}
