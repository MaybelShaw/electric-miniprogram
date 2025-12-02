import { useState, useRef, useEffect } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormDigit } from '@ant-design/pro-components';
import { Button, Popconfirm, message, Upload, Image, Form } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getCategories, createCategory, updateCategory, deleteCategory, uploadImage } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';

export default function MajorCategories() {
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [logoUrl, setLogoUrl] = useState<string>('');
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();

  useEffect(() => {
      if (modalVisible) {
          if (editingRecord) {
              setLogoUrl(editingRecord.logo || '');
              form.setFieldsValue({ ...editingRecord, logo: editingRecord.logo });
          } else {
              setLogoUrl('');
              form.resetFields();
              form.setFieldsValue({ order: 0 });
          }
      }
  }, [modalVisible, editingRecord, form]);

  const handleDelete = async (id: number) => {
    try {
      await deleteCategory(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const columns: any = [
    { 
      title: '空间名称', 
      dataIndex: 'name',
      formItemProps: {
        rules: [{ required: false }],
      },
      fieldProps: {
        placeholder: '请输入空间名称搜索',
      },
    },
    {
      title: 'Logo',
      dataIndex: 'logo',
      hideInSearch: true,
      width: 100,
      render: (_: any, record: any) => record.logo ? (
        <Image src={record.logo} width={40} height={40} style={{ objectFit: 'contain' }} />
      ) : '-',
    },
    { 
      title: '排序', 
      dataIndex: 'order', 
      hideInSearch: true,
      width: 100,
      sorter: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_: any, record: any) => [
        <a key="edit" onClick={() => { setEditingRecord(record); setModalVisible(true); }}>
          编辑
        </a>,
        <Popconfirm key="delete" title="确定删除?" onConfirm={() => handleDelete(record.id)}>
          <a style={{ color: 'red' }}>删除</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <>
      <ProTable
        headerTitle="空间列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            // 构建查询参数
            const queryParams: any = {
                level: 'major'
            };
            
            // 搜索关键词
            if (params.name) {
              queryParams.search = params.name;
            }

            const res: any = await getCategories(queryParams);
            
            // 后端返回的是数组，需要转换为 ProTable 期望的格式
            const data = Array.isArray(res) ? res : (res.results || res.data || []);
            
            // 移除 children 字段，避免 ProTable 自动渲染为树形结构
            const cleanData = data.map((item: any) => {
                const { children, ...rest } = item;
                return rest;
            });
            
            return { 
              data: cleanData, 
              success: true,
              total: cleanData.length 
            };
          } catch (error) {
            message.error('加载空间列表失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        rowKey="id"
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
        options={{
          reload: true,
          density: true,
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalVisible(true); }}>
            新增空间
          </Button>,
        ]}
      />
      <ModalForm
        title={editingRecord ? '编辑空间' : '新增空间'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        form={form}
        autoFocusFirstInput
        modalProps={{
            destroyOnClose: true,
            onCancel: () => setModalVisible(false),
        }}
        onFinish={async (values) => {
          try {
            const submitData = {
                ...values,
                logo: logoUrl,
                level: 'major'
            };
            
            if (editingRecord) {
              await updateCategory(editingRecord.id, submitData);
              message.success('更新成功');
            } else {
              await createCategory(submitData);
              message.success('创建成功');
            }
            setModalVisible(false);
            actionRef.current?.reload();
            return true;
          } catch (error) {
            return false;
          }
        }}
      >
        <ProFormText name="name" label="空间名称" rules={[{ required: true, message: '请输入空间名称' }]} />
        
        <Form.Item label="空间Logo">
            <Upload
                listType="picture-card"
                maxCount={1}
                showUploadList={false}
                customRequest={async (options) => {
                    const { file, onSuccess, onError } = options;
                    try {
                        const res: any = await uploadImage(file as File);
                        const url = res.url || res.file; 
                        setLogoUrl(url);
                        onSuccess?.(res);
                    } catch (err) {
                        onError?.(err as Error);
                        message.error('上传失败');
                    }
                }}
            >
                {logoUrl ? <img src={logoUrl} alt="logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} /> : (
                    <div>
                        <PlusOutlined />
                        <div style={{ marginTop: 8 }}>上传</div>
                    </div>
                )}
            </Upload>
        </Form.Item>
        
        <ProFormDigit name="order" label="排序" fieldProps={{ min: 0 }} />
      </ModalForm>
    </>
  );
}
