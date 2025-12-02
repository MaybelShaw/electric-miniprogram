import { useState, useRef } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Button, Popconfirm, message, Upload, Image, Form } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getHomeBanners, createHomeBanner, updateHomeBanner, deleteHomeBanner, uploadImage } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import type { HomeBanner } from '@/services/types';

export default function HomeBanners() {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<HomeBanner | null>(null);
  const [imageUrl, setImageUrl] = useState<string>();
  const [imageId, setImageId] = useState<number>();
  const [form] = Form.useForm();

  const handleUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    try {
      const res: any = await uploadImage(file);
      const url = res.url;
      const id = res.id;
      setImageUrl(url);
      setImageId(id);
      onSuccess(res);
      message.success('图片上传成功');
    } catch (err) {
      onError(err);
      message.error('图片上传失败');
    }
  };

  const handleEdit = (record: HomeBanner) => {
    setEditingRecord(record);
    setImageUrl(record.image_url);
    setImageId(record.image_id);
    setModalVisible(true);
    form.setFieldsValue({
      title: record.title,
      link_url: record.link_url,
      order: record.order,
      is_active: record.is_active,
    });
  };

  const handleAdd = () => {
    setEditingRecord(null);
    setImageUrl(undefined);
    setImageId(undefined);
    setModalVisible(true);
    form.resetFields();
    form.setFieldsValue({
      order: 0,
      is_active: true,
    });
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteHomeBanner(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const columns: ProColumns<HomeBanner>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 50,
      hideInSearch: true,
    },
    {
      title: '图片',
      dataIndex: 'image_url',
      hideInSearch: true,
      width: 150,
      render: (_, record) => (
        <Image
          src={record.image_url}
          width={120}
          height={60}
          style={{ objectFit: 'cover' }}
        />
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
    },
    {
      title: '跳转链接',
      dataIndex: 'link_url',
      hideInSearch: true,
      ellipsis: true,
    },
    {
      title: '排序',
      dataIndex: 'order',
      hideInSearch: true,
      width: 80,
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
      <ProTable<HomeBanner>
        headerTitle="轮播图列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            const res: any = await getHomeBanners(params);
            const data = Array.isArray(res) ? res : (res.results || []);
            return {
              data: data,
              success: true,
              total: res.count || data.length,
            };
          } catch (error) {
            message.error('加载失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        rowKey="id"
        pagination={{
          defaultPageSize: 10,
        }}
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新建轮播图
          </Button>,
        ]}
      />
      <ModalForm
        title={editingRecord ? '编辑轮播图' : '新建轮播图'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        form={form}
        modalProps={{
          destroyOnClose: true,
        }}
        onFinish={async (values) => {
          if (!imageId && !editingRecord) {
            message.error('请上传图片');
            return false;
          }

          try {
            const data = {
              ...values,
              image: imageId || editingRecord?.image_id,
            };

            if (editingRecord) {
              await updateHomeBanner(editingRecord.id, data);
              message.success('更新成功');
            } else {
              await createHomeBanner(data);
              message.success('创建成功');
            }
            actionRef.current?.reload();
            return true;
          } catch (error) {
            message.error('操作失败');
            return false;
          }
        }}
      >
        <Form.Item label="轮播图片" required>
          <Upload
            listType="picture-card"
            showUploadList={false}
            customRequest={handleUpload}
            accept="image/*"
          >
            {imageUrl ? (
              <img src={imageUrl} alt="banner" style={{ width: '100%' }} />
            ) : (
              <div>
                <PlusOutlined />
                <div style={{ marginTop: 8 }}>上传</div>
              </div>
            )}
          </Upload>
        </Form.Item>

        <ProFormText
          name="title"
          label="标题"
          placeholder="请输入标题"
        />

        <ProFormText
          name="link_url"
          label="跳转链接"
          placeholder="请输入跳转链接"
        />

        <ProFormDigit
          name="order"
          label="排序"
          tooltip="数值越小越靠前"
          min={0}
          fieldProps={{ precision: 0 }}
        />

        <ProFormSwitch
          name="is_active"
          label="是否启用"
        />
      </ModalForm>
    </>
  );
}
