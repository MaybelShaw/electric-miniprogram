import { useState, useRef } from 'react';
import { ProTable, ModalForm, ProFormSwitch, ProFormSelect } from '@ant-design/pro-components';
import { Button, Popconfirm, message, Upload, Image, Form } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getSpecialZoneCovers, createSpecialZoneCover, updateSpecialZoneCover, deleteSpecialZoneCover, uploadImage } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import type { SpecialZoneCover } from '@/services/types';

export default function SpecialZoneCovers() {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<SpecialZoneCover | null>(null);
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

  const handleEdit = (record: SpecialZoneCover) => {
    setEditingRecord(record);
    setImageUrl(record.image_url);
    setImageId(record.image_id);
    setModalVisible(true);
    form.setFieldsValue({
      type: record.type,
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
      is_active: true,
      type: 'gift',
    });
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteSpecialZoneCover(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const columns: ProColumns<SpecialZoneCover>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 60,
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
      title: '专区类型',
      dataIndex: 'type',
      valueType: 'select',
      valueEnum: {
        gift: { text: '礼品专区', status: 'Processing' },
        designer: { text: '设计师专区', status: 'Success' },
      },
      width: 120,
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
      <ProTable<SpecialZoneCover>
        headerTitle="首页专区图片"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            const { current, pageSize, ...rest } = params;
            const queryParams: any = {
              page: current,
              page_size: pageSize,
              ...rest,
            };
            if (params.type) {
              queryParams.type = params.type;
            }
            const res: any = await getSpecialZoneCovers(queryParams);
            const data = Array.isArray(res) ? res : (res.results || []);
            return {
              data,
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
          defaultCollapsed: false,
          collapseRender: false,
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新建图片
          </Button>,
        ]}
      />
      <ModalForm
        title={editingRecord ? '编辑首页专区图片' : '新建首页专区图片'}
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
              await updateSpecialZoneCover(editingRecord.id, data);
              message.success('更新成功');
            } else {
              await createSpecialZoneCover(data);
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
        <Form.Item
          label="专区图片"
          required
          extra="建议比例约2:1，推荐尺寸670x320或1000x480，主体居中避免裁切"
        >
          <Upload
            listType="picture-card"
            showUploadList={false}
            customRequest={handleUpload}
            accept="image/*"
          >
            {imageUrl ? (
              <img src={imageUrl} alt="zone" style={{ width: '100%' }} />
            ) : (
              <div>
                <PlusOutlined />
                <div style={{ marginTop: 8 }}>上传</div>
              </div>
            )}
          </Upload>
        </Form.Item>

        <ProFormSelect
          name="type"
          label="专区类型"
          valueEnum={{
            gift: '礼品专区',
            designer: '设计师专区',
          }}
          rules={[{ required: true, message: '请选择专区类型' }]}
          initialValue="gift"
        />

        <ProFormSwitch
          name="is_active"
          label="是否启用"
        />
      </ModalForm>
    </>
  );
}
