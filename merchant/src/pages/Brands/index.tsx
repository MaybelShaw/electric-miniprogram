import { useState, useRef, useEffect } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormDigit, ProFormSwitch, ProFormTextArea } from '@ant-design/pro-components';
import { Button, Popconfirm, message, Tag, Modal, Form, Upload, Input } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getBrands, createBrand, updateBrand, deleteBrand, uploadImage } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';

export default function Brands() {
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [logoUrl, setLogoUrl] = useState<string>('');
  const [form] = Form.useForm();
  const actionRef = useRef<ActionType>();

  useEffect(() => {
    if (modalVisible) {
      if (editingRecord) {
        setLogoUrl(editingRecord.logo || '');
        form.setFieldsValue(editingRecord);
      } else {
        setLogoUrl('');
        form.resetFields();
        form.setFieldsValue({ order: 0, is_active: true });
      }
    }
  }, [modalVisible, editingRecord, form]);

  const handleDelete = async (id: number, force = false) => {
    try {
      await deleteBrand(id, force);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      const errorData = error.response?.data;
      if (errorData?.associated_products_count > 0) {
        Modal.confirm({
          title: '确认删除',
          content: `该品牌有 ${errorData.associated_products_count} 个关联商品，是否强制删除？`,
          okText: '强制删除',
          okType: 'danger',
          cancelText: '取消',
          onOk: () => handleDelete(id, true),
        });
      } else {
        message.error(errorData?.message || '删除失败');
      }
    }
  };

  const columns: any = [
    { 
      title: '品牌名称', 
      dataIndex: 'name',
      formItemProps: {
        rules: [{ required: false }],
      },
      fieldProps: {
        placeholder: '请输入品牌名称搜索',
      },
    },
    { 
      title: 'Logo', 
      dataIndex: 'logo', 
      hideInSearch: true,
      width: 100,
      render: (logo: string) => logo ? <img src={logo} alt="logo" style={{ width: 40, height: 40, objectFit: 'contain' }} /> : '-'
    },
    { 
      title: '描述', 
      dataIndex: 'description', 
      hideInSearch: true,
      ellipsis: true 
    },
    { 
      title: '排序', 
      dataIndex: 'order', 
      hideInSearch: true,
      width: 100,
      sorter: true,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      valueType: 'select',
      valueEnum: {
        true: { text: '启用', status: 'Success' },
        false: { text: '禁用', status: 'Error' },
      },
      render: (_: any, record: any) => (
        <Tag color={record.is_active ? 'green' : 'red'}>
          {record.is_active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    { 
      title: '创建时间', 
      dataIndex: 'created_at', 
      hideInSearch: true,
      valueType: 'dateTime', 
      width: 180 
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
        headerTitle="品牌列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            // 构建查询参数
            const queryParams: any = {};
            
            // 搜索关键词
            if (params.name) {
              queryParams.search = params.name;
            }
            
            // 状态筛选
            if (params.is_active !== undefined) {
              queryParams.is_active = params.is_active;
            }

            const res: any = await getBrands(queryParams);
            
            // 后端返回的是数组，需要转换为 ProTable 期望的格式
            const data = Array.isArray(res) ? res : (res.results || res.data || []);
            return { 
              data: data, 
              success: true,
              total: data.length 
            };
          } catch (error) {
            message.error('加载品牌列表失败');
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
            新增品牌
          </Button>,
        ]}
      />
      <ModalForm
        title={editingRecord ? '编辑品牌' : '新增品牌'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        form={form}
        onFinish={async (values) => {
          try {
            if (editingRecord) {
              await updateBrand(editingRecord.id, values);
              message.success('更新成功');
            } else {
              await createBrand(values);
              message.success('创建成功');
            }
            actionRef.current?.reload();
            return true;
          } catch (error) {
            return false;
          }
        }}
      >
        <ProFormText name="name" label="品牌名称" rules={[{ required: true, message: '请输入品牌名称' }]} />
        <Form.Item label="Logo URL">
          <Form.Item name="logo" noStyle hidden>
            <Input />
          </Form.Item>
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
                form.setFieldValue('logo', url);
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
        <ProFormTextArea name="description" label="品牌描述" placeholder="请输入品牌描述" />
        <ProFormDigit name="order" label="排序" fieldProps={{ min: 0 }} />
        <ProFormSwitch name="is_active" label="是否启用" />
      </ModalForm>
    </>
  );
}
