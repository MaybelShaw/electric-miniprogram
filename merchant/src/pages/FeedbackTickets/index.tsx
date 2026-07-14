import { useRef, useState } from 'react';
import { ProTable, ProDescriptions } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Drawer, Form, Image, Input, List, Modal, Space, Tag, Upload, message } from 'antd';
import { CloseOutlined, EyeOutlined, UploadOutlined } from '@ant-design/icons';
import { closeFeedbackTicket, getFeedbackTicket, getFeedbackTickets, replyFeedbackTicket } from '@/services/api';
import type { FeedbackTicket, FeedbackTicketReply } from '@/services/types';
import { getUser } from '@/utils/auth';

const typeMap = {
  question: { text: '问题', color: 'blue' },
  requirement: { text: '需求', color: 'purple' },
};

const statusMap = {
  pending: { text: '待处理', color: 'orange' },
  replied: { text: '已回复', color: 'green' },
  closed: { text: '已关闭', color: 'default' },
};

export default function FeedbackTickets() {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentTicket, setCurrentTicket] = useState<FeedbackTicket | null>(null);
  const [replyContent, setReplyContent] = useState('');
  const [replyFiles, setReplyFiles] = useState<any[]>([]);
  const [replying, setReplying] = useState(false);
  const currentUser = getUser();

  const canClose = Boolean(
    currentTicket &&
      (currentUser?.is_superuser ||
        currentUser?.store_roles?.some(
          (role: any) =>
            role?.status === 'active' &&
            role?.store === currentTicket.store &&
            role?.role === 'store_admin',
        )),
  );

  const refreshDetail = async (id: number) => {
    const data: any = await getFeedbackTicket(id);
    setCurrentTicket(data);
  };

  const openDetail = async (record: FeedbackTicket) => {
    setDetailVisible(true);
    setReplyContent('');
    setReplyFiles([]);
    await refreshDetail(record.id);
  };

  const handleReply = async () => {
    if (!currentTicket || !replyContent.trim()) {
      message.warning('请填写回复内容');
      return;
    }
    setReplying(true);
    try {
      await replyFeedbackTicket(
        currentTicket.id,
        replyContent.trim(),
        replyFiles.map(item => item.originFileObj).filter(Boolean),
      );
      message.success('已回复');
      setReplyContent('');
      setReplyFiles([]);
      await refreshDetail(currentTicket.id);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '回复失败');
    } finally {
      setReplying(false);
    }
  };

  const handleClose = () => {
    if (!currentTicket) return;
    let note = '';
    Modal.confirm({
      title: '关闭工单',
      content: (
        <Input.TextArea
          rows={3}
          placeholder="关闭说明，可选"
          onChange={(event) => {
            note = event.target.value;
          }}
        />
      ),
      onOk: async () => {
        try {
          await closeFeedbackTicket(currentTicket.id, note);
          message.success('已关闭');
          await refreshDetail(currentTicket.id);
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '关闭失败');
        }
      },
    });
  };

  const renderImages = (images?: string[]) => {
    if (!images?.length) return null;
    return (
      <Image.PreviewGroup>
        <Space size={8} wrap style={{ marginTop: 8 }}>
          {images.map((url, index) => (
            <Image key={`${url}-${index}`} width={72} height={72} src={url} style={{ objectFit: 'cover', borderRadius: 4 }} />
          ))}
        </Space>
      </Image.PreviewGroup>
    );
  };

  const renderRecord = (item: FeedbackTicketReply) => (
    <List.Item>
      <List.Item.Meta
        title={
          <Space>
            <Tag color={item.record_type === 'merchant_reply' ? 'green' : item.record_type === 'close' ? 'default' : 'blue'}>
              {item.record_type_display}
            </Tag>
            <span>{item.sender_username}</span>
            <span style={{ color: '#999', fontWeight: 400 }}>{new Date(item.created_at).toLocaleString()}</span>
          </Space>
        }
        description={
          <div>
            <div style={{ whiteSpace: 'pre-wrap', color: '#333' }}>{item.content || (item.record_type === 'close' ? '工单已关闭' : '')}</div>
            {renderImages(item.attachments)}
          </div>
        }
      />
    </List.Item>
  );

  const columns: ProColumns<FeedbackTicket>[] = [
    { title: '编号', dataIndex: 'ticket_number', width: 150 },
    {
      title: '类型',
      dataIndex: 'ticket_type',
      width: 90,
      valueEnum: { question: '问题', requirement: '需求' },
      render: (_, record) => <Tag color={typeMap[record.ticket_type]?.color}>{record.ticket_type_display}</Tag>,
    },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '店铺', dataIndex: 'store_name', search: false, width: 140 },
    { title: '用户', dataIndex: 'user_username', search: false, width: 130 },
    { title: '联系电话', dataIndex: 'contact_phone', search: false, width: 130 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: { pending: '待处理', replied: '已回复', closed: '已关闭' },
      render: (_, record) => <Tag color={statusMap[record.status]?.color}>{record.status_display}</Tag>,
    },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', search: false, width: 170 },
    { title: '最后回复', dataIndex: 'last_replied_at', valueType: 'dateTime', search: false, width: 170 },
    {
      title: '操作',
      valueType: 'option',
      width: 90,
      fixed: 'right',
      render: (_, record) => (
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openDetail(record)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <>
      <ProTable<FeedbackTicket>
        headerTitle="问题建议工单"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto', defaultCollapsed: false, collapseRender: false }}
        request={async (params) => {
          try {
            const query: any = {
              page: params.current,
              page_size: params.pageSize,
              search: params.ticket_number || params.title,
              ticket_type: params.ticket_type,
              status: params.status,
            };
            const res: any = await getFeedbackTickets(query);
            return { data: res.results || [], total: res.count || res.total || 0, success: true };
          } catch {
            return { data: [], total: 0, success: false };
          }
        }}
      />

      <Drawer
        title={currentTicket ? `工单 ${currentTicket.ticket_number}` : '工单详情'}
        width={720}
        visible={detailVisible}
        onClose={() => setDetailVisible(false)}
        destroyOnClose
      >
        {currentTicket && (
          <>
            <ProDescriptions column={2} dataSource={currentTicket}>
              <ProDescriptions.Item label="标题" dataIndex="title" span={2} />
              <ProDescriptions.Item label="类型">
                <Tag color={typeMap[currentTicket.ticket_type]?.color}>{currentTicket.ticket_type_display}</Tag>
              </ProDescriptions.Item>
              <ProDescriptions.Item label="状态">
                <Tag color={statusMap[currentTicket.status]?.color}>{currentTicket.status_display}</Tag>
              </ProDescriptions.Item>
              <ProDescriptions.Item label="店铺" dataIndex="store_name" />
              <ProDescriptions.Item label="用户" dataIndex="user_username" />
              <ProDescriptions.Item label="联系电话" dataIndex="contact_phone" />
              <ProDescriptions.Item label="创建时间" dataIndex="created_at" valueType="dateTime" />
            </ProDescriptions>

            <div style={{ margin: '16px 0' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>用户提交</div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{currentTicket.content}</div>
              {renderImages(currentTicket.attachments)}
            </div>

            <List
              header={<strong>处理记录</strong>}
              dataSource={currentTicket.replies || []}
              renderItem={renderRecord}
              locale={{ emptyText: '暂无处理记录' }}
            />

            {currentTicket.status !== 'closed' && (
              <div style={{ marginTop: 20 }}>
                <Form layout="vertical">
                  <Form.Item label="回复内容" required>
                    <Input.TextArea rows={4} value={replyContent} onChange={(event) => setReplyContent(event.target.value)} />
                  </Form.Item>
                  <Form.Item label="图片附件" extra="无固定比例，建议上传清晰原图；最多 9 张">
                    <Upload
                      beforeUpload={() => false}
                      accept="image/*"
                      multiple
                      maxCount={9}
                      fileList={replyFiles}
                      onChange={({ fileList }) => setReplyFiles(fileList)}
                    >
                      <Button icon={<UploadOutlined />}>上传图片</Button>
                    </Upload>
                  </Form.Item>
                  <Space>
                    <Button type="primary" loading={replying} onClick={handleReply}>
                      回复
                    </Button>
                    {canClose && (
                      <Button danger icon={<CloseOutlined />} onClick={handleClose}>
                        关闭工单
                      </Button>
                    )}
                  </Space>
                </Form>
              </div>
            )}
          </>
        )}
      </Drawer>
    </>
  );
}
