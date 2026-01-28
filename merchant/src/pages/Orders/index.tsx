import { useRef } from 'react';
import { ProTable, ProDescriptions, ModalForm, ProFormText, ProFormRadio, ProFormTextArea, ProFormDependency, ProFormDigit } from '@ant-design/pro-components';
import { Tag, Button, message, Space, Popconfirm, Drawer, Modal, Form, Input, List, Image, Tooltip } from 'antd';
import { EyeOutlined, SendOutlined, CheckOutlined, CloseOutlined, CloudUploadOutlined, CarOutlined, RollbackOutlined, PayCircleOutlined, UploadOutlined, DownloadOutlined, EditOutlined } from '@ant-design/icons';
import { getOrders, getOrder, shipOrder, completeOrder, cancelOrder, pushToHaier, getHaierLogistics, receiveReturn, completeRefund, uploadInvoice, downloadInvoice, approveReturn, rejectReturn, getRefunds, startRefund, failRefund, exportOrders, adjustOrderAmount } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { useState } from 'react';
import type { Order } from '@/services/types';
import { Upload } from 'antd';
import { downloadBlob } from '@/utils/download';
import ExportLoadingModal from '@/components/ExportLoadingModal';

const statusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '待支付', color: 'orange' },
  paid: { text: '已支付', color: 'blue' },
  shipped: { text: '已发货', color: 'cyan' },
  completed: { text: '已完成', color: 'green' },
  cancelled: { text: '已取消', color: 'red' },
  returning: { text: '退货中', color: 'purple' },
  refunding: { text: '退款中', color: 'purple' },
  refunded: { text: '已退款', color: 'magenta' },
};

const haierStatusMap: Record<string, { text: string; color: string }> = {
  push_pending: { text: '推送中', color: 'processing' },
  confirmed: { text: '已推送', color: 'green' },
  failed: { text: '推送失败', color: 'red' },
  cancel_pending: { text: '取消中', color: 'orange' },
  cancelled: { text: '已取消', color: 'red' },
  cancel_failed: { text: '取消失败', color: 'red' },
  out_of_stock: { text: '缺货', color: 'orange' },
  out_of_stock_failed: { text: '缺货回调失败', color: 'red' },
};

const returnStatusMap: Record<string, { text: string; color: string }> = {
  requested: { text: '等待商家处理', color: 'orange' },
  approved: { text: '已同意退货', color: 'green' },
  in_transit: { text: '退货中', color: 'blue' },
  received: { text: '已收到退货', color: 'purple' },
  rejected: { text: '已拒绝退货', color: 'red' },
};

