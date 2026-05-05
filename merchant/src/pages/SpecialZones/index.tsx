import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ModalForm,
  ProFormDateTimePicker,
  ProFormDigit,
  ProFormSelect,
  ProFormSwitch,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Drawer, Form, Image, InputNumber, Popconfirm, Select, Space, Switch, Table, Tag, Upload, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined } from '@ant-design/icons';
import {
  bindSpecialZoneProduct,
  createSpecialZone,
  deleteSpecialZone,
  getCurrentStoreContext,
  getProducts,
  getSpecialZoneProducts,
  getSpecialZones,
  removeSpecialZoneProduct,
  updateSpecialZone,
  updateSpecialZoneProduct,
  uploadImage,
} from '@/services/api';
import type { CurrentStoreContext, Product, SpecialZone, SpecialZoneProduct } from '@/services/types';
import { getSelectedStoreId } from '@/utils/store';

const kindOptions = {
  activity: { text: '活动专区', status: 'Processing' },
  promotion: { text: '优惠专区', status: 'Success' },
  category: { text: '品类专区', status: 'Default' },
  brand: { text: '品牌专区', status: 'Warning' },
  custom: { text: '自定义专区', status: 'Default' },
};

const toDateTimeValue = (value: unknown) => {
  if (!value) return null;
  if (typeof value === 'string') return value;
  if (typeof value === 'object' && 'toISOString' in value && typeof value.toISOString === 'function') {
    return value.toISOString();
  }
  return value;
};

const getList = <T,>(res: any): T[] => {
  if (Array.isArray(res)) return res;
  return res?.results || [];
};

