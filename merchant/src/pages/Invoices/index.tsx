import { useRef, useState } from 'react';
import { ProTable, ProDescriptions } from '@ant-design/pro-components';
import { Tag, Button, message, Space, Popconfirm, Drawer, Modal, Form, Input } from 'antd';
import { EyeOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { getInvoices, getInvoice, issueInvoice, cancelInvoice, getOrder } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';

const statusMap: any = {
  requested: { text: '已申请', color: 'orange' },
  issued: { text: '已开具', color: 'green' },
  cancelled: { text: '已取消', color: 'red' },
};

const typeMap: any = {
  normal: '普通发票',
  special: '专用发票',
};

export default function Invoices() {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentInvoice, setCurrentInvoice] = useState<any>(null);
  const [issueModalVisible, setIssueModalVisible] = useState(false);
  const [issueForm] = Form.useForm();
  const [issuing, setIssuing] = useState(false);
  const [orderDetailVisible, setOrderDetailVisible] = useState(false);
  const [currentOrder, setCurrentOrder] = useState<any>(null);

  const handleViewDetail = async (record: any) => {
    try {
      const res = await getInvoice(record.id);
      setCurrentInvoice(res);
      setDetailVisible(true);
    } catch (error) {
      message.error('获取发票详情失败');
    }
  };

  const handleViewOrder = async (orderId: number) => {
    try {
      const res = await getOrder(orderId);
      setCurrentOrder(res);
      setOrderDetailVisible(true);
    } catch (error) {
      message.error('获取订单详情失败');
    }
  };

  const handleIssue = (record: any) => {
    setCurrentInvoice(record);
    issueForm.resetFields();
    setIssueModalVisible(true);
  };

  const handleIssueSubmit = async () => {
    try {
      const values = await issueForm.validateFields();
      setIssuing(true);
      await issueInvoice(currentInvoice.id, values);
      message.success('发票开具成功');
      setIssueModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
    } finally {
      setIssuing(false);
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await cancelInvoice(id);
      message.success('取消成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns: any = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      hideInSearch: true,
    },
    {
      title: '订单号',
      dataIndex: 'order_number',
      copyable: true,
      render: (text: string, record: any) => (
        <a onClick={() => handleViewOrder(record.order)}>{text}</a>
      ),
    },
    {
      title: '用户名',
      dataIndex: 'username',
      copyable: true,
    },
    {
      title: '发票抬头',
      dataIndex: 'title',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'invoice_type',
      valueEnum: {
        normal: { text: '普通发票' },
        special: { text: '专用发票' },
      },
    },
    {
      title: '金额',
      dataIndex: 'amount',
      hideInSearch: true,
      render: (amount: number) => `¥${amount}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      valueEnum: {
        requested: { text: '已申请', status: 'Processing' },
        issued: { text: '已开具', status: 'Success' },
        cancelled: { text: '已取消', status: 'Error' },
      },
      render: (_: any, record: any) => {
        const status = statusMap[record.status];
        return <Tag color={status?.color}>{status?.text}</Tag>;
      },
    },
    {
      title: '申请时间',
      dataIndex: 'requested_at',
      valueType: 'dateTime',
      hideInSearch: true,
    },
    {
      title: '操作',
      valueType: 'option',
      fixed: 'right',
      render: (_: any, record: any) => {
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

        if (record.status === 'requested') {
          actions.push(
            <Button
              key="issue"
              type="link"
              size="small"
              icon={<CheckOutlined />}
              onClick={() => handleIssue(record)}
            >
              开具
            </Button>
          );
          actions.push(
            <Popconfirm
              key="cancel"
              title="确认取消申请?"
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
        headerTitle="发票列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params: any) => {
          const res: any = await getInvoices({
            page: params.current,
            page_size: params.pageSize,
            ...params,
          });
          return {
            data: res.results,
            total: res.count,
            success: true,
          };
        }}
        rowKey="id"
        scroll={{ x: 1200 }}
      />

      <Drawer
        title="发票详情"
        width={600}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {currentInvoice && (
          <ProDescriptions column={1} dataSource={currentInvoice} bordered>
            <ProDescriptions.Item label="ID">{currentInvoice.id}</ProDescriptions.Item>
            <ProDescriptions.Item label="订单ID">{currentInvoice.order}</ProDescriptions.Item>
            <ProDescriptions.Item label="用户ID">{currentInvoice.user}</ProDescriptions.Item>
            <ProDescriptions.Item label="发票类型">{typeMap[currentInvoice.invoice_type]}</ProDescriptions.Item>
            <ProDescriptions.Item label="发票抬头">{currentInvoice.title}</ProDescriptions.Item>
            <ProDescriptions.Item label="纳税人识别号">{currentInvoice.taxpayer_id}</ProDescriptions.Item>
            <ProDescriptions.Item label="金额">¥{currentInvoice.amount}</ProDescriptions.Item>
            <ProDescriptions.Item label="税率">{currentInvoice.tax_rate}%</ProDescriptions.Item>
            <ProDescriptions.Item label="税额">¥{currentInvoice.tax_amount}</ProDescriptions.Item>
            <ProDescriptions.Item label="接收邮箱">{currentInvoice.email}</ProDescriptions.Item>
            <ProDescriptions.Item label="联系电话">{currentInvoice.phone}</ProDescriptions.Item>
            <ProDescriptions.Item label="地址">{currentInvoice.address}</ProDescriptions.Item>
            <ProDescriptions.Item label="开户行及账号">{currentInvoice.bank_account}</ProDescriptions.Item>
            <ProDescriptions.Item label="状态">
               <Tag color={statusMap[currentInvoice.status]?.color}>
                {statusMap[currentInvoice.status]?.text}
              </Tag>
            </ProDescriptions.Item>
            <ProDescriptions.Item label="发票号码">{currentInvoice.invoice_number}</ProDescriptions.Item>
            <ProDescriptions.Item label="文件URL">
              {currentInvoice.file_url && <a href={currentInvoice.file_url} target="_blank" rel="noreferrer">下载/查看</a>}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="申请时间" valueType="dateTime">{currentInvoice.requested_at}</ProDescriptions.Item>
            <ProDescriptions.Item label="开具时间" valueType="dateTime">{currentInvoice.issued_at}</ProDescriptions.Item>
          </ProDescriptions>
        )}
      </Drawer>

      <Drawer
        title="订单详情"
        width={600}
        open={orderDetailVisible}
        onClose={() => setOrderDetailVisible(false)}
      >
        {currentOrder && (
          <ProDescriptions column={1} dataSource={currentOrder} bordered>
            <ProDescriptions.Item label="订单号">{currentOrder.order_number}</ProDescriptions.Item>
            <ProDescriptions.Item label="商品名称">{currentOrder.product?.name}</ProDescriptions.Item>
            <ProDescriptions.Item label="商品型号">{currentOrder.product?.product_model}</ProDescriptions.Item>
            <ProDescriptions.Item label="数量">{currentOrder.quantity}</ProDescriptions.Item>
            <ProDescriptions.Item label="总金额">¥{currentOrder.total_amount}</ProDescriptions.Item>
            <ProDescriptions.Item label="实付金额">¥{currentOrder.actual_amount}</ProDescriptions.Item>
            <ProDescriptions.Item label="状态">{currentOrder.status_label}</ProDescriptions.Item>
            <ProDescriptions.Item label="下单时间" valueType="dateTime">{currentOrder.created_at}</ProDescriptions.Item>
            <ProDescriptions.Item label="收货人">{currentOrder.snapshot_contact_name}</ProDescriptions.Item>
            <ProDescriptions.Item label="联系电话">{currentOrder.snapshot_phone}</ProDescriptions.Item>
            <ProDescriptions.Item label="收货地址">
              {currentOrder.snapshot_province}{currentOrder.snapshot_city}{currentOrder.snapshot_district}{currentOrder.snapshot_town}
              {currentOrder.snapshot_address}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="备注">{currentOrder.note || '-'}</ProDescriptions.Item>
          </ProDescriptions>
        )}
      </Drawer>

      <Modal
        title="开具发票"
        open={issueModalVisible}
        onOk={handleIssueSubmit}
        onCancel={() => setIssueModalVisible(false)}
        confirmLoading={issuing}
      >
        <Form form={issueForm} layout="vertical">
          <Form.Item
            label="发票号码"
            name="invoice_number"
            rules={[{ required: true, message: '请输入发票号码' }]}
          >
            <Input placeholder="请输入发票号码" />
          </Form.Item>
          <Form.Item
            label="发票文件URL"
            name="file_url"
            rules={[{ type: 'url', message: '请输入有效的URL' }]}
          >
            <Input placeholder="请输入发票PDF下载链接" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