const refundStatusMap: Record<string, { text: string; color: string }> = {
  pending: { text: '待审核', color: 'orange' },
  processing: { text: '处理中', color: 'purple' },
  succeeded: { text: '已退款', color: 'green' },
  failed: { text: '已拒绝', color: 'red' },
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
  const [refundModalVisible, setRefundModalVisible] = useState(false);
  const [refundDetail, setRefundDetail] = useState<any>(null);
  const [refundReviewVisible, setRefundReviewVisible] = useState(false);
  const [refundReviewList, setRefundReviewList] = useState<any[]>([]);
  const [refundReviewOrder, setRefundReviewOrder] = useState<Order | null>(null);
  const [refundProcessing, setRefundProcessing] = useState(false);
  const [shippingOrder, setShippingOrder] = useState<Order | null>(null);
  const [cancelModalVisible, setCancelModalVisible] = useState(false);
  const [cancellingOrder, setCancellingOrder] = useState<Order | null>(null);
  const [receiveReturnModalVisible, setReceiveReturnModalVisible] = useState(false);
  const [receivingOrder, setReceivingOrder] = useState<Order | null>(null);
  const [viewReturnModalVisible, setViewReturnModalVisible] = useState(false);
  const [viewingReturnOrder, setViewingReturnOrder] = useState<Order | null>(null);
  const [uploadInvoiceModalVisible, setUploadInvoiceModalVisible] = useState(false);
  const [uploadingOrder, setUploadingOrder] = useState<Order | null>(null);
  const [invoiceFileList, setInvoiceFileList] = useState<any[]>([]);
  const [adjustModalVisible, setAdjustModalVisible] = useState(false);
  const [adjustingOrder, setAdjustingOrder] = useState<Order | null>(null);
  const [adjustForm] = Form.useForm();
  const [exportParams, setExportParams] = useState<Record<string, any>>({});
  const [exporting, setExporting] = useState(false);
  const exportLockRef = useRef(false);

  const handleExport = async () => {
    if (exportLockRef.current) return;
    exportLockRef.current = true;
    setExporting(true);
    try {
      const res: any = await exportOrders(exportParams);
      const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
      downloadBlob(res, `orders_${timestamp}.xlsx`);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    } finally {
      exportLockRef.current = false;
      setExporting(false);
    }
  };

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
      const res: any = await cancelOrder(cancellingOrder.id, values);
      const haierStatus = res?.haier_order_info?.haier_status;
      if (haierStatus === 'cancel_pending') {
        message.success(res?.detail || '取消已提交，等待回调');
      } else {
        message.success('取消成功');
      }
      setCancelModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
      return false;
    }
  };

  const handleAdjustAmount = (record: Order) => {
    setAdjustingOrder(record);
    setAdjustModalVisible(true);
    const currentActual = Number(record.actual_amount ?? record.total_amount);
    const totalAmount = Number(record.total_amount);
    adjustForm.setFieldsValue({
      total_amount: totalAmount,
      current_actual_amount: currentActual,
      actual_amount: currentActual,
    });
  };

  const handleAdjustAmountSubmit = async (values: any) => {
    try {
      if (!adjustingOrder) return false;
      await adjustOrderAmount(adjustingOrder.id, { actual_amount: values.actual_amount });
      message.success('改价成功');
      setAdjustModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '改价失败');
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

  const handleUploadInvoiceClick = (record: Order) => {
    setUploadingOrder(record);
    setInvoiceFileList([]);
    setUploadInvoiceModalVisible(true);
  };

  const handleUploadInvoiceSubmit = async () => {
    try {
      if (!uploadingOrder?.invoice_info?.id) {
        message.error('未找到发票信息');
        return false;
      }
      if (invoiceFileList.length === 0) {
        message.error('请选择文件');
        return false;
      }
      const file = invoiceFileList[0].originFileObj;
      await uploadInvoice(uploadingOrder.invoice_info.id, file);
      message.success('上传成功');
      setUploadInvoiceModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '上传失败');
      return false;
    }
  };

  const handleDownloadInvoiceClick = async (record: Order) => {
    if (!record.invoice_info?.id) return;
    try {
      const res: any = await downloadInvoice(record.invoice_info.id);
      const url = window.URL.createObjectURL(new Blob([res]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `invoice_${record.order_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      message.error('下载失败');
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

  const handleRetryRefund = async (orderId: number, refundId?: number) => {
    try {
      let targetId = refundId;
      if (!targetId) {
        const list: any = await getRefunds({ order_id: orderId, page_size: 10 });
        const refund = list?.results?.find((r: any) => r.status === 'failed' || r.status === 'processing') || list?.results?.[0];
        targetId = refund?.id;
      }
      if (!targetId) {
        message.warning('未找到退款记录');
        return;
      }
      await startRefund(targetId, { provider: 'wechat' });
      message.success('已重新发起微信退款');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.message || '重试退款失败');
    }
  };

  const handleViewRefund = async (orderId: number) => {
    try {
      const list: any = await getRefunds({ order_id: orderId, page_size: 10 });
      if (!list?.results?.length) {
        message.warning('未找到退款记录');
        return;
      }
      setRefundDetail(list.results);
      setRefundModalVisible(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '获取退款信息失败');
    }
  };

  const handleReviewRefund = async (record: Order) => {
    try {
      const list: any = await getRefunds({ order_id: record.id, page_size: 20 });
      const pending = (list?.results || []).filter((item: any) => ['pending', 'failed'].includes(item.status));
      if (!pending.length) {
        message.warning('暂无待审核退款');
        return;
      }
      setRefundReviewOrder(record);
      setRefundReviewList(pending);
      setRefundReviewVisible(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '获取退款信息失败');
    }
  };

  const handleApproveRefund = async (refund: any) => {
    if (!refundReviewOrder || refundProcessing) return;
    setRefundProcessing(true);
    try {
      const provider = refundReviewOrder.payment_method === 'credit' ? 'credit' : 'wechat';
      await startRefund(refund.id, { provider });
      message.success('已发起退款');
      setRefundReviewVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '发起退款失败');
    } finally {
      setRefundProcessing(false);
    }
  };

  const handleRejectRefund = (refund: any) => {
    if (refundProcessing) return;
    let reason = '';
    Modal.confirm({
      title: '拒绝退款',
      content: (
        <Input.TextArea
          placeholder="请输入拒绝原因"
          rows={3}
          onChange={(e) => {
            reason = e.target.value;
          }}
        />
      ),
      okText: '确认拒绝',
      okButtonProps: { danger: true },
      onOk: async () => {
        if (!reason) {
          message.warning('请输入拒绝原因');
          return Promise.reject();
        }
        setRefundProcessing(true);
        try {
          await failRefund(refund.id, { reason });
          message.success('已拒绝退款');
          setRefundReviewVisible(false);
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || '拒绝退款失败');
        } finally {
          setRefundProcessing(false);
        }
        return undefined;
      }
    });
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
    pushForm.resetFields();
    setPushModalVisible(true);
  };

  const handlePushSubmit = async () => {
    try {
      const values = await pushForm.validateFields();
      setPushing(true);
      if (currentOrder) {
        const res: any = await pushToHaier(currentOrder.id, values);
        message.success(res?.detail || '推送已提交，等待回调');
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

  const handleViewReturnDetail = (record: Order) => {
    setViewingReturnOrder(record);
    setViewReturnModalVisible(true);
  };

  const handleProcessReturnSubmit = async (values: any) => {
    try {
      if (!viewingReturnOrder) return false;
      
      if (values.action === 'approve') {
        await approveReturn(viewingReturnOrder.id, { note: values.note });
        message.success('已同意退货');
      } else if (values.action === 'reject') {
        await rejectReturn(viewingReturnOrder.id, { note: values.note }); // backend expects 'note' for rejection reason based on previous code context? Wait, let's check previous code.
        // Previous code: handleRejectReturnSubmit called rejectReturn(id, values). values had 'note' (label="拒绝原因", name="note").
        // So yes, 'note' is correct.
        message.success('已拒绝退货');
      }
      
      setViewReturnModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
      return false;
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
      width: 200,
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
      title: '实付款', 
      dataIndex: 'actual_amount', 
      hideInSearch: true, 
      width: 120,
      render: (_, record) => `¥${record.actual_amount ?? record.total_amount}`,
    },
    { 
      title: '已退款', 
      dataIndex: 'refunded_amount', 
      hideInSearch: true, 
      width: 120,
      render: (_, record) => {
        if (!record.refunded_amount) return '-';
        return `¥${record.refunded_amount}`;
      },
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
        returning: { text: '退货中' },
        refunding: { text: '退款中' },
        refunded: { text: '已退款' },
      },
      render: (_, record) => {
        const status = statusMap[record.status];
        return <Tag color={status?.color}>{status?.text}</Tag>;
      },
    },
    {
      title: '物流单号',
      dataIndex: ['logistics_info', 'logistics_no'],
      width: 140,
      hideInSearch: true,
      render: (_, record) => record.logistics_info?.logistics_no || '-',
    },
    {
      title: '海尔订单',
      dataIndex: 'is_haier_order',
      width: 100,
      hideInSearch: true,
      render: (_, record) => {
        if (!record.is_haier_order) return <Tag>否</Tag>;
        const haierInfo = record.haier_order_info;
        const haierStatus = haierInfo?.haier_status || (haierInfo?.haier_so_id ? 'confirmed' : '');
        const failMsg = haierInfo?.haier_fail_msg;
        const statusMeta = haierStatus ? haierStatusMap[haierStatus] : { text: '未推送', color: 'orange' };
        const baseTag = (
          <Tag color={statusMeta?.color || 'default'} style={{ fontSize: 11 }}>
            {statusMeta?.text || haierStatus || '未推送'}
          </Tag>
        );
        const statusTag = failMsg && haierStatus?.includes('failed')
          ? <Tooltip title={failMsg}>{baseTag}</Tooltip>
          : baseTag;
        return (
          <Space direction="vertical" size={0}>
            <Tag color="blue">是</Tag>
            {statusTag}
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
      width: 200,
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

        if (record.status === 'pending') {
          actions.push(
            <Button
              key="adjust"
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleAdjustAmount(record)}
            >
              改价
            </Button>
          );
        }
        
        // 海尔订单相关操作
        const isHaierOrder = record.is_haier_order;
        const haierInfo = record.haier_order_info;
        const haierStatus = haierInfo?.haier_status || (haierInfo?.haier_so_id ? 'confirmed' : '');
        const canPushHaier = isHaierOrder && record.status === 'paid' && (!haierStatus || ['failed', 'cancel_failed', 'out_of_stock_failed'].includes(haierStatus));
        const canViewLogistics = isHaierOrder && haierStatus === 'confirmed';
        const isCancelPending = isHaierOrder && haierStatus === 'cancel_pending';
        
        if (canPushHaier) {
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
        
        if (canViewLogistics) {
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
        
        if (record.status === 'paid' && !isCancelPending) {
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
              disabled={isCancelPending}
            >
              取消
            </Button>
          );
        }
        
        // 退货相关操作
        if (record.return_info) {
          if (record.return_info.status === 'requested') {
            actions.push(
              <Button
                key="process_return"
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleViewReturnDetail(record)}
              >
                处理退货
              </Button>
            );
          } else {
            actions.push(
              <Button
                key="view_return"
                type="link"
                size="small"
                onClick={() => handleViewReturnDetail(record)}
              >
                退货详情
              </Button>
            );
          }

          if (record.return_info.status === 'in_transit') {
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

        if (record.refund_action_required && record.status !== 'refunding') {
          actions.push(
            <Button
              key="review_refund"
              type="link"
              size="small"
              icon={<PayCircleOutlined />}
              onClick={() => handleReviewRefund(record)}
            >
              审核退款
            </Button>
          );
        }

        // 退款中：提供重新发起退款
        if (record.status === 'refunding') {
          actions.push(
            <Popconfirm
              key="retry_refund"
              title="重新发起微信退款？"
              onConfirm={() => handleRetryRefund(record.id)}
            >
              <Button type="link" size="small" icon={<PayCircleOutlined />}>
                重试退款
              </Button>
            </Popconfirm>
          );
          actions.push(
            <Button
              key="view_refund"
              type="link"
              size="small"
              onClick={() => handleViewRefund(record.id)}
            >
              退款详情
            </Button>
          );
        } else if (record.payment_method === 'credit' && ['paid', 'shipped'].includes(record.status)) {
          // 信用支付退款入口：未发货可直接完成，已发货提示人工处理
          actions.push(
            <Popconfirm
              key="credit_refund"
              title={record.status === 'paid' ? '确认对信用账户执行退款？' : '已发货信用订单，需人工线下退款，确认标记退款完成？'}
              onConfirm={() => handleCompleteRefund(record.id)}
            >
              <Button type="link" size="small" icon={<PayCircleOutlined />}>
                {record.status === 'paid' ? '信用退款' : '标记信用退款'}
              </Button>
            </Popconfirm>
          );
        }

        // 发票相关操作
        if (record.invoice_info) {
          actions.push(
            <Button
              key="upload_invoice"
              type="link"
              size="small"
              icon={<UploadOutlined />}
              onClick={() => handleUploadInvoiceClick(record)}
            >
              上传发票
            </Button>
          );
          if (record.invoice_info.file_url) {
            actions.push(
              <Button
                key="download_invoice"
                type="link"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleDownloadInvoiceClick(record)}
              >
                下载发票
              </Button>
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
        scroll={{ x: 1800 }}
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

            const exportQuery = { ...queryParams };
            delete exportQuery.page;
            delete exportQuery.page_size;
            setExportParams(exportQuery);

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
          defaultCollapsed: false,
          collapseRender: false,
        }}
        toolBarRender={() => [
          <Button key="export" icon={<DownloadOutlined />} onClick={handleExport} loading={exporting} disabled={exporting}>
            导出
          </Button>,
        ]}
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

      {/* 改价弹窗 */}
      <ModalForm
        form={adjustForm}
        title="修改订单金额"
        visible={adjustModalVisible}
        onVisibleChange={(visible) => {
          setAdjustModalVisible(visible);
          if (!visible) {
            setAdjustingOrder(null);
            adjustForm.resetFields();
          }
        }}
        onFinish={handleAdjustAmountSubmit}
      >
        <ProFormText name="total_amount" label="原订单金额" disabled />
        <ProFormText name="current_actual_amount" label="当前实付金额" disabled />
        <ProFormDigit
          name="actual_amount"
          label="调整后实付金额"
          rules={[{ required: true, message: '请输入调整后的实付金额' }]}
          fieldProps={{
            precision: 2,
            min: 0.01,
            max: adjustingOrder ? Number(adjustingOrder.actual_amount ?? adjustingOrder.total_amount) : undefined,
            addonBefore: '¥',
          }}
          extra="仅待支付订单可修改，修改后需重新发起支付"
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

      {/* 退货详情/处理弹窗 */}
      <ModalForm
        title={viewingReturnOrder?.return_info?.status === 'requested' ? "处理退货申请" : "退货详情"}
        visible={viewReturnModalVisible}
        onVisibleChange={setViewReturnModalVisible}
        onFinish={handleProcessReturnSubmit}
        modalProps={{
          destroyOnClose: true,
        }}
        submitter={
          viewingReturnOrder?.return_info?.status === 'requested'
            ? {
                searchConfig: {
                  submitText: '确认提交',
                  resetText: '取消',
                },
              }
            : false
        }
      >
        {viewingReturnOrder?.return_info && (
          <>
            <ProDescriptions column={1} title="退货申请详情" dataSource={viewingReturnOrder.return_info}>
               <ProDescriptions.Item 
               label="退货状态" 
               dataIndex="status"
               render={(_, record) => {
                 const status = returnStatusMap[record.status];
                 return <Tag color={status?.color}>{status?.text || record.status_display}</Tag>;
               }}
             />
               <ProDescriptions.Item label="退货原因" dataIndex="reason" />
               <ProDescriptions.Item label="申请时间" dataIndex="created_at" valueType="dateTime" />
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
               <ProDescriptions.Item label="物流单号" dataIndex="tracking_number" />
               <ProDescriptions.Item label="处理备注" dataIndex="processed_note" />
               <ProDescriptions.Item label="处理时间" dataIndex="processed_at" valueType="dateTime" />
            </ProDescriptions>

            {viewingReturnOrder.return_info.status === 'requested' && (
              <>
                <div style={{ margin: '24px 0', borderTop: '1px solid #f0f0f0' }} />
                <ProFormRadio.Group
                  name="action"
                  label="处理结果"
                  rules={[{ required: true, message: '请选择处理结果' }]}
                  options={[
                    { label: '同意退货', value: 'approve' },
                    { label: '拒绝退货', value: 'reject' },
                  ]}
                />
                
                <ProFormDependency name={['action']}>
                  {({ action }) => {
                    if (action === 'approve') {
                      return (
                        <ProFormTextArea
                          name="note"
                          label="处理备注"
                          placeholder="请输入处理备注（可选）"
                        />
                      );
                    }
                    if (action === 'reject') {
                      return (
                        <ProFormTextArea
                          name="note" // Reusing 'note' as per API check earlier
                          label="拒绝原因"
                          placeholder="请输入拒绝原因"
                          rules={[{ required: true, message: '请输入拒绝原因' }]}
                        />
                      );
                    }
                    return null;
                  }}
                </ProFormDependency>
              </>
            )}
          </>
        )}
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
            <ProDescriptions.Item label="总金额" render={(_, record) => `¥${record.total_amount}`} />
            <ProDescriptions.Item label="实付款" render={(_, record) => `¥${record.actual_amount ?? record.total_amount}`} />
            <ProDescriptions.Item label="已退款" render={(_, record) => `¥${record.refunded_amount ?? 0}`} />
            <ProDescriptions.Item label="可退金额" render={(_, record) => `¥${record.refundable_amount ?? 0}`} />
            {currentOrder.logistics_info?.logistics_no && (
              <ProDescriptions.Item label="物流单号" render={() => currentOrder.logistics_info?.logistics_no} />
            )}
            <ProDescriptions.Item label="取消原因" dataIndex="cancel_reason" />
            <ProDescriptions.Item label="备注" dataIndex="note" />
          </ProDescriptions>
        )}

        {currentOrder?.is_haier_order && currentOrder.haier_order_info && (
          <ProDescriptions
            column={1}
            title="海尔信息"
            style={{ marginTop: 24 }}
            dataSource={currentOrder.haier_order_info}
          >
            <ProDescriptions.Item
              label="推送状态"
              dataIndex="haier_status"
              render={(_, record) => {
                const rawStatus = record.haier_status || (record.haier_so_id ? 'confirmed' : '');
                const statusMeta = rawStatus ? haierStatusMap[rawStatus] : undefined;
                const text = statusMeta?.text || rawStatus || '未推送';
                const color = statusMeta?.color || 'default';
                return <Tag color={color}>{text}</Tag>;
              }}
            />
            <ProDescriptions.Item label="海尔订单号" dataIndex="haier_order_no" />
            <ProDescriptions.Item
              label="失败原因"
              dataIndex="haier_fail_msg"
              render={(_, record) => record.haier_fail_msg || '-'}
            />
          </ProDescriptions>
        )}

        {currentOrder && currentOrder.return_info && (
          <ProDescriptions
            column={1}
            title="退货信息"
            style={{ marginTop: 24 }}
            dataSource={currentOrder.return_info}
          >
            <ProDescriptions.Item 
              label="退货状态" 
              dataIndex="status"
              render={(_, record) => {
                const status = returnStatusMap[record.status];
                return <Tag color={status?.color}>{status?.text || record.status_display}</Tag>;
              }}
            />
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
          <div style={{ color: '#999' }}>店铺名称由后台配置</div>
        </Form>
      </Modal>

      {/* 退款审核 */}
      <Modal
        title={<div style={{ textAlign: 'center', fontWeight: 600 }}>退款审核</div>}
        open={refundReviewVisible}
        onCancel={() => {
          setRefundReviewVisible(false);
          setRefundReviewList([]);
          setRefundReviewOrder(null);
        }}
        footer={null}
        width={560}
      >
        <List
          dataSource={refundReviewList}
          renderItem={(item) => (
            <List.Item
            >
              {(() => {
                const statusInfo = refundStatusMap[item.status] || { text: item.status, color: 'default' };
                const createdAt = item.created_at ? new Date(item.created_at).toLocaleString() : '-';
                const images = Array.isArray(item.evidence_images) ? item.evidence_images : [];
                const evidence = images.length ? (
                  <Image.PreviewGroup>
                    <Space size={8} wrap>
                      {images.map((url: string, index: number) => (
                        <Image
                          key={`${url}-${index}`}
                          src={url}
                          width={56}
                          height={56}
                          style={{ borderRadius: 6, objectFit: 'cover' }}
                        />
                      ))}
                    </Space>
                  </Image.PreviewGroup>
                ) : null;
                return (
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 16, fontWeight: 600 }}>退款金额 ¥{item.amount}</span>
                      <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
                    </div>
                    <div style={{ marginTop: 8, color: '#666' }}>订单号：{item.order_number || '-'}</div>
                    <div style={{ marginTop: 4, color: '#666' }}>原因：{item.reason || '无'}</div>
                    <div style={{ marginTop: 4, color: '#666' }}>申请时间：{createdAt}</div>
                    {evidence && (
                      <div style={{ marginTop: 10, color: '#666' }}>凭证图片：{evidence}</div>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 16 }}>
                      <Button
                        type="primary"
                        loading={refundProcessing}
                        disabled={refundProcessing}
                        onClick={() => handleApproveRefund(item)}
                      >
                        同意退款
                      </Button>
                      <Button
                        danger
                        loading={refundProcessing}
                        disabled={refundProcessing}
                        onClick={() => handleRejectRefund(item)}
                      >
                        拒绝
                      </Button>
                    </div>
                  </div>
                );
              })()}
            </List.Item>
          )}
        />
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

      {/* 上传发票弹窗 */}
      <ModalForm
        title="上传发票"
        visible={uploadInvoiceModalVisible}
        onVisibleChange={setUploadInvoiceModalVisible}
        onFinish={handleUploadInvoiceSubmit}
      >
        <Form.Item
          label="发票文件"
          required
          tooltip="支持PDF、图片格式"
        >
          <Upload
            fileList={invoiceFileList}
            onChange={({ fileList }) => setInvoiceFileList(fileList)}
            beforeUpload={() => false}
            maxCount={1}
          >
            <Button icon={<UploadOutlined />}>选择文件</Button>
          </Upload>
        </Form.Item>
      </ModalForm>

      {/* 退款详情 */}
      <Modal
        title="退款详情"
        open={refundModalVisible}
        onCancel={() => setRefundModalVisible(false)}
        footer={null}
        width={520}
      >
        {refundDetail ? (
          Array.isArray(refundDetail) ? (
            <ProDescriptions
              column={1}
              dataSource={refundDetail}
              columns={[
                { title: '退款ID', dataIndex: 'id' },
                { title: '状态', dataIndex: 'status' },
                { title: '金额', dataIndex: 'amount' },
                { title: '原因', dataIndex: 'reason' },
                { title: '交易号', dataIndex: 'transaction_id' },
                { title: '创建时间', dataIndex: 'created_at' },
                { title: '更新时间', dataIndex: 'updated_at' },
              ]}
            />
          ) : (
          <ProDescriptions
            column={1}
            dataSource={refundDetail}
            columns={[
              { title: '退款ID', dataIndex: 'id' },
              { title: '订单', dataIndex: 'order_number' },
              { title: '状态', dataIndex: 'status' },
              { title: '金额', dataIndex: 'amount' },
              { title: '原因', dataIndex: 'reason' },
              { title: '交易号', dataIndex: 'transaction_id' },
              { title: '创建时间', dataIndex: 'created_at' },
              { title: '更新时间', dataIndex: 'updated_at' },
              { title: '日志', render: () => <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(refundDetail.logs || [], null, 2)}</pre> },
            ]}
          />)
        ) : (
          <div>暂无数据</div>
        )}
      </Modal>
      <ExportLoadingModal open={exporting} />
    </>
  );
}