export default function SpecialZones() {
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [bindingForm] = Form.useForm();
  const [storeContext, setStoreContext] = useState<CurrentStoreContext | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<SpecialZone | null>(null);
  const [coverUrl, setCoverUrl] = useState<string>('');
  const [bindingZone, setBindingZone] = useState<SpecialZone | null>(null);
  const [bindings, setBindings] = useState<SpecialZoneProduct[]>([]);
  const [bindingLoading, setBindingLoading] = useState(false);
  const [productOptions, setProductOptions] = useState<{ label: string; value: number }[]>([]);
  const [productSearchLoading, setProductSearchLoading] = useState(false);

  const isPlatformAdmin = Boolean(storeContext?.is_platform_admin);
  const storeOptions = useMemo(
    () => storeContext?.stores.map(store => ({ label: store.name, value: store.id })) || [],
    [storeContext],
  );
  const storeNameById = useMemo(() => {
    const map = new Map<number, string>();
    storeContext?.stores.forEach(store => map.set(store.id, store.name));
    return map;
  }, [storeContext]);

  useEffect(() => {
    getCurrentStoreContext()
      .then(setStoreContext)
      .catch(() => setStoreContext(null));
  }, []);

  const getDefaultStoreId = () => getSelectedStoreId() || storeContext?.default_store?.id || storeContext?.stores[0]?.id;

  const handleUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    try {
      const res: any = await uploadImage(file);
      setCoverUrl(res.url);
      form.setFieldValue('cover_image', res.url);
      onSuccess(res);
      message.success('封面上传成功');
    } catch (error) {
      onError(error);
      message.error('封面上传失败');
    }
  };

  const handleAdd = () => {
    setEditingRecord(null);
    setCoverUrl('');
    form.resetFields();
    form.setFieldsValue({
      store_id: getDefaultStoreId(),
      kind: 'activity',
      is_active: true,
      show_on_home: true,
      home_order: 0,
      cover_image: '',
    });
    setModalVisible(true);
  };

  const handleEdit = (record: SpecialZone) => {
    setEditingRecord(record);
    setCoverUrl(record.cover_image || '');
    form.resetFields();
    form.setFieldsValue({
      store_id: record.store,
      title: record.title,
      slug: record.slug,
      kind: record.kind,
      subtitle: record.subtitle,
      cover_image: record.cover_image,
      home_order: record.home_order,
      show_on_home: record.show_on_home,
      is_active: record.is_active,
      start_at: record.start_at,
      end_at: record.end_at,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteSpecialZone(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const loadBindings = async (zone: SpecialZone) => {
    setBindingLoading(true);
    try {
      const res: any = await getSpecialZoneProducts(zone.id, { include_inactive: true, store: zone.store });
      setBindings(getList<SpecialZoneProduct>(res));
    } catch (error) {
      message.error('加载专区商品失败');
    } finally {
      setBindingLoading(false);
    }
  };

  const searchProducts = async (keyword?: string, zone?: SpecialZone | null) => {
    const targetZone = zone || bindingZone;
    if (!targetZone) return;
    setProductSearchLoading(true);
    try {
      const res: any = await getProducts({
        search: keyword,
        page: 1,
        page_size: 20,
        is_active: true,
        store: targetZone.store,
      });
      const products = getList<Product>(res);
      setProductOptions(products.map(product => ({ label: product.name, value: product.id })));
    } catch (error) {
      setProductOptions([]);
    } finally {
      setProductSearchLoading(false);
    }
  };

  const openBindings = (zone: SpecialZone) => {
    setBindingZone(zone);
    bindingForm.resetFields();
    bindingForm.setFieldsValue({ order: 0, is_active: true });
    searchProducts(undefined, zone);
    loadBindings(zone);
  };

  const handleBindProduct = async (values: { product_id: number; order?: number; is_active?: boolean }) => {
    if (!bindingZone) return false;
    try {
      await bindSpecialZoneProduct(bindingZone.id, {
        product_id: values.product_id,
        order: values.order || 0,
        is_active: values.is_active ?? true,
      });
      message.success('商品已绑定');
      bindingForm.resetFields();
      await loadBindings(bindingZone);
      return true;
    } catch (error) {
      message.error('绑定失败');
      return false;
    }
  };

  const handleUpdateBinding = async (record: SpecialZoneProduct, data: Partial<Pick<SpecialZoneProduct, 'order' | 'is_active'>>) => {
    if (!bindingZone) return;
    try {
      await updateSpecialZoneProduct(bindingZone.id, record.product_id, {
        order: data.order ?? record.order,
        is_active: data.is_active ?? record.is_active,
      });
      await loadBindings(bindingZone);
    } catch (error) {
      message.error('更新绑定失败');
    }
  };

  const handleRemoveBinding = async (record: SpecialZoneProduct) => {
    if (!bindingZone) return;
    try {
      await removeSpecialZoneProduct(bindingZone.id, record.product_id);
      message.success('已移除');
      await loadBindings(bindingZone);
    } catch (error) {
      message.error('移除失败');
    }
  };

  const columns: ProColumns<SpecialZone>[] = [
    { title: 'ID', dataIndex: 'id', width: 64, hideInSearch: true },
    {
      title: '店铺',
      dataIndex: 'store',
      width: 120,
      hideInSearch: !isPlatformAdmin,
      hideInTable: !isPlatformAdmin,
      valueType: 'select',
      fieldProps: { options: storeOptions },
      render: (_, record) => storeNameById.get(record.store) || `店铺 #${record.store}`,
    },
    {
      title: '封面',
      dataIndex: 'cover_image',
      width: 120,
      hideInSearch: true,
      render: (_, record) => record.cover_image ? <Image src={record.cover_image} width={96} height={54} style={{ objectFit: 'cover' }} /> : '-',
    },
    { title: '标题', dataIndex: 'title', width: 160 },
    {
      title: '类型',
      dataIndex: 'kind',
      width: 110,
      valueType: 'select',
      valueEnum: kindOptions,
    },
    { title: '标识', dataIndex: 'slug', width: 140, hideInSearch: true },
    { title: '首页排序', dataIndex: 'home_order', width: 90, hideInSearch: true, sorter: true },
    {
      title: '首页显示',
      dataIndex: 'show_on_home',
      width: 100,
      hideInSearch: true,
      render: (_, record) => <Tag color={record.show_on_home ? 'blue' : 'default'}>{record.show_on_home ? '显示' : '隐藏'}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 90,
      valueType: 'select',
      valueEnum: {
        true: { text: '启用', status: 'Success' },
        false: { text: '禁用', status: 'Error' },
      },
      render: (_, record) => <Tag color={record.is_active ? 'green' : 'red'}>{record.is_active ? '启用' : '禁用'}</Tag>,
    },
    { title: '开始时间', dataIndex: 'start_at', valueType: 'dateTime', width: 160, hideInSearch: true },
    { title: '结束时间', dataIndex: 'end_at', valueType: 'dateTime', width: 160, hideInSearch: true },
    {
      title: '操作',
      valueType: 'option',
      width: 190,
      fixed: 'right',
      render: (_, record) => [
        <a key="products" onClick={() => openBindings(record)}>商品</a>,
        <a key="edit" onClick={() => handleEdit(record)}>编辑</a>,
        <Popconfirm key="delete" title="确定删除该专区?" onConfirm={() => handleDelete(record.id)}>
          <a style={{ color: 'red' }}>删除</a>
        </Popconfirm>,
      ],
    },
  ];

  const bindingColumns: ColumnsType<SpecialZoneProduct> = [
    {
      title: '商品',
      dataIndex: ['product', 'name'],
      render: (_, record) => record.product?.name || `商品 #${record.product_id}`,
    },
    {
      title: '排序',
      dataIndex: 'order',
      width: 110,
      render: (_, record) => (
        <InputNumber
          min={0}
          precision={0}
          value={record.order}
          onChange={(value) => handleUpdateBinding(record, { order: Number(value || 0) })}
        />
      ),
    },
    {
      title: '展示',
      dataIndex: 'is_active',
      width: 90,
      render: (_, record) => (
        <Switch
          checked={record.is_active}
          onChange={(checked) => handleUpdateBinding(record, { is_active: checked })}
        />
      ),
    },
    {
      title: '操作',
      width: 90,
      render: (_, record) => (
        <Popconfirm title="确定移除该商品?" onConfirm={() => handleRemoveBinding(record)}>
          <a style={{ color: 'red' }}>移除</a>
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      <ProTable<SpecialZone>
        headerTitle="动态运营专区"
        actionRef={actionRef}
        columns={columns}
        rowKey="id"
        scroll={{ x: 'max-content' }}
        request={async (params) => {
          try {
            const { current, pageSize, ...rest } = params;
            const queryParams: any = {
              page: current,
              page_size: pageSize,
              ...rest,
            };
            if (!isPlatformAdmin) {
              delete queryParams.store;
            }
            const res: any = await getSpecialZones(queryParams);
            const data = getList<SpecialZone>(res);
            return {
              data,
              success: true,
              total: res?.count || res?.total || data.length,
            };
          } catch (error) {
            message.error('加载专区失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        search={{ labelWidth: 'auto', defaultCollapsed: false, collapseRender: false }}
        pagination={{ defaultPageSize: 10 }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新建专区
          </Button>,
        ]}
      />

      <ModalForm
        title={editingRecord ? '编辑动态专区' : '新建动态专区'}
        open={modalVisible}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) {
            setEditingRecord(null);
            setCoverUrl('');
            form.resetFields();
          }
        }}
        form={form}
        grid
        width={820}
        modalProps={{ destroyOnClose: true }}
        onFinish={async (values) => {
          try {
            const payload = {
              ...values,
              start_at: toDateTimeValue(values.start_at),
              end_at: toDateTimeValue(values.end_at),
            };
            if (!isPlatformAdmin) {
              delete payload.store_id;
            }
            if (editingRecord) {
              await updateSpecialZone(editingRecord.id, payload);
              message.success('更新成功');
            } else {
              await createSpecialZone(payload);
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
        {isPlatformAdmin && (
          <ProFormSelect
            name="store_id"
            label="所属店铺"
            options={storeOptions}
            rules={[{ required: true, message: '请选择店铺' }]}
            colProps={{ span: 12 }}
          />
        )}
        <ProFormText
          name="title"
          label="专区标题"
          rules={[{ required: true, message: '请输入专区标题' }]}
          colProps={{ span: 12 }}
        />
        <ProFormText
          name="slug"
          label="专区标识"
          rules={[{ required: true, message: '请输入专区标识' }]}
          colProps={{ span: 12 }}
        />
        <ProFormSelect
          name="kind"
          label="专区类型"
          valueEnum={{
            activity: '活动专区',
            promotion: '优惠专区',
            category: '品类专区',
            brand: '品牌专区',
            custom: '自定义专区',
          }}
          rules={[{ required: true, message: '请选择专区类型' }]}
          colProps={{ span: 12 }}
        />
        <ProFormText name="subtitle" label="副标题" colProps={{ span: 24 }} />
        <ProFormDigit name="home_order" label="首页排序" min={0} fieldProps={{ precision: 0 }} colProps={{ span: 8 }} />
        <ProFormSwitch name="show_on_home" label="首页显示" colProps={{ span: 8 }} />
        <ProFormSwitch name="is_active" label="是否启用" colProps={{ span: 8 }} />
        <ProFormDateTimePicker name="start_at" label="开始时间" colProps={{ span: 12 }} />
        <ProFormDateTimePicker name="end_at" label="结束时间" colProps={{ span: 12 }} />
        <ProFormText name="cover_image" hidden />
        <Form.Item label="专区封面" style={{ width: '100%' }}>
          <Upload listType="picture-card" showUploadList={false} customRequest={handleUpload} accept="image/*">
            {coverUrl ? (
              <img src={coverUrl} alt="cover" style={{ width: '100%' }} />
            ) : (
              <div>
                <PlusOutlined />
                <div style={{ marginTop: 8 }}>上传</div>
              </div>
            )}
          </Upload>
        </Form.Item>
      </ModalForm>

      <Drawer
        title={bindingZone ? `${bindingZone.title} - 商品绑定` : '商品绑定'}
        open={Boolean(bindingZone)}
        onClose={() => {
          setBindingZone(null);
          setBindings([]);
          bindingForm.resetFields();
        }}
        width={760}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Form form={bindingForm} layout="inline" onFinish={handleBindProduct}>
            <Form.Item name="product_id" rules={[{ required: true, message: '请选择商品' }]} style={{ minWidth: 320 }}>
              <Select
                showSearch
                filterOption={false}
                placeholder="搜索商品名称"
                loading={productSearchLoading}
                options={productOptions}
                onSearch={(keyword) => searchProducts(keyword)}
                onFocus={() => searchProducts(undefined)}
              />
            </Form.Item>
            <Form.Item name="order">
              <InputNumber min={0} precision={0} placeholder="排序" />
            </Form.Item>
            <Form.Item name="is_active" valuePropName="checked">
              <Switch checkedChildren="展示" unCheckedChildren="隐藏" />
            </Form.Item>
            <Button type="primary" htmlType="submit">添加商品</Button>
          </Form>
          <Table<SpecialZoneProduct>
            rowKey="id"
            loading={bindingLoading}
            columns={bindingColumns}
            dataSource={bindings}
            pagination={false}
          />
        </Space>
      </Drawer>
    </>
  );
}
