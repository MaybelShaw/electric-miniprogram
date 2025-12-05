import { useRef, useState, useEffect } from 'react';
import { ProTable, ProDescriptions } from '@ant-design/pro-components';
import { Button, message, Tag, Drawer, List, Avatar, Input, Space, Select, Divider, Upload, Image as AntImage, Modal } from 'antd';
import { EyeOutlined, SendOutlined, UserOutlined, UploadOutlined, PaperClipOutlined, ShoppingOutlined, FileTextOutlined } from '@ant-design/icons';
import { getSupportTickets, getSupportTicket, setSupportTicketStatus, assignSupportTicket, getProducts, getOrders } from '@/services/api';
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
  const { messages: chatMessages, sendMessage, loading: chatLoading } = useSupportChat(currentTicket?.user || null, currentTicket?.id || null);
  const messageListRef = useRef<HTMLDivElement>(null);
  
  const [productModalVisible, setProductModalVisible] = useState(false);
  const [orderModalVisible, setOrderModalVisible] = useState(false);

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

  const handleSendProduct = async (product: any) => {
    setProductModalVisible(false);
    const productInfo = {
      id: product.id,
      name: product.name,
      price: product.price,
      image: product.image
    };
    // Using 'any' for sendMessage arguments to bypass TS check for now as we updated the hook but maybe not the type definition in this file's context if it was imported
    // Actually we updated useSupportChat.ts, so it should be fine if TS picks it up.
    await sendMessage('', undefined, undefined, { product_id: product.id }, { product_info: productInfo });
  };

  const handleSendOrder = async (order: any) => {
    setOrderModalVisible(false);
    // Extract info for optimistic update
    const item = order.items && order.items.length > 0 ? order.items[0] : {};
    const orderInfo = {
      id: order.id,
      order_number: order.order_number,
      status: order.status,
      quantity: order.items?.reduce((acc: number, cur: any) => acc + cur.quantity, 0) || 0,
      total_amount: order.total_amount,
      product_name: item.product_name || '商品',
      image: item.product_image || ''
    };
    await sendMessage('', undefined, undefined, { order_id: order.id }, { order_info: orderInfo });
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

  const getOrderStatusText = (status: string) => {
    const map: any = {
      pending: '待付款',
      paid: '待发货',
      shipped: '已发货',
      completed: '已完成',
      cancelled: '已取消',
      returning: '退货中',
      refunding: '退款中',
      refunded: '已退款'
    };
    return map[status] || status;
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
                <Space direction="vertical" size={5}>
                  <Tag color={statusMap[currentTicket.status]?.color}>
                    {statusMap[currentTicket.status]?.text}
                  </Tag>
                  {(currentUser?.is_staff || currentUser?.role === 'support') && (
                    <Space size={5} wrap>
                      {currentTicket.status === 'open' && (
                        <>
                          <Button size="small" type="primary" onClick={() => handleStatusChange('pending')}>开始处理</Button>
                          <Button size="small" onClick={() => handleStatusChange('resolved')}>已解决</Button>
                          <Button size="small" danger onClick={() => handleStatusChange('closed')}>关闭</Button>
                        </>
                      )}
                      {currentTicket.status === 'pending' && (
                        <>
                          <Button size="small" type="primary" onClick={() => handleStatusChange('resolved')}>已解决</Button>
                          <Button size="small" onClick={() => handleStatusChange('open')}>放回待处理</Button>
                          <Button size="small" danger onClick={() => handleStatusChange('closed')}>关闭</Button>
                        </>
                      )}
                      {currentTicket.status === 'resolved' && (
                        <>
                          <Button size="small" onClick={() => handleStatusChange('open')}>重新打开</Button>
                          <Button size="small" danger onClick={() => handleStatusChange('closed')}>关闭</Button>
                        </>
                      )}
                      {currentTicket.status === 'closed' && (
                        <Button size="small" type="primary" onClick={() => handleStatusChange('open')}>重新打开</Button>
                      )}
                    </Space>
                  )}
                </Space>
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
                            {msg.order_info ? (
                              <div 
                                style={{ width: 200, cursor: 'pointer' }} 
                                onClick={() => window.open(`/orders?id=${msg.order_info?.id}`, '_blank')}
                              >
                                <div style={{ borderBottom: '1px solid #eee', paddingBottom: 4, marginBottom: 4, color: '#999', fontSize: 12, display: 'flex', justifyContent: 'space-between' }}>
                                  <span>订单号: {msg.order_info.order_number}</span>
                                  <span style={{ backgroundColor: '#f6ffed', color: '#52c41a', padding: '0 4px', borderRadius: 2 }}>{getOrderStatusText(msg.order_info.status)}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                  <AntImage 
                                    width={40} 
                                    height={40} 
                                    src={msg.order_info.image} 
                                    preview={false}
                                    style={{ borderRadius: 4, objectFit: 'cover' }}
                                  />
                                  <div style={{ marginLeft: 8, flex: 1, overflow: 'hidden' }}>
                                    <div style={{ fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{msg.order_info.product_name}</div>
                                    <div style={{ color: '#fa4126', fontSize: 12 }}>¥{msg.order_info.total_amount}</div>
                                  </div>
                                </div>
                              </div>
                            ) : msg.product_info ? (
                              <div 
                                style={{ width: 200, cursor: 'pointer' }} 
                                onClick={() => window.open(`/products?id=${msg.product_info?.id}`, '_blank')}
                              >
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                  <AntImage 
                                    width={40} 
                                    height={40} 
                                    src={msg.product_info.image} 
                                    preview={false}
                                    style={{ borderRadius: 4, objectFit: 'cover' }}
                                  />
                                  <div style={{ marginLeft: 8, flex: 1, overflow: 'hidden' }}>
                                    <div style={{ fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{msg.product_info.name}</div>
                                    <div style={{ color: '#fa4126', fontSize: 12 }}>¥{msg.product_info.price}</div>
                                  </div>
                                </div>
                              </div>
                            ) : msg.attachment_type === 'image' ? (
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
              <div style={{ marginBottom: 8, display: 'flex', gap: 8 }}>
                <Upload 
                   customRequest={handleUpload} 
                   showUploadList={false} 
                   accept="image/*,video/*"
                 >
                   <Button icon={<PaperClipOutlined />} size="small">上传图片/视频</Button>
                 </Upload>
                 <Button icon={<ShoppingOutlined />} size="small" onClick={() => setProductModalVisible(true)}>推荐商品</Button>
                 <Button icon={<FileTextOutlined />} size="small" onClick={() => setOrderModalVisible(true)}>关联订单</Button>
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

      <Modal
        title="选择推荐商品"
        visible={productModalVisible}
        onCancel={() => setProductModalVisible(false)}
        footer={null}
        width={800}
        destroyOnClose
      >
        <ProTable
          search={{ labelWidth: 'auto' }}
          rowKey="id"
          columns={[
             { title: 'ID', dataIndex: 'id', width: 60, search: false },
             { title: '商品名称', dataIndex: 'name' },
             { title: '价格', dataIndex: 'price', search: false, render: (dom) => `¥${dom}` },
             { title: '图片', dataIndex: 'image', search: false, render: (_, record: any) => <AntImage src={record.image} width={40} /> },
             { 
               title: '操作', 
               valueType: 'option',
               render: (_, record) => <Button type="link" onClick={() => handleSendProduct(record)}>发送</Button>
             }
          ]}
          request={async (params) => {
            const res: any = await getProducts({ page: params.current, page_size: params.pageSize, ...params });
            return { data: res.results, total: res.count, success: true };
          }}
          pagination={{ pageSize: 5 }}
          options={false}
        />
      </Modal>

      <Modal
        title="选择关联订单"
        visible={orderModalVisible}
        onCancel={() => setOrderModalVisible(false)}
        footer={null}
        width={800}
        destroyOnClose
      >
        <ProTable
          search={false}
          rowKey="id"
          columns={[
             { title: '订单号', dataIndex: 'order_number' },
             { title: '金额', dataIndex: 'total_amount', render: (dom) => `¥${dom}` },
             { title: '状态', dataIndex: 'status', valueEnum: { pending: { text: '待付款' }, paid: { text: '待发货' }, shipped: { text: '已发货' }, completed: { text: '已完成' }, cancelled: { text: '已取消' } } },
             { title: '时间', dataIndex: 'created_at', valueType: 'dateTime' },
             { 
               title: '操作', 
               valueType: 'option',
               render: (_, record) => <Button type="link" onClick={() => handleSendOrder(record)}>发送</Button>
             }
          ]}
          request={async (params) => {
            if (!currentTicket?.user) return { data: [], success: true };
            const res: any = await getOrders({ 
              page: params.current, 
              page_size: params.pageSize, 
              user_id: currentTicket.user, 
              ...params 
            });
            return { data: res.results, total: res.count, success: true };
          }}
          pagination={{ pageSize: 5 }}
          options={false}
        />
      </Modal>
    </>
  );
}
