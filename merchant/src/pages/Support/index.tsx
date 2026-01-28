import { useRef, useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ProTable, ProDescriptions, ModalForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormSwitch, ProFormDigit, ProFormDependency, ProFormList } from '@ant-design/pro-components';
import { Button, message, Drawer, List, Avatar, Input, Divider, Upload, Image as AntImage, Modal, Select, Tag, Form, Popconfirm, Space } from 'antd';
import { EyeOutlined, SendOutlined, UserOutlined, PaperClipOutlined, ShoppingOutlined, FileTextOutlined, PlusOutlined } from '@ant-design/icons';
import { getConversations, getProducts, getOrders, getSupportReplyTemplates, createSupportReplyTemplate, updateSupportReplyTemplate, deleteSupportReplyTemplate } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import type { SupportConversation, SupportReplyTemplate } from '@/services/types';
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
  const [templateModalVisible, setTemplateModalVisible] = useState(false);
  const [replyTemplates, setReplyTemplates] = useState<SupportReplyTemplate[]>([]);
  const [templateKeyword, setTemplateKeyword] = useState('');
  const [templateGroup, setTemplateGroup] = useState<string | undefined>(undefined);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [templateFormVisible, setTemplateFormVisible] = useState(false);
  const [templateEditing, setTemplateEditing] = useState<SupportReplyTemplate | null>(null);
  const templateActionRef = useRef<ActionType>();
  const [templateForm] = Form.useForm();
  const location = useLocation();
  const isTemplateManageView = location.pathname.includes('/support/templates');

  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [chatMessages, detailVisible]);

  useEffect(() => {
    setCurrentUser(getUser());
  }, []);

  const fetchQuickTemplates = async () => {
    setTemplateLoading(true);
    try {
      const res: any = await getSupportReplyTemplates({
        type: 'B',
        enabled: true,
        search: templateKeyword || undefined,
        group: templateGroup || undefined
      });
      setReplyTemplates(res?.results || res || []);
    } catch (error) {
      message.error('获取快捷回复失败');
    } finally {
      setTemplateLoading(false);
    }
  };

  useEffect(() => {
    if (!templateModalVisible) return;
    fetchQuickTemplates();
  }, [templateModalVisible, templateKeyword, templateGroup]);

  useEffect(() => {
    if (!templateFormVisible) return;
    if (templateEditing) {
      const payload: any = templateEditing.content_payload || {};
      templateForm.setFieldsValue({
        template_type: templateEditing.template_type,
        title: templateEditing.title,
        content: templateEditing.content,
        content_type: templateEditing.content_type,
        group_name: templateEditing.group_name,
        is_pinned: templateEditing.is_pinned,
        enabled: templateEditing.enabled,
        trigger_event: templateEditing.trigger_event || undefined,
        idle_minutes: templateEditing.idle_minutes ?? undefined,
        daily_limit: templateEditing.daily_limit ?? undefined,
        user_cooldown_days: templateEditing.user_cooldown_days ?? undefined,
        sort_order: templateEditing.sort_order,
        card_payload: {
          title: payload.title,
          description: payload.description,
          image_url: payload.image_url,
          link_type: payload.link_type,
          link_value: payload.link_value
        },
        quick_buttons: Array.isArray(payload.buttons) ? payload.buttons : []
      });
      return;
    }
    templateForm.resetFields();
    templateForm.setFieldsValue({
      template_type: 'quick',
      content_type: 'text',
      enabled: true,
      is_pinned: false,
      sort_order: 0,
      trigger_event: 'first_contact',
      idle_minutes: undefined,
      daily_limit: 1,
      user_cooldown_days: 1,
      quick_buttons: []
    });
  }, [templateFormVisible, templateEditing, templateForm]);

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

  const handleUseTemplate = (template: SupportReplyTemplate) => {
    setMessageContent(template.content || template.title || '');
    setTemplateModalVisible(false);
  };

  const handleSendTemplate = async (template: SupportReplyTemplate) => {
    if (!currentConversation) return;
    setTemplateModalVisible(false);
    await sendMessage(
      template.content || '',
      undefined,
      undefined,
      { template_id: template.id },
      { template_info: { content: template.content, title: template.title, content_type: template.content_type, content_payload: template.content_payload } }
    );
  };

  const handleOpenTemplateCreate = () => {
    setTemplateEditing(null);
    setTemplateFormVisible(true);
  };

  const handleOpenTemplateEdit = (record: SupportReplyTemplate) => {
    setTemplateEditing(record);
    setTemplateFormVisible(true);
  };

  const handleDeleteTemplate = async (record: SupportReplyTemplate) => {
    try {
      await deleteSupportReplyTemplate(record.id);
      message.success('已删除模板');
      templateActionRef.current?.reload();
      if (templateModalVisible) {
        fetchQuickTemplates();
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败');
    }
  };

  const handleSubmitTemplate = async (values: any) => {
    const payload: any = {
      template_type: values.template_type,
      title: values.title,
      content: values.content || '',
      content_type: values.content_type,
      group_name: values.group_name || undefined,
      is_pinned: values.is_pinned || false,
      enabled: values.enabled !== undefined ? values.enabled : true,
      sort_order: values.sort_order ?? 0,
      trigger_event: values.template_type === 'auto' ? values.trigger_event : undefined,
      idle_minutes: values.template_type === 'auto' ? values.idle_minutes ?? undefined : undefined,
      daily_limit: values.template_type === 'auto' ? values.daily_limit ?? undefined : undefined,
      user_cooldown_days: values.template_type === 'auto' ? values.user_cooldown_days ?? undefined : undefined
    };
    if (values.content_type === 'card') {
      payload.content_payload = {
        title: values.card_payload?.title,
        description: values.card_payload?.description,
        image_url: values.card_payload?.image_url,
        link_type: values.card_payload?.link_type,
        link_value: values.card_payload?.link_value
      };
    }
    if (values.content_type === 'quick_buttons') {
      const buttons = Array.isArray(values.quick_buttons) ? values.quick_buttons : [];
      payload.content_payload = {
        buttons: buttons
          .filter((btn: any) => btn?.text || btn?.value)
          .map((btn: any) => ({ text: btn.text, value: btn.value }))
      };
    }
    try {
      if (templateEditing) {
        await updateSupportReplyTemplate(templateEditing.id, payload);
        message.success('已更新模板');
      } else {
        await createSupportReplyTemplate(payload);
        message.success('已创建模板');
      }
      setTemplateFormVisible(false);
      setTemplateEditing(null);
      templateActionRef.current?.reload();
      if (templateModalVisible) {
        fetchQuickTemplates();
      }
      return true;
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
      return false;
    }
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
    if (currentConversation && order?.user && order.user !== currentConversation.user) {
      message.error('订单所属用户与当前会话用户不一致');
      return;
    }
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

  const renderMessageBody = (msg: ExtendedSupportMessage) => {
    if (msg.order_info) {
      return (
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
      );
    }
    if (msg.product_info) {
      return (
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
      );
    }
    if (msg.attachment_type === 'image') {
      return (
        <AntImage 
          width={200} 
          src={msg.attachment_url} 
          style={{ borderRadius: 4 }}
        />
      );
    }
    if (msg.attachment_type === 'video') {
      return (
        <video 
          width={200} 
          controls 
          src={msg.attachment_url} 
          style={{ borderRadius: 4 }}
        />
      );
    }
    if (msg.content_type === 'card') {
      const payload: any = msg.content_payload || {};
      return (
        <div style={{ width: 240 }}>
          {payload.image_url && (
            <AntImage 
              width={220} 
              src={payload.image_url} 
              preview={false}
              style={{ borderRadius: 4, marginBottom: 6 }}
            />
          )}
          <div style={{ fontWeight: 600 }}>{payload.title || msg.content}</div>
          {payload.description && <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{payload.description}</div>}
        </div>
      );
    }
    if (msg.content_type === 'quick_buttons') {
      const payload: any = msg.content_payload || {};
      const buttons: any[] = Array.isArray(payload.buttons) ? payload.buttons : [];
      return (
        <div>
          {msg.content && <div style={{ marginBottom: 6 }}>{msg.content}</div>}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {buttons.map((btn, index) => (
              <Button key={`${btn.text || btn.value}-${index}`} size="small" disabled>
                {btn.text || btn.value}
              </Button>
            ))}
          </div>
        </div>
      );
    }
    return msg.content;
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

  const templateColumns: ProColumns<SupportReplyTemplate>[] = [
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true
    },
    {
      title: '模板类型',
      dataIndex: 'template_type',
      valueEnum: {
        quick: '快捷回复',
        auto: '自动回复'
      }
    },
    {
      title: '内容类型',
      dataIndex: 'content_type',
      valueEnum: {
        text: '文本',
        card: '图文卡片',
        quick_buttons: '快捷按钮'
      }
    },
    {
      title: '分组',
      dataIndex: 'group_name'
    },
    {
      title: '置顶',
      dataIndex: 'is_pinned',
      search: false,
      render: (_, record) => record.is_pinned ? <Tag color="gold">常用</Tag> : '-'
    },
    {
      title: '启用',
      dataIndex: 'enabled',
      valueEnum: {
        true: { text: '启用', status: 'Success' },
        false: { text: '停用', status: 'Default' }
      },
      render: (_, record) => record.enabled ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      valueType: 'dateTime',
      search: false,
      width: 160
    },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => handleOpenTemplateEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除该模板?" onConfirm={() => handleDeleteTemplate(record)}>
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <>
      {isTemplateManageView ? (
        <>
          <ProTable<SupportReplyTemplate>
            actionRef={templateActionRef}
            columns={templateColumns}
            rowKey="id"
            search={{
              labelWidth: 'auto',
              defaultCollapsed: false,
              collapseRender: false
            }}
            toolBarRender={() => [
              <Button key="create" type="primary" icon={<PlusOutlined />} onClick={handleOpenTemplateCreate}>
                新增模板
              </Button>
            ]}
            request={async (params) => {
              try {
                const queryParams: any = {
                  page: params.current,
                  page_size: params.pageSize
                };
                if (params.title) {
                  queryParams.search = params.title;
                }
                if (params.group_name) {
                  queryParams.group = params.group_name;
                }
                if (params.content_type) {
                  queryParams.content_type = params.content_type;
                }
                if (params.template_type) {
                  queryParams.template_type = params.template_type;
                }
                if (params.enabled !== undefined) {
                  queryParams.enabled = params.enabled;
                }
                const res: any = await getSupportReplyTemplates(queryParams);
                return {
                  data: res.results || res || [],
                  success: true,
                  total: res.count || res.pagination?.total || res.total || 0
                };
              } catch (error) {
                return { success: false };
              }
            }}
            pagination={{ pageSize: 10, showSizeChanger: true }}
          />
          <ModalForm
            title={templateEditing ? '编辑模板' : '新增模板'}
            open={templateFormVisible}
            onOpenChange={setTemplateFormVisible}
            form={templateForm}
            onFinish={handleSubmitTemplate}
            modalProps={{ destroyOnClose: true }}
            width={640}
          >
            <ProFormSelect
              name="template_type"
              label="模板类型"
              valueEnum={{ quick: '快捷回复', auto: '自动回复' }}
              rules={[{ required: true, message: '请选择模板类型' }]}
            />
            <ProFormText
              name="title"
              label="标题"
              placeholder="请输入模板标题"
              rules={[{ required: true, message: '请输入模板标题' }]}
            />
            <ProFormSelect
              name="content_type"
              label="内容类型"
              valueEnum={{ text: '文本', card: '图文卡片', quick_buttons: '快捷按钮' }}
              rules={[{ required: true, message: '请选择内容类型' }]}
            />
            <ProFormDependency name={['template_type', 'trigger_event']}>
              {({ template_type, trigger_event }) => {
                if (template_type !== 'auto') return null;
                return (
                  <>
                    <ProFormSelect
                      name="trigger_event"
                      label="触发条件"
                      valueEnum={{ first_contact: '首次联系', idle_contact: '长时间未联系', both: '首次联系 + 长时间未联系' }}
                      rules={[{ required: true, message: '请选择触发条件' }]}
                    />
                    {(trigger_event === 'idle_contact' || trigger_event === 'both') && (
                      <ProFormDigit
                        name="idle_minutes"
                        label="未联系分钟数"
                        tooltip="用户进入会话后超过该分钟数仍未联系时触发"
                        fieldProps={{ min: 1, precision: 0 }}
                        rules={[{ required: true, message: '请输入分钟数' }]}
                      />
                    )}
                    <ProFormDigit
                      name="daily_limit"
                      label="日限额"
                      tooltip="单个用户每天最多触发次数，0 表示不限制"
                      fieldProps={{ min: 0, precision: 0 }}
                      rules={[{ required: true, message: '请输入日限额' }]}
                    />
                    <ProFormDigit
                      name="user_cooldown_days"
                      label="用户冷却天数"
                      tooltip="同一用户两次自动回复之间的最小间隔天数"
                      fieldProps={{ min: 0, precision: 0 }}
                      rules={[{ required: true, message: '请输入冷却天数' }]}
                    />
                  </>
                );
              }}
            </ProFormDependency>
            <ProFormDependency name={['content_type']}>
              {({ content_type }) => (
                <ProFormTextArea
                  name="content"
                  label="模板内容"
                  placeholder={content_type === 'text' ? '请输入文本内容' : '请输入模板内容'}
                  rules={[{ required: true, message: '请输入模板内容' }]}
                />
              )}
            </ProFormDependency>
            <ProFormText name="group_name" label="分组" placeholder="可选" />
            <ProFormDigit name="sort_order" label="排序" fieldProps={{ min: 0, precision: 0 }} />
            <ProFormSwitch name="is_pinned" label="置顶" />
            <ProFormSwitch name="enabled" label="启用" />
            <ProFormDependency name={['content_type']}>
              {({ content_type }) => {
                if (content_type === 'card') {
                  return (
                    <>
                      <ProFormText name={['card_payload', 'title']} label="卡片标题" rules={[{ required: true, message: '请输入卡片标题' }]} />
                      <ProFormTextArea name={['card_payload', 'description']} label="卡片描述" />
                      <ProFormText name={['card_payload', 'image_url']} label="图片链接" placeholder="https://..." />
                      <ProFormSelect
                        name={['card_payload', 'link_type']}
                        label="跳转类型"
                        valueEnum={{ product: '商品', order: '订单', url: 'URL', none: '无' }}
                      />
                      <ProFormText name={['card_payload', 'link_value']} label="跳转值" placeholder="商品ID/订单ID/URL" />
                    </>
                  );
                }
                if (content_type === 'quick_buttons') {
                  return (
                    <ProFormList
                      name="quick_buttons"
                      label="按钮列表"
                      creatorButtonProps={{ creatorButtonText: '添加按钮' }}
                    >
                      <ProFormText name="text" label="按钮文案" rules={[{ required: true, message: '请输入按钮文案' }]} />
                      <ProFormText name="value" label="发送内容" rules={[{ required: true, message: '请输入发送内容' }]} />
                    </ProFormList>
                  );
                }
                return null;
              }}
            </ProFormDependency>
          </ModalForm>
        </>
      ) : (
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
                                {renderMessageBody(msg)}
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
                    <Button size="small" onClick={() => setTemplateModalVisible(true)}>快捷回复</Button>
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
                const queryParams: any = {
                  page: params.current,
                  page_size: params.pageSize || 5,
                };
                if (params.name) {
                  queryParams.search = params.name;
                }
                const res: any = await getProducts(queryParams);
                return { data: res.results || [], total: res.total || res.count || 0, success: true };
              }}
              pagination={{ defaultPageSize: 5, showSizeChanger: true, pageSizeOptions: ['5', '10', '20', '50'] }}
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
                 if (!currentConversation?.user) {
                   return { data: [], total: 0, success: true };
                 }
                 const res: any = await getOrders({
                   page: params.current,
                   page_size: params.pageSize,
                   user_id: currentConversation.user,
                 });
                 return { data: res.results || [], total: res.count || res.total || 0, success: true };
              }}
              pagination={{ pageSize: 5 }}
              options={false}
            />
          </Modal>

          <Modal
            title="快捷回复"
            visible={templateModalVisible}
            onCancel={() => setTemplateModalVisible(false)}
            footer={null}
            width={720}
            destroyOnClose
          >
            <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
              <Input.Search
                placeholder="搜索快捷回复"
                allowClear
                onSearch={(value) => setTemplateKeyword(value)}
                onChange={(e) => setTemplateKeyword(e.target.value)}
                value={templateKeyword}
              />
              <Select
                allowClear
                placeholder="选择分组"
                style={{ width: 180 }}
                value={templateGroup}
                onChange={(value) => setTemplateGroup(value)}
                options={[
                  ...Array.from(new Set(replyTemplates.map(t => t.group_name || '').filter(Boolean))).map(group => ({
                    label: group,
                    value: group
                  }))
                ]}
              />
            </div>
            <List
              loading={templateLoading}
              dataSource={[...replyTemplates].sort((a, b) => {
                const pinDiff = (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0);
                if (pinDiff !== 0) return pinDiff;
                return (a.sort_order || 0) - (b.sort_order || 0);
              })}
              renderItem={(template) => (
                <List.Item
                  actions={[
                    <Button key="use" size="small" onClick={() => handleUseTemplate(template)}>填入</Button>,
                    <Button key="send" type="primary" size="small" onClick={() => handleSendTemplate(template)}>发送</Button>
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span>{template.title}</span>
                        {template.is_pinned && <Tag color="gold">常用</Tag>}
                        {template.group_name && <Tag>{template.group_name}</Tag>}
                      </div>
                    }
                    description={
                      <div>
                        <div style={{ color: '#666' }}>{template.content || '-'}</div>
                        <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                          使用 {template.usage_count || 0} 次 · 最近 {template.last_used_at ? new Date(template.last_used_at).toLocaleString() : '未使用'}
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </Modal>
        </>
      )}
    </>
  );
}
