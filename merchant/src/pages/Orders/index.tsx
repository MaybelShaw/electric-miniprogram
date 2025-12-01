import { useRef } from 'react';
import { ProTable, ProDescriptions, ModalForm, ProFormText } from '@ant-design/pro-components';
import { Tag, Button, message, Space, Popconfirm, Drawer, Modal, Form, Input } from 'antd';
import { EyeOutlined, SendOutlined, CheckOutlined, CloseOutlined, CloudUploadOutlined, CarOutlined, RollbackOutlined, PayCircleOutlined } from '@ant-design/icons';
import { getOrders, getOrder, shipOrder, completeOrder, cancelOrder, pushToHaier, getHaierLogistics, receiveReturn, completeRefund } from '@/services/api';
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
  const [cancelModalVisible, setCancelModalVisible] = useState(false);
  const [cancellingOrder, setCancellingOrder] = useState<Order | null>(null);
  const [receiveReturnModalVisible, setReceiveReturnModalVisible] = useState(false);
  const [receivingOrder, setReceivingOrder] = useState<Order | null>(null);

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

  const handleCancelClick = (record: Order) => {
    setCancellingOrder(record);
    setCancelModalVisible(true);
  };

  const handleCancelSubmit = async (values: any) => {
    try {
      if (!cancellingOrder) return false;
      await cancelOrder(cancellingOrder.id, values);
      message.success('取消成功');
      setCancelModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
      return false;
    }
  };

  const handleReceiveReturn = (record: Order) => {
    setReceivingOrder(record);
    setReceiveReturnModalVisible(true);
  };

  const handleReceiveReturnSubmit = async (values: any) => {
    try {
      if (!receivingOrder) return false;
      await receiveReturn(receivingOrder.id, values);
      message.success('验收成功');
      setReceiveReturnModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
      return false;
    }
  };

  const handleCompleteRefund = async (id: number) => {
    try {
      await completeRefund(id);
      message.success('退款成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
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
            <Button
              key="cancel"
              type="link"
              size="small"
              danger
              icon={<CloseOutlined />}
              onClick={() => handleCancelClick(record)}
            >
              取消
            </Button>
          );
        }
        
        // 退货相关操作
        if (record.return_info) {
          if (['requested', 'in_transit'].includes(record.return_info.status)) {
            actions.push(
              <Button
                key="receive_return"
                type="link"
                size="small"
                icon={<RollbackOutlined />}
                onClick={() => handleReceiveReturn(record)}
              >
                验收退货
              </Button>
            );
          }
          
          if (record.return_info.status === 'received' && record.status !== 'refunded') {
             actions.push(
              <Popconfirm
                key="complete_refund"
                title="确认退款?"
                onConfirm={() => handleCompleteRefund(record.id)}
              >
                <Button
                  type="link"
                  size="small"
                  icon={<PayCircleOutlined />}
                >
                  完成退款
                </Button>
              </Popconfirm>
            );
          }
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
            return {
              data: [],
              success: false,
            };
          }
        }}
        rowKey="id"
        pagination={{
          pageSize: 20,
        }}
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => []}
      />
      
      {/* 发货弹窗 */}
      <ModalForm
        title="订单发货"
        visible={shipModalVisible}
        onVisibleChange={setShipModalVisible}
        onFinish={handleShipSubmit}
      >
        <ProFormText
          name="logistics_no"
          label="物流单号"
          placeholder="请输入物流单号"
          rules={[{ required: true, message: '请输入物流单号' }]}
        />
      </ModalForm>

      {/* 取消订单弹窗 */}
      <ModalForm
        title="取消订单"
        visible={cancelModalVisible}
        onVisibleChange={setCancelModalVisible}
        onFinish={handleCancelSubmit}
      >
        <ProFormText
          name="reason"
          label="取消原因"
          placeholder="请输入取消原因"
          rules={[{ required: true, message: '请输入取消原因' }]}
        />
        <ProFormText
          name="note"
          label="备注"
          placeholder="备注信息（可选）"
        />
      </ModalForm>

      {/* 验收退货弹窗 */}
      <ModalForm
        title="验收退货"
        visible={receiveReturnModalVisible}
        onVisibleChange={setReceiveReturnModalVisible}
        onFinish={handleReceiveReturnSubmit}
      >
        <ProFormText
          name="note"
          label="验收备注"
          placeholder="备注信息（如：商品完好，同意退款）"
          rules={[{ required: true, message: '请输入验收备注' }]}
        />
      </ModalForm>

      {/* 详情弹窗 */}
      <Drawer
        title="订单详情"
        width={600}
        visible={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {currentOrder && (
          <ProDescriptions
            column={1}
            title="基本信息"
            dataSource={currentOrder}
          >
            <ProDescriptions.Item label="订单号" dataIndex="order_number" />
            <ProDescriptions.Item label="创建时间" dataIndex="created_at" valueType="dateTime" />
            <ProDescriptions.Item 
              label="状态" 
              dataIndex="status"
              render={(_, record) => {
                 const status = statusMap[record.status];
                 return <Tag color={status?.color}>{status?.text}</Tag>;
              }}
            />
            <ProDescriptions.Item label="取消原因" dataIndex="cancel_reason" />
            <ProDescriptions.Item label="备注" dataIndex="note" />
          </ProDescriptions>
        )}

        {currentOrder && currentOrder.return_info && (
          <ProDescriptions
            column={1}
            title="退货信息"
            style={{ marginTop: 24 }}
            dataSource={currentOrder.return_info}
          >
            <ProDescriptions.Item label="退货状态" dataIndex="status_display" />
            <ProDescriptions.Item label="退货原因" dataIndex="reason" />
            <ProDescriptions.Item label="物流单号" dataIndex="tracking_number" />
            <ProDescriptions.Item 
              label="凭证图片" 
              dataIndex="evidence_images"
              render={(_, record) => {
                if (!record.evidence_images || record.evidence_images.length === 0) return '-';
                return (
                  <Space>
                    {record.evidence_images.map((url: string, index: number) => (
                      <a key={index} href={url} target="_blank" rel="noopener noreferrer">
                         <img src={url} style={{ width: 60, height: 60, objectFit: 'cover', border: '1px solid #f0f0f0' }} />
                      </a>
                    ))}
                  </Space>
                );
              }}
            />
            <ProDescriptions.Item label="处理备注" dataIndex="processed_note" />
            <ProDescriptions.Item label="处理时间" dataIndex="processed_at" valueType="dateTime" />
          </ProDescriptions>
        )}
      </Drawer>

      {/* 推送海尔弹窗 */}
      <Modal
        title="推送到海尔系统"
        visible={pushModalVisible}
        onOk={handlePushSubmit}
        onCancel={() => setPushModalVisible(false)}
        confirmLoading={pushing}
      >
        <Form form={pushForm} layout="vertical">
           <Form.Item name="source_system" label="源系统" rules={[{ required: true }]}>
             <Input />
           </Form.Item>
           <Form.Item name="shop_name" label="店铺名称" rules={[{ required: true }]}>
             <Input />
           </Form.Item>
        </Form>
      </Modal>

      {/* 物流查询弹窗 */}
      <Modal
        title="物流信息"
        visible={logisticsModalVisible}
        onCancel={() => setLogisticsModalVisible(false)}
        footer={null}
      >
        {loadingLogistics ? (
          <div>加载中...</div>
        ) : logisticsData ? (
          <div>
            <p>物流公司: {logisticsData.logistics_company}</p>
            <p>运单号: {logisticsData.logistics_no}</p>
            <p>发货单号: {logisticsData.delivery_record_code}</p>
            <p>SN码: {logisticsData.sn_code}</p>
          </div>
        ) : (
          <div>暂无物流信息</div>
        )}
      </Modal>
    </>
  );
}
