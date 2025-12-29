import { useState, useRef, useEffect } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormDigit, ProFormSelect } from '@ant-design/pro-components';
import { Button, Popconfirm, message, Upload, Image, Form } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getCategories, createCategory, updateCategory, deleteCategory, uploadImage } from '@/services/api';
import { fetchAllPaginated } from '@/utils/request';
import type { ActionType } from '@ant-design/pro-components';

export default function ItemCategories() {
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [logoUrl, setLogoUrl] = useState<string>('');
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [minorCategories, setMinorCategories] = useState<{label: string, value: number}[]>([]);

  useEffect(() => {
      if (modalVisible) {
          fetchAllPaginated<any>(getCategories, { level: 'minor' }, 100).then((data) => {
            setMinorCategories(data.map((c: any) => ({ label: c.name, value: c.id })));
          });

          if (editingRecord) {
              setLogoUrl(editingRecord.logo || '');
              form.setFieldsValue({ 
                  ...editingRecord, 
                  logo: editingRecord.logo,
                  parent_id: editingRecord.parent_id
              });
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
      title: '品项名称', 
      dataIndex: 'name',
      formItemProps: {
        rules: [{ required: false }],
      },
      fieldProps: {
        placeholder: '请输入品项名称搜索',
      },
    },
    {
        title: '所属子品类',
        dataIndex: 'parent_id',
        valueType: 'select',
        request: async () => {
            const data = await fetchAllPaginated<any>(getCategories, { level: 'minor' }, 100);
            return data.map((c: any) => ({ label: c.name, value: c.id }));
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
        headerTitle="品项列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            const { current, pageSize, ...rest } = params;
            const queryParams: any = {
                level: 'item',
                page: current,
                page_size: pageSize,
                ...rest
            };
            
            if (params.name) queryParams.search = params.name;
            
            const res: any = await getCategories(queryParams);
            
            let data = [];
            let total = 0;
            
            if (res.results) {
                data = res.results;
                total = res.count || res.total || 0;
            } else if (Array.isArray(res)) {
                data = res;
                total = res.length;
            } else if (res.data) {
                data = res.data;
                total = res.total || res.length;
            }

            const cleanData = data.map((item: any) => {
                const { children, ...rest } = item;
                return rest;
            });
            
            return { 
              data: cleanData, 
              success: true,
              total: total 
            };
          } catch (error) {
            message.error('加载品项列表失败');
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
            新增品项
          </Button>,
        ]}
      />
      <ModalForm
        title={editingRecord ? '编辑品项' : '新增品项'}
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
                level: 'item'
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
        <ProFormText name="name" label="品项名称" rules={[{ required: true, message: '请输入品项名称' }]} />
        
        <ProFormSelect
            name="parent_id"
            label="所属子品类"
            rules={[{ required: true, message: '请选择所属子品类' }]}
            options={minorCategories}
        />
        
        <Form.Item label="品项Logo">
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
