import { useRef, useState, useEffect } from 'react';
import { ProTable, ProDescriptions } from '@ant-design/pro-components';
import { Button, message, Tag, Drawer, List, Avatar, Input, Space, Select, Divider, Upload, Image as AntImage } from 'antd';
import { EyeOutlined, SendOutlined, UserOutlined, UploadOutlined, PaperClipOutlined } from '@ant-design/icons';
import { getSupportTickets, getSupportTicket, setSupportTicketStatus, assignSupportTicket } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import type { SupportTicket, SupportMessage } from '@/services/types';
import { getUser } from '@/utils/auth';
import { useSupportChat, ExtendedSupportMessage } from './useSupportChat';

const statusMap: Record<string, { text: string; color: string }> = {
  open: { text: '待处理', color: 'blue' },
  pending: { text: '处理中', color: 'orange' },
  resolved: { text: '已解决', color: 'green' },
  closed: { text: '已关闭', color: 'gray' },
};

const priorityMap: Record<string, { text: string; color: string }> = {
  low: { text: '低', color: 'blue' },
  normal: { text: '普通', color: 'orange' },
  high: { text: '高', color: 'red' },
};

export default function Support() {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentTicket, setCurrentTicket] = useState<SupportTicket | null>(null);
  const [messageContent, setMessageContent] = useState('');
  const [sending, setSending] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const { messages: chatMessages, sendMessage, loading: chatLoading } = useSupportChat(currentTicket?.user || null);
  const messageListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [chatMessages, detailVisible]);

  useEffect(() => {
    setCurrentUser(getUser());
  }, []);

  const handleViewDetail = async (record: SupportTicket) => {
    try {
      const res: any = await getSupportTicket(record.id);
      setCurrentTicket(res);
      setDetailVisible(true);
    } catch (error) {
      message.error('获取工单详情失败');
    }
  };

  const handleSendMessage = async () => {
    if (!currentTicket || !messageContent.trim()) return;
    await sendMessage(messageContent);
    setMessageContent('');
  };

  const handleUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    const type = file.type.startsWith('image/') ? 'image' : (file.type.startsWith('video/') ? 'video' : undefined);
    
    if (!type) {
      message.error('仅支持图片和视频');
      return;
    }
    
    try {
      await sendMessage('', file, type);
      onSuccess("ok");
    } catch (e) {
      onError(e);
    }
  };

  const handleStatusChange = async (status: string) => {
    if (!currentTicket) return;
    try {
      await setSupportTicketStatus(currentTicket.id, status);
      message.success('状态更新成功');
      const res: any = await getSupportTicket(currentTicket.id);
      setCurrentTicket(res);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '操作失败');
    }
  };

  const columns: ProColumns<SupportTicket>[] = [
    {
      title: '工单ID',
      dataIndex: 'id',
      width: 80,
      search: false,
    },
    {
      title: '主题',
      dataIndex: 'subject',
      ellipsis: true,
    },
    {
      title: '提交用户',
      dataIndex: 'user_username',
      width: 120,
    },
    {
      title: '关联订单',
      dataIndex: 'order_number',
      width: 150,
      render: (text) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        open: { text: '待处理' },
        pending: { text: '处理中' },
        resolved: { text: '已解决' },
        closed: { text: '已关闭' },
      },
      render: (_, record) => {
        const status = statusMap[record.status];
        return <Tag color={status?.color}>{status?.text}</Tag>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 100,
      valueEnum: {
        low: { text: '低' },
        normal: { text: '普通' },
        high: { text: '高' },
      },
      render: (_, record) => {
        const priority = priorityMap[record.priority];
        return <Tag color={priority?.color}>{priority?.text}</Tag>;
      },
    },
    {
      title: '指派给',
      dataIndex: 'assigned_to_username',
      width: 120,
      render: (text) => text || '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      fixed: 'right',
      render: (_, record) => [
        <Button
          key="view"
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          查看
        </Button>,
      ],
    },
  ];

  return (
    <>
      <ProTable<SupportTicket>
        headerTitle="工单与消息列表"
        tooltip="点击右侧“查看”按钮进入详情页进行聊天"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            const res: any = await getSupportTickets({
              page: params.current,
              page_size: params.pageSize,
              ...params,
            });
            return {
              data: res.results,
              total: res.count,
              success: true,
            };
          } catch (error) {
            return { success: false };
          }
        }}
        rowKey="id"
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 'auto' }}
      />

      <Drawer
        title="工单详情与聊天"
        width={600}
        visible={detailVisible}
        onClose={() => setDetailVisible(false)}
        destroyOnClose
      >
        {currentTicket && (
          <>
            <ProDescriptions column={2} dataSource={currentTicket}>
              <ProDescriptions.Item label="ID" dataIndex="id" />
              <ProDescriptions.Item label="状态">
                <Select
                  defaultValue={currentTicket.status}
                  style={{ width: 120 }}
                  onChange={handleStatusChange}
                  disabled={!(currentUser?.is_staff || currentUser?.role === 'support')}
                >
                  <Select.Option value="open">待处理</Select.Option>
                  <Select.Option value="pending">处理中</Select.Option>
                  <Select.Option value="resolved">已解决</Select.Option>
                  <Select.Option value="closed">已关闭</Select.Option>
                </Select>
              </ProDescriptions.Item>
              <ProDescriptions.Item label="提交用户" dataIndex="user_username" />
              <ProDescriptions.Item label="优先级">
                <Tag color={priorityMap[currentTicket.priority]?.color}>
                  {priorityMap[currentTicket.priority]?.text}
                </Tag>
              </ProDescriptions.Item>
              <ProDescriptions.Item label="关联订单" dataIndex="order_number" />
              <ProDescriptions.Item label="创建时间" dataIndex="created_at" valueType="dateTime" />
              <ProDescriptions.Item label="主题" span={2} dataIndex="subject" />
            </ProDescriptions>

            <Divider orientation="left">消息记录</Divider>
            
            <div ref={messageListRef} style={{ maxHeight: '400px', overflowY: 'auto', marginBottom: '20px', padding: '0 10px' }}>
              <List
                loading={chatLoading}
                dataSource={chatMessages}
                renderItem={(msg: ExtendedSupportMessage) => {
                  const isMe = msg.sender === currentUser?.id;
                  return (
                    <List.Item style={{ 
                      display: 'flex', 
                      justifyContent: isMe ? 'flex-end' : 'flex-start',
                      border: 'none',
                      padding: '8px 0'
                    }}>
                      <div style={{ 
                        display: 'flex', 
                        flexDirection: isMe ? 'row-reverse' : 'row',
                        maxWidth: '80%',
                        alignItems: 'flex-start',
                        opacity: msg.status === 'sending' ? 0.6 : 1
                      }}>
                        <Avatar 
                          icon={<UserOutlined />} 
                          style={{ 
                            backgroundColor: msg.role === 'support' || msg.role === 'admin' ? '#87d068' : '#1890ff',
                            marginLeft: isMe ? 8 : 0,
                            marginRight: isMe ? 0 : 8
                          }} 
                        />
                        <div>
                          <div style={{ 
                            textAlign: isMe ? 'right' : 'left', 
                            fontSize: '12px', 
                            color: '#999', 
                            marginBottom: 4 
                          }}>
                            {msg.sender_username} ({msg.role}) - {new Date(msg.created_at).toLocaleString()}
                          </div>
                          <div style={{ 
                            backgroundColor: msg.status === 'error' ? '#ffccc7' : (isMe ? '#e6f7ff' : '#f5f5f5'), 
                            padding: '8px 12px', 
                            borderRadius: '8px',
                            wordBreak: 'break-word'
                          }}>
                            {msg.attachment_type === 'image' ? (
                              <AntImage 
                                width={200} 
                                src={msg.attachment_url} 
                                style={{ borderRadius: 4 }}
                              />
                            ) : msg.attachment_type === 'video' ? (
                              <video 
                                width={200} 
                                controls 
                                src={msg.attachment_url} 
                                style={{ borderRadius: 4 }}
                              />
                            ) : (
                              msg.content
                            )}
                            {msg.status === 'error' && <span style={{ color: 'red', marginLeft: 4 }}>(发送失败)</span>}
                          </div>
                        </div>
                      </div>
                    </List.Item>
                  );
                }}
              />
            </div>

            <div style={{ marginTop: 'auto' }}>
              <div style={{ marginBottom: 8 }}>
                <Upload 
                   customRequest={handleUpload} 
                   showUploadList={false} 
                   accept="image/*,video/*"
                 >
                   <Button icon={<PaperClipOutlined />} size="small">上传图片/视频</Button>
                 </Upload>
              </div>
              <Input.TextArea
                rows={3}
                value={messageContent}
                onChange={(e) => setMessageContent(e.target.value)}
                placeholder="请输入回复内容..."
                style={{ marginBottom: 10 }}
              />
              <Button 
                type="primary" 
                icon={<SendOutlined />} 
                onClick={handleSendMessage}
                loading={sending}
                block
              >
                发送回复
              </Button>
            </div>
          </>
        )}
      </Drawer>
    </>
  );
}
