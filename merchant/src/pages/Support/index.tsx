import { useRef, useState, useEffect } from 'react';
import { ProTable, ProDescriptions } from '@ant-design/pro-components';
import { Button, message, Drawer, List, Avatar, Input, Divider, Upload, Image as AntImage, Modal } from 'antd';
import { EyeOutlined, SendOutlined, UserOutlined, PaperClipOutlined, ShoppingOutlined, FileTextOutlined } from '@ant-design/icons';
import { getConversations, getProducts, getOrders } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import type { SupportConversation } from '@/services/types';
import { getUser } from '@/utils/auth';
import { useSupportChat, ExtendedSupportMessage } from './useSupportChat';

export default function Support() {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentConversation, setCurrentConversation] = useState<SupportConversation | null>(null);
  const [messageContent, setMessageContent] = useState('');
  const [sending, setSending] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const { messages: chatMessages, sendMessage, loading: chatLoading } = useSupportChat(currentConversation?.user || null, null);
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

  const handleViewDetail = (record: SupportConversation) => {
    setCurrentConversation(record);
    setDetailVisible(true);
  };

  const handleSendMessage = async () => {
    if (!currentConversation || !messageContent.trim()) return;
    setSending(true);
    await sendMessage(messageContent);
    setMessageContent('');
    setSending(false);
  };

  const handleSendProduct = async (product: any) => {
    setProductModalVisible(false);
    const productInfo = {
      id: product.id,
      name: product.name,
      price: product.price,
      image: product.image
    };
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

  const columns: ProColumns<SupportConversation>[] = [
    {
      title: '会话ID',
      dataIndex: 'id',
      width: 80,
      search: false,
    },
    {
      title: '用户',
      dataIndex: 'user_username',
      width: 150,
    },
    {
      title: '最新消息',
      dataIndex: 'last_message',
      ellipsis: true,
      search: false,
      render: (_, record) => {
        const msg = record.last_message;
        if (!msg) return '-';
        if (msg.attachment_type === 'image') return '[图片]';
        if (msg.attachment_type === 'video') return '[视频]';
        if (msg.order_info) return '[订单]';
        if (msg.product_info) return '[商品]';
        return msg.content;
      }
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 180,
      valueType: 'dateTime',
      search: false,
      sorter: (a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      defaultSortOrder: 'descend',
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
      <ProTable<SupportConversation>
        headerTitle="客服会话列表"
        tooltip="点击右侧“查看”按钮进入会话"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            const res: any = await getConversations({
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
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
          collapseRender: false,
        }}
      />

      <Drawer
        title={`与 ${currentConversation?.user_username || '用户'} 的会话`}
        width={600}
        visible={detailVisible}
        onClose={() => setDetailVisible(false)}
        destroyOnClose
      >
        {currentConversation && (
          <>
            <ProDescriptions column={2} dataSource={currentConversation}>
              <ProDescriptions.Item label="用户" dataIndex="user_username" />
              <ProDescriptions.Item label="最后活跃" dataIndex="updated_at" valueType="dateTime" />
            </ProDescriptions>

            <Divider orientation="left">消息记录</Divider>
            
            <div ref={messageListRef} style={{ height: 'calc(100vh - 350px)', overflowY: 'auto', marginBottom: '20px', padding: '0 10px', border: '1px solid #f0f0f0', borderRadius: '4px' }}>
              <List
                loading={chatLoading}
                dataSource={chatMessages}
                renderItem={(msg: ExtendedSupportMessage) => {
                  const isMe = msg.sender === currentUser?.id || msg.role === 'support' || msg.role === 'admin';
                  // Note: msg.sender is ID, currentUser.id is ID. 
                  // If I am admin, my messages should be on right.
                  // Messages from user should be on left.
                  
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
                        maxWidth: '85%',
                        alignItems: 'flex-start',
                        opacity: msg.status === 'sending' ? 0.6 : 1
                      }}>
                        <Avatar 
                          icon={<UserOutlined />} 
                          style={{ 
                            backgroundColor: isMe ? '#87d068' : '#1890ff',
                            marginLeft: isMe ? 8 : 0,
                            marginRight: isMe ? 0 : 8,
                            flexShrink: 0
                          }} 
                        />
                        <div style={{ minWidth: 0 }}>
                          <div style={{ 
                            textAlign: isMe ? 'right' : 'left', 
                            fontSize: '12px', 
                            color: '#999', 
                            marginBottom: 4 
                          }}>
                            {msg.sender_username || (isMe ? '我' : '用户')} - {new Date(msg.created_at).toLocaleString()}
                          </div>
                          <div style={{ 
                            backgroundColor: msg.status === 'error' ? '#ffccc7' : (isMe ? '#e6f7ff' : '#f5f5f5'), 
                            padding: '8px 12px', 
                            borderRadius: '8px',
                            wordBreak: 'break-word'
                          }}>
                            {msg.order_info ? (
                              <div 
                                style={{ width: 220, cursor: 'pointer' }} 
                                onClick={() => window.open(`/orders?id=${msg.order_info?.id}`, '_blank')}
                              >
                                <div style={{ borderBottom: '1px solid #ddd', paddingBottom: 4, marginBottom: 4, color: '#666', fontSize: 12, display: 'flex', justifyContent: 'space-between' }}>
                                  <span>订单号: {msg.order_info.order_number}</span>
                                  <span style={{ backgroundColor: '#f6ffed', color: '#52c41a', padding: '0 4px', borderRadius: 2 }}>{getOrderStatusText(msg.order_info.status)}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                  <AntImage 
                                    width={50} 
                                    height={50} 
                                    src={msg.order_info.image} 
                                    preview={false}
                                    style={{ borderRadius: 4, objectFit: 'cover', border: '1px solid #eee' }}
                                  />
                                  <div style={{ marginLeft: 8, flex: 1, overflow: 'hidden' }}>
                                    <div style={{ fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{msg.order_info.product_name}</div>
                                    <div style={{ color: '#fa4126', fontSize: 12, marginTop: 4 }}>¥{msg.order_info.total_amount}</div>
                                  </div>
                                </div>
                              </div>
                            ) : msg.product_info ? (
                              <div 
                                style={{ width: 220, cursor: 'pointer' }} 
                                onClick={() => window.open(`/products?id=${msg.product_info?.id}`, '_blank')}
                              >
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                  <AntImage 
                                    width={50} 
                                    height={50} 
                                    src={msg.product_info.image} 
                                    preview={false}
                                    style={{ borderRadius: 4, objectFit: 'cover', border: '1px solid #eee' }}
                                  />
                                  <div style={{ marginLeft: 8, flex: 1, overflow: 'hidden' }}>
                                    <div style={{ fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{msg.product_info.name}</div>
                                    <div style={{ color: '#fa4126', fontSize: 12, marginTop: 4 }}>¥{msg.product_info.price}</div>
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
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
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
          search={{
            labelWidth: 'auto',
            defaultCollapsed: false,
            collapseRender: false,
          }}
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
             { 
               title: '操作', 
               valueType: 'option',
               render: (_, record) => <Button type="link" onClick={() => handleSendOrder(record)}>发送</Button>
             }
          ]}
          request={async (params) => {
             const res: any = await getOrders({ page: params.current, page_size: params.pageSize, ...params });
             return { data: res.results, total: res.count, success: true };
          }}
          pagination={{ pageSize: 5 }}
          options={false}
        />
      </Modal>
    </>
  );
}
