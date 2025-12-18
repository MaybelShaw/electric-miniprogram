import { useState, useRef, useEffect } from 'react';
import { 
  ProTable, 
  ModalForm, 
  ProFormText, 
  ProFormDigit, 
  ProFormSwitch, 
  ProFormList, 
  ProFormSelect,
  ProFormTextArea,
  ProFormDependency,
  ProFormField,
} from '@ant-design/pro-components';
import { Button, Popconfirm, message, Upload, Image, Card, Form, Spin } from 'antd';
import { PlusOutlined, UploadOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { getCases, createCase, updateCase, deleteCase, uploadImage } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import type { Case } from '@/services/types';

// 单图上传组件
const SingleImageUpload = ({ 
  onChange, 
  defaultUrl,
  buttonText = "上传图片"
}: { 
  value?: number, 
  onChange?: (val: number) => void, 
  defaultUrl?: string,
  buttonText?: string
}) => {
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | undefined>(defaultUrl);

  useEffect(() => {
    if (defaultUrl) {
      setPreviewUrl(defaultUrl);
    }
  }, [defaultUrl]);

  const handleUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    setLoading(true);
    try {
      const res: any = await uploadImage(file);
      const url = res.url;
      const id = res.id;
      setPreviewUrl(url);
      onChange?.(id);
      onSuccess(res);
      message.success('上传成功');
    } catch (err) {
      onError(err);
      message.error('上传失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      {previewUrl && (
        <Image src={previewUrl} width={100} height={60} style={{ objectFit: 'cover', borderRadius: 4 }} />
      )}
      <Upload customRequest={handleUpload} showUploadList={false}>
        <Button icon={loading ? <Spin size="small" /> : <UploadOutlined />} disabled={loading}>
          {previewUrl ? '更换图片' : buttonText}
        </Button>
      </Upload>
    </div>
  );
};

export default function Cases() {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState<number | null>(null);

  const handleEdit = (record: Case) => {
    setEditingId(record.id);
    setModalVisible(true);
    // 填充表单
    form.setFieldsValue({
      ...record,
      // 确保 cover_image_id 也有值，虽然我们有 cover_image (id) 字段
      // 但我们需要传递 cover_image_url 给 Upload 组件
      // 这里通过 Form initialValues 或者 setFieldsValue 处理
      // 由于 SingleImageUpload 使用 defaultUrl prop，我们需要在组件里处理
    });
  };

  const handleAdd = () => {
    setEditingId(null);
    setModalVisible(true);
    form.resetFields();
    form.setFieldsValue({
      order: 0,
      is_active: true,
      detail_blocks: [{ block_type: 'text', text: '' }] // 默认给一个文本块
    });
  };

  const handleSubmit = async (values: any) => {
    try {
      // 自动设置排序
      if (values.detail_blocks && Array.isArray(values.detail_blocks)) {
        values.detail_blocks = values.detail_blocks.map((block: any, index: number) => ({
          ...block,
          order: index
        }));
      }

      if (editingId) {
        await updateCase(editingId, values);
        message.success('更新成功');
      } else {
        await createCase(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error) {
      message.error('操作失败');
      return false;
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteCase(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const columns: ProColumns<Case>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 50,
      hideInSearch: true,
    },
    {
      title: '封面图',
      dataIndex: 'cover_image_url',
      hideInSearch: true,
      width: 100,
      render: (_, record) => (
        <Image
          src={record.cover_image_url}
          width={80}
          height={50}
          style={{ objectFit: 'cover' }}
        />
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
    },
    {
      title: '排序',
      dataIndex: 'order',
      hideInSearch: true,
      width: 80,
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
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      width: 160,
      hideInSearch: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_, record) => [
        <a key="edit" onClick={() => handleEdit(record)}>
          编辑
        </a>,
        <Popconfirm
          key="delete"
          title="确定删除?"
          onConfirm={() => handleDelete(record.id)}
        >
          <a style={{ color: 'red' }}>删除</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <>
      <ProTable<Case>
        headerTitle="案例管理"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            const res: any = await getCases(params);
            return {
              data: res.results,
              success: true,
              total: res.count,
            };
          } catch (error) {
            return { data: [], success: false };
          }
        }}
        rowKey="id"
        toolBarRender={() => [
          <Button key="add" type="primary" onClick={handleAdd}>
            <PlusOutlined /> 新建案例
          </Button>,
        ]}
      />

      <ModalForm
        title={editingId ? '编辑案例' : '新建案例'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        form={form}
        onFinish={handleSubmit}
        width={800}
      >
        <ProFormText
          name="title"
          label="标题"
          placeholder="请输入案例标题"
          rules={[{ required: true, message: '请输入标题' }]}
        />
        
        {/* 封面图上传 */}
        <ProFormDependency name={['cover_image_url']}>
          {({ cover_image_url }) => (
            <Form.Item name="cover_image_id" label="展示图" rules={[{ required: true, message: '请上传展示图' }]}>
               <SingleImageUpload defaultUrl={cover_image_url} buttonText="上传展示图" />
            </Form.Item>
          )}
        </ProFormDependency>
        
        <ProFormDigit
          name="order"
          label="排序"
          placeholder="数字越大越靠前"
          min={0}
        />
        
        <ProFormSwitch
          name="is_active"
          label="是否启用"
        />

        {/* 详情块编辑 */}
        <ProFormList
          name="detail_blocks"
          label="详情内容（图文混排）"
          creatorButtonProps={{
            creatorButtonText: '添加内容块',
          }}
          itemRender={(dom, listMeta) => (
            <Card 
              size="small"
              extra={dom.action}
              title={`内容块 ${listMeta.index + 1}`}
              style={{ marginBottom: 16 }}
            >
              {dom.listDom}
            </Card>
          )}
          actionRender={(field, action, defaultActionDom) => {
            return [
              <Button
                key="up"
                type="text"
                icon={<ArrowUpOutlined />}
                onClick={() => action.move(field.name, field.name - 1)}
                disabled={field.name === 0}
              />,
              <Button
                key="down"
                type="text"
                icon={<ArrowDownOutlined />}
                onClick={() => action.move(field.name, field.name + 1)}
                disabled={field.name === form.getFieldValue('detail_blocks')?.length - 1}
              />,
              ...defaultActionDom,
            ];
          }}
        >
          <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
            <ProFormSelect
              name="block_type"
              label="类型"
              options={[
                { value: 'text', label: '文本' },
                { value: 'image', label: '图片' },
              ]}
              initialValue="text"
              width="xs"
            />
            <div style={{ flex: 1 }}>
              <ProFormDependency name={['block_type', 'image_url']}>
                {({ block_type, image_url }) => {
                  if (block_type === 'image') {
                    return (
                      <ProFormField 
                        name="image_id" 
                        label="图片" 
                        rules={[{ required: true, message: '请上传图片' }]}
                      >
                         <SingleImageUpload defaultUrl={image_url} />
                      </ProFormField>
                    );
                  }
                  return (
                    <ProFormTextArea
                      name="text"
                      label="文本内容"
                      placeholder="请输入文本"
                      fieldProps={{ autoSize: { minRows: 2 } }}
                    />
                  );
                }}
              </ProFormDependency>
            </div>
          </div>
        </ProFormList>
      </ModalForm>
    </>
  );
}
