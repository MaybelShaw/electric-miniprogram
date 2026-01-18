import { useRef, useState } from 'react';
import { ProTable, ProDescriptions } from '@ant-design/pro-components';
import { Tag, Button, message, Space, Popconfirm, Drawer, Modal, Form, Input, Upload } from 'antd';
import { EyeOutlined, CheckOutlined, CloseOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { getInvoices, getInvoice, issueInvoice, cancelInvoice, getOrder, uploadInvoice, exportInvoices } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';
import { downloadBlob } from '@/utils/download';
import ExportLoadingModal from '@/components/ExportLoadingModal';

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
  const [fileList, setFileList] = useState<any[]>([]);
  const [exportParams, setExportParams] = useState<Record<string, any>>({});
  const [exporting, setExporting] = useState(false);
  const exportLockRef = useRef(false);

  const handleExport = async () => {
    if (exportLockRef.current) return;
    exportLockRef.current = true;
    setExporting(true);
    try {
      const res: any = await exportInvoices(exportParams);
      const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
      downloadBlob(res, `invoices_${timestamp}.xlsx`);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    } finally {
      exportLockRef.current = false;
      setExporting(false);
    }
  };

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
    setFileList([]);
    setIssueModalVisible(true);
  };

  const handleIssueSubmit = async () => {
    try {
      const values = await issueForm.validateFields();
      setIssuing(true);

      // 1. Upload file if present
      let fileUrl = values.file_url || '';
      if (fileList.length > 0) {
          const file = fileList[0].originFileObj;
          try {
             await uploadInvoice(currentInvoice.id, file);
             // Wait a bit or refetch? 
             // Actually, we just need to ensure issueInvoice uses the uploaded file info if possible.
             // But issueInvoice currently takes file_url.
             // If we upload file, the backend updates 'file' field.
             // We can just pass empty file_url or let the backend handle it.
             // Ideally, we should modify backend issue() to not require file_url if file is present.
          } catch (uploadErr) {
              console.error(uploadErr);
              message.error('文件上传失败');
              setIssuing(false);
              return;
          }
      }

      // 2. Issue invoice
      await issueInvoice(currentInvoice.id, {
          invoice_number: values.invoice_number,
          file_url: fileUrl 
      });
      
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
          const { current, pageSize, ...rest } = params;
          const queryParams = {
            page: current,
            page_size: pageSize,
            ...rest,
          };
          const exportQuery = { ...rest };
          setExportParams(exportQuery);
          const res: any = await getInvoices(queryParams);
          return {
            data: res.results,
            total: res.count,
            success: true,
          };
        }}
        rowKey="id"
        scroll={{ x: 1200 }}
        toolBarRender={() => [
          <Button key="export" icon={<DownloadOutlined />} onClick={handleExport} loading={exporting} disabled={exporting}>
            导出
          </Button>,
        ]}
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
          
          <Form.Item label="上传发票文件">
             <Upload
                fileList={fileList}
                onChange={({ fileList }) => setFileList(fileList)}
                beforeUpload={() => false}
                maxCount={1}
             >
               <Button icon={<UploadOutlined />}>选择文件</Button>
             </Upload>
          </Form.Item>

          <Form.Item
            label="发票文件URL (可选)"
            name="file_url"
            rules={[{ type: 'url', message: '请输入有效的URL' }]}
            tooltip="若已上传文件，此项可留空"
          >
            <Input placeholder="请输入发票PDF下载链接" />
          </Form.Item>
        </Form>
      </Modal>
      <ExportLoadingModal open={exporting} />
    </>
  );
}
