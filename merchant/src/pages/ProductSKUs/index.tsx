import { useRef, useState } from 'react';
import { ProTable, ModalForm, ProFormDigit, ProFormSelect, ProFormSwitch, ProFormText } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Popconfirm, Space, Tag, message } from 'antd';
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { createProductSku, deleteProductSku, getProductSkus, getProducts, updateProductSku } from '@/services/api';
import type { Product, ProductSKU } from '@/services/types';
import { fetchAllPaginated } from '@/utils/request';

type SpecItem = {
  key?: string;
  value?: string;
};

function specsToItems(specs?: ProductSKU['specs']): SpecItem[] {
  if (!specs || typeof specs !== 'object') return [];
  return Object.entries(specs).map(([key, value]) => ({ key, value: String(value ?? '') }));
}

function itemsToSpecs(items?: SpecItem[]): Record<string, string> {
  const specs: Record<string, string> = {};
  (items || []).forEach((item) => {
    const key = item.key?.trim();
    if (!key) return;
    specs[key] = item.value?.trim() || '';
  });
  return specs;
}

export default function ProductSKUs() {
  const actionRef = useRef<ActionType>();
  const initialProductId = Number(new URLSearchParams(window.location.search).get('product')) || undefined;
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ProductSKU | null>(null);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ stock: 0, is_active: true, spec_items: [] });
    setModalVisible(true);
  };

  const openEdit = (record: ProductSKU) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      product_id: record.product,
      spec_items: specsToItems(record.specs),
    });
    setModalVisible(true);
  };

  const columns: ProColumns<ProductSKU>[] = [
    { title: 'ID', dataIndex: 'id', width: 70, hideInSearch: true },
    { title: '商品', dataIndex: 'product_name', hideInSearch: true },
    {
      title: '商品',
      dataIndex: 'product',
      hideInTable: true,
      valueType: 'select',
      request: async () => {
        const products = await fetchAllPaginated<Product>(getProducts, { is_active: true }, 100);
        return products.map(product => ({ label: `${product.name} (#${product.id})`, value: product.id }));
      },
    },
    { title: 'SKU名称', dataIndex: 'name' },
    { title: 'SKU编码', dataIndex: 'sku_code' },
    {
      title: '规格',
      dataIndex: 'specs',
      hideInSearch: true,
      render: (_, record) => (
        <Space wrap>
          {Object.entries(record.specs || {}).map(([key, value]) => (
            <Tag key={key}>{key}: {String(value)}</Tag>
          ))}
        </Space>
      ),
    },
    { title: '售价', dataIndex: 'price', valueType: 'money', hideInSearch: true, width: 110 },
    { title: '库存', dataIndex: 'stock', hideInSearch: true, width: 90 },
    {
      title: '状态',
      dataIndex: 'is_active',
      valueType: 'select',
      valueEnum: {
        true: { text: '启用', status: 'Success' },
        false: { text: '停用', status: 'Default' },
      },
      width: 100,
    },
    { title: '更新时间', dataIndex: 'updated_at', valueType: 'dateTime', hideInSearch: true, width: 170 },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => [
        <a key="edit" onClick={() => openEdit(record)}>编辑</a>,
        <Popconfirm key="delete" title="确定删除该 SKU?" onConfirm={async () => {
          await deleteProductSku(record.id);
          message.success('删除成功');
          actionRef.current?.reload();
        }}>
          <a style={{ color: 'red' }}>删除</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <>
      <ProTable<ProductSKU>
        headerTitle="商品 SKU 管理"
        actionRef={actionRef}
        columns={columns}
        rowKey="id"
        params={initialProductId ? { product: initialProductId } : undefined}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const res: any = await getProductSkus({ page: current, page_size: pageSize, ...rest });
          const data = Array.isArray(res) ? res : res.results || [];
          return { data, success: true, total: res.count || data.length };
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增 SKU
          </Button>,
        ]}
      />

      <ModalForm
        title={editingRecord ? '编辑 SKU' : '新增 SKU'}
        open={modalVisible}
        form={form}
        width={720}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={setModalVisible}
        onFinish={async (values) => {
          const { spec_items, ...rest } = values;
          const payload = { ...rest, specs: itemsToSpecs(spec_items) };
          if (editingRecord) {
            await updateProductSku(editingRecord.id, payload);
            message.success('更新成功');
          } else {
            await createProductSku(payload);
            message.success('创建成功');
          }
          setModalVisible(false);
          actionRef.current?.reload();
          return true;
        }}
      >
        <ProFormSelect
          name="product_id"
          label="商品"
          disabled={Boolean(editingRecord)}
          rules={[{ required: true, message: '请选择商品' }]}
          showSearch
          request={async () => {
            const products = await fetchAllPaginated<Product>(getProducts, { is_active: true }, 100);
            return products.map(product => ({ label: `${product.name} (#${product.id})`, value: product.id }));
          }}
        />
        <ProFormText name="name" label="SKU名称" rules={[{ required: true, message: '请输入SKU名称' }]} />
        <ProFormText name="sku_code" label="SKU编码" rules={[{ required: true, message: '请输入SKU编码' }]} />
        <Form.Item label="规格参数">
          <Form.List name="spec_items">
            {(fields, { add, remove }) => (
              <Space direction="vertical" style={{ width: '100%' }}>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} align="baseline">
                    <Form.Item {...restField} name={[name, 'key']} rules={[{ required: true, message: '请输入规格名' }]}>
                      <Input placeholder="规格名，如容量" style={{ width: 180 }} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'value']} rules={[{ required: true, message: '请输入规格值' }]}>
                      <Input placeholder="规格值，如 520L" style={{ width: 260 }} />
                    </Form.Item>
                    <MinusCircleOutlined onClick={() => remove(name)} />
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />}>
                  添加规格
                </Button>
              </Space>
            )}
          </Form.List>
        </Form.Item>
        <ProFormDigit name="price" label="售价" rules={[{ required: true, message: '请输入售价' }]} fieldProps={{ min: 0, precision: 2 }} />
        <ProFormDigit name="stock" label="库存" rules={[{ required: true, message: '请输入库存' }]} fieldProps={{ min: 0, precision: 0 }} />
        <ProFormText name="image" label="SKU主图" />
        <ProFormSwitch name="is_active" label="启用" />
      </ModalForm>
    </>
  );
}
