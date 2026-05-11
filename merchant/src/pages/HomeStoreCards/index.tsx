import { useRef, useState } from 'react';
import { ProTable, ModalForm, ProFormDigit, ProFormSelect, ProFormSwitch, ProFormText } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Form, Popconfirm, Space, Tag, message } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import {
  createHomeStoreCard,
  deleteHomeStoreCard,
  getCategories,
  getHomeStoreCards,
  getProducts,
  getStores,
  updateHomeStoreCard,
} from '@/services/api';
import type { Category, HomeStoreCard, Product, Store } from '@/services/types';
import { fetchAllPaginated } from '@/utils/request';

export default function HomeStoreCards() {
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<HomeStoreCard | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<number | undefined>();

  const openCreate = () => {
    setEditingRecord(null);
    setSelectedStoreId(undefined);
    form.resetFields();
    form.setFieldsValue({ is_active: true, order: 0 });
    setModalVisible(true);
  };

  const openEdit = (record: HomeStoreCard) => {
    setEditingRecord(record);
    setSelectedStoreId(record.store);
    form.setFieldsValue({
      store_id: record.store,
      title: record.title,
      subtitle: record.subtitle,
      order: record.order,
      is_active: record.is_active,
      main_product_id: record.main_product?.id,
      secondary_product_ids: record.secondary_products?.map(item => item.id) || [],
      category_ids: record.categories?.map(item => item.id) || [],
    });
    setModalVisible(true);
  };

  const columns: ProColumns<HomeStoreCard>[] = [
    { title: '排序', dataIndex: 'order', width: 80, hideInSearch: true },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 90,
      valueType: 'select',
      valueEnum: {
        true: { text: '启用', status: 'Success' },
        false: { text: '停用', status: 'Default' },
      },
      render: (_, record) => <Tag color={record.is_active ? 'green' : 'default'}>{record.is_active ? '启用' : '停用'}</Tag>,
    },
    { title: '店铺', dataIndex: 'store_name', width: 140, hideInSearch: true },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '副标题', dataIndex: 'subtitle', ellipsis: true, hideInSearch: true },
    { title: '主推商品', dataIndex: ['main_product', 'name'], hideInSearch: true, ellipsis: true },
    {
      title: '副推',
      hideInSearch: true,
      width: 80,
      render: (_, record) => record.secondary_products?.length || 0,
    },
    {
      title: '分类',
      hideInSearch: true,
      width: 80,
      render: (_, record) => record.categories?.length || 0,
    },
    {
      title: '商品状态',
      hideInSearch: true,
      width: 130,
      render: (_, record) =>
        record.has_inactive_products ? (
          <Tag color="red">存在下架商品</Tag>
        ) : (
          <Tag color="green">正常</Tag>
        ),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => [
        <Button key="edit" type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定删除这张首页卡片？"
          onConfirm={async () => {
            await deleteHomeStoreCard(record.id);
            message.success('删除成功');
            actionRef.current?.reload();
          }}
        >
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <>
      <ProTable<HomeStoreCard>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const res: any = await getHomeStoreCards({ page: params.current, page_size: params.pageSize, title: params.title, is_active: params.is_active });
          const data = res.results || res;
          return { data, success: true, total: res.count || res.total || data.length };
        }}
        toolBarRender={() => [
          <Button key="create" type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建首页卡片
          </Button>,
        ]}
      />

      <ModalForm
        title={editingRecord ? '编辑首页卡片' : '新建首页卡片'}
        open={modalVisible}
        form={form}
        modalProps={{ destroyOnClose: true, onCancel: () => setModalVisible(false) }}
        onFinish={async (values) => {
          const payload = {
            ...values,
            store_id: Number(values.store_id),
            main_product_id: Number(values.main_product_id),
            secondary_product_ids: values.secondary_product_ids || [],
            category_ids: values.category_ids || [],
          };
          if (editingRecord) {
            await updateHomeStoreCard(editingRecord.id, payload);
          } else {
            await createHomeStoreCard(payload);
          }
          message.success('保存成功');
          setModalVisible(false);
          actionRef.current?.reload();
          return true;
        }}
      >
        {editingRecord?.has_inactive_products && (
          <Tag color="red">存在下架商品：{editingRecord.inactive_product_names?.join('、')}</Tag>
        )}
        <ProFormSelect
          name="store_id"
          label="店铺"
          rules={[{ required: true, message: '请选择店铺' }]}
          fieldProps={{
            showSearch: true,
            onChange: (value) => {
              setSelectedStoreId(Number(value));
              form.setFieldsValue({ main_product_id: undefined, secondary_product_ids: [], category_ids: [] });
            },
          }}
          request={async () => {
            const stores = await fetchAllPaginated<Store>(getStores, {}, 100);
            return stores.map(store => ({ label: store.name, value: store.id }));
          }}
        />
        <Space style={{ width: '100%' }} direction="vertical">
          <ProFormText name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]} />
          <ProFormText name="subtitle" label="副标题" />
        </Space>
        <ProFormSelect
          name="main_product_id"
          label="主推商品"
          rules={[{ required: true, message: '请选择主推商品' }]}
          request={async () => {
            if (!selectedStoreId) return [];
            const products = await fetchAllPaginated<Product>(getProducts, { store: selectedStoreId }, 100);
            return products.map(product => ({ label: product.name, value: product.id }));
          }}
        />
        <ProFormSelect
          name="secondary_product_ids"
          label="副推商品"
          mode="multiple"
          rules={[{ required: true, message: '请选择 4 个副推商品' }]}
          request={async () => {
            if (!selectedStoreId) return [];
            const products = await fetchAllPaginated<Product>(getProducts, { store: selectedStoreId }, 100);
            return products.map(product => ({ label: product.name, value: product.id }));
          }}
        />
        <ProFormSelect
          name="category_ids"
          label="一级分类"
          mode="multiple"
          rules={[{ required: true, message: '请选择至少 3 个一级分类' }]}
          request={async () => {
            if (!selectedStoreId) return [];
            const categories = await fetchAllPaginated<Category>(getCategories, { store: selectedStoreId, level: 'major' }, 100);
            return categories.map(category => ({ label: category.name, value: category.id }));
          }}
        />
        <ProFormDigit name="order" label="排序" min={0} />
        <ProFormSwitch name="is_active" label="启用" />
      </ModalForm>
    </>
  );
}
