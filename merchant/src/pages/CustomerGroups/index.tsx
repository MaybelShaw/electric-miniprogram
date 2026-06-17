import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ModalForm,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
  ProTable,
} from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Drawer, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch, Table, Tag, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined } from '@ant-design/icons';
import {
  createStoreCustomerGroup,
  createStoreCustomerGroupMember,
  createStoreCustomerGroupPrice,
  deleteStoreCustomerGroup,
  deleteStoreCustomerGroupMember,
  deleteStoreCustomerGroupPrice,
  getCurrentStoreContext,
  getProductSkus,
  getProducts,
  getStoreCustomerGroupMembers,
  getStoreCustomerGroupPrices,
  getStoreCustomerGroups,
  updateStore,
  updateStoreCustomerGroup,
  updateStoreCustomerGroupMember,
  updateStoreCustomerGroupPrice,
} from '@/services/api';
import type {
  CurrentStoreContext,
  Product,
  ProductSKU,
  StoreCustomerGroup,
  StoreCustomerGroupMember,
  StoreCustomerGroupPrice,
} from '@/services/types';
import { getSelectedStoreId } from '@/utils/store';

type Option = { label: string; value: number; title?: string };
type GroupFormValues = {
  store?: number;
  name: string;
  description?: string;
  status: 'active' | 'disabled';
};
type MemberFormValues = { phone: string };
type PriceFormValues = { product: number; sku?: number; price: number };

const statusValueEnum = {
  active: { text: '启用', status: 'Success' },
  disabled: { text: '停用', status: 'Default' },
};

const getList = <T,>(res: any): T[] => {
  if (Array.isArray(res)) return res;
  return res?.results || [];
};

const statusTag = (status: 'active' | 'disabled') => (
  <Tag color={status === 'active' ? 'green' : 'default'}>{status === 'active' ? '启用' : '停用'}</Tag>
);

const formatMoney = (value?: string | number | null) => {
  if (value === undefined || value === null || value === '') return '-';
  return `¥${value}`;
};

export default function CustomerGroups() {
  const actionRef = useRef<ActionType>();
  const [groupForm] = Form.useForm<GroupFormValues>();
  const [memberForm] = Form.useForm<MemberFormValues>();
  const [priceForm] = Form.useForm<PriceFormValues>();
  const [storeContext, setStoreContext] = useState<CurrentStoreContext | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<StoreCustomerGroup | null>(null);
  const [memberGroup, setMemberGroup] = useState<StoreCustomerGroup | null>(null);
  const [members, setMembers] = useState<StoreCustomerGroupMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [priceGroup, setPriceGroup] = useState<StoreCustomerGroup | null>(null);
  const [prices, setPrices] = useState<StoreCustomerGroupPrice[]>([]);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [editingPrice, setEditingPrice] = useState<StoreCustomerGroupPrice | null>(null);
  const [productOptions, setProductOptions] = useState<Option[]>([]);
  const [skuOptions, setSkuOptions] = useState<Option[]>([]);
  const [productSearchLoading, setProductSearchLoading] = useState(false);
  const [displaySwitchLoading, setDisplaySwitchLoading] = useState(false);
  const [batchPhones, setBatchPhones] = useState('');
  const [batchImporting, setBatchImporting] = useState(false);

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
  const currentStore = useMemo(() => {
    if (!storeContext) return null;
    const selectedStoreId = getSelectedStoreId();
    return storeContext.stores.find(store => store.id === selectedStoreId)
      || storeContext.default_store
      || storeContext.stores[0]
      || null;
  }, [storeContext]);

  const loadStoreContext = async () => {
    try {
      setStoreContext(await getCurrentStoreContext());
    } catch (error) {
      setStoreContext(null);
    }
  };

  useEffect(() => {
    loadStoreContext();
  }, []);

  const getDefaultStoreId = () => getSelectedStoreId() || currentStore?.id;

  const handleToggleGroupNameDisplay = async (checked: boolean) => {
    const storeId = getDefaultStoreId();
    if (!storeId) {
      message.warning('请先选择店铺');
      return;
    }
    setDisplaySwitchLoading(true);
    try {
      await updateStore(storeId, { show_customer_group_name: checked });
      message.success('展示开关已更新');
      await loadStoreContext();
    } catch (error) {
      message.error('更新展示开关失败');
    } finally {
      setDisplaySwitchLoading(false);
    }
  };

  const openCreateGroup = () => {
    setEditingGroup(null);
    groupForm.resetFields();
    groupForm.setFieldsValue({
      store: getDefaultStoreId(),
      status: 'active',
    });
    setModalVisible(true);
  };

  const openEditGroup = (record: StoreCustomerGroup) => {
    setEditingGroup(record);
    groupForm.resetFields();
    groupForm.setFieldsValue({
      store: record.store,
      name: record.name,
      description: record.description,
      status: record.status,
    });
    setModalVisible(true);
  };

  const loadMembers = async (group = memberGroup) => {
    if (!group) return;
    setMembersLoading(true);
    try {
      const res: any = await getStoreCustomerGroupMembers({ group: group.id, store: group.store, page: 1, page_size: 200 });
      setMembers(getList<StoreCustomerGroupMember>(res));
    } catch (error) {
      message.error('加载分组成员失败');
    } finally {
      setMembersLoading(false);
    }
  };

  const openMembers = (group: StoreCustomerGroup) => {
    setMemberGroup(group);
    memberForm.resetFields();
    setBatchPhones('');
    loadMembers(group);
  };

  const handleCreateMember = async (values: MemberFormValues) => {
    if (!memberGroup) return;
    try {
      await createStoreCustomerGroupMember({
        store: memberGroup.store,
        group: memberGroup.id,
        phone: values.phone,
        status: 'active',
      });
      message.success('成员已加入分组');
      memberForm.resetFields();
      await loadMembers(memberGroup);
    } catch (error) {
      message.error('添加成员失败');
    }
  };

  const parsePhones = (value: string) => {
    const phones = value
      .split(/[\s,，;；]+/)
      .map(item => item.trim())
      .filter(Boolean);
    return Array.from(new Set(phones));
  };

  const handleBatchCreateMembers = async () => {
    if (!memberGroup) return;
    const phones = parsePhones(batchPhones);
    if (phones.length === 0) {
      message.warning('请先粘贴手机号');
      return;
    }
    setBatchImporting(true);
    let successCount = 0;
    const failed: string[] = [];
    for (const phone of phones) {
      try {
        await createStoreCustomerGroupMember({
          store: memberGroup.store,
          group: memberGroup.id,
          phone,
          status: 'active',
        });
        successCount += 1;
      } catch (error) {
        failed.push(phone);
      }
    }
    setBatchImporting(false);
    if (successCount > 0) {
      message.success(`已加入 ${successCount} 个成员`);
      setBatchPhones(failed.join('\n'));
      await loadMembers(memberGroup);
      actionRef.current?.reload();
    }
    if (failed.length > 0) {
      message.warning(`有 ${failed.length} 个手机号未导入，请检查是否已在本店其他分组或格式不正确`);
    }
  };

  const handleUpdateMemberStatus = async (record: StoreCustomerGroupMember, status: 'active' | 'disabled') => {
    if (!memberGroup) return;
    try {
      await updateStoreCustomerGroupMember(record.id, { status });
      await loadMembers(memberGroup);
    } catch (error) {
      message.error('更新成员状态失败');
    }
  };

  const handleDeleteMember = async (record: StoreCustomerGroupMember) => {
    if (!memberGroup) return;
    try {
      await deleteStoreCustomerGroupMember(record.id);
      message.success('成员已移除');
      await loadMembers(memberGroup);
    } catch (error) {
      message.error('移除成员失败');
    }
  };

  const loadPrices = async (group = priceGroup) => {
    if (!group) return;
    setPricesLoading(true);
    try {
      const res: any = await getStoreCustomerGroupPrices({ group: group.id, store: group.store, page: 1, page_size: 200 });
      setPrices(getList<StoreCustomerGroupPrice>(res));
    } catch (error) {
      message.error('加载价格表失败');
    } finally {
      setPricesLoading(false);
    }
  };

  const searchProducts = async (keyword?: string, group = priceGroup) => {
    if (!group) return;
    setProductSearchLoading(true);
    try {
      const res: any = await getProducts({
        search: keyword,
        store: group.store,
        is_active: true,
        page: 1,
        page_size: 30,
      });
      const products = getList<Product>(res);
      setProductOptions(products.map(product => ({
        label: `${product.name} (#${product.id}) · 默认价 ${formatMoney(product.price)}`,
        title: `${product.name} (#${product.id})`,
        value: product.id,
      })));
    } catch (error) {
      setProductOptions([]);
    } finally {
      setProductSearchLoading(false);
    }
  };

  const loadSkus = async (productId?: number) => {
    if (!productId || !priceGroup) {
      setSkuOptions([]);
      return;
    }
    try {
      const res: any = await getProductSkus({ product: productId, store: priceGroup.store, is_active: true, page: 1, page_size: 100 });
      const skus = getList<ProductSKU>(res);
      setSkuOptions(skus.map(sku => ({
        label: `${sku.name || '默认规格'}${sku.sku_code ? ` (${sku.sku_code})` : ''} · 默认价 ${formatMoney(sku.price)}`,
        title: `${sku.name || '默认规格'}${sku.sku_code ? ` (${sku.sku_code})` : ''}`,
        value: sku.id,
      })));
    } catch (error) {
      setSkuOptions([]);
    }
  };

  const openPrices = (group: StoreCustomerGroup) => {
    setPriceGroup(group);
    setEditingPrice(null);
    priceForm.resetFields();
    setSkuOptions([]);
    searchProducts(undefined, group);
    loadPrices(group);
  };

  const resetPriceForm = () => {
    setEditingPrice(null);
    setSkuOptions([]);
    priceForm.resetFields();
  };

  const openEditPrice = async (record: StoreCustomerGroupPrice) => {
    setEditingPrice(record);
    if (!productOptions.some(option => option.value === record.product)) {
      setProductOptions(prev => [{
        label: `${record.product_name || `商品 #${record.product}`} · 默认价 ${formatMoney(record.product_price)}`,
        title: record.product_name || `商品 #${record.product}`,
        value: record.product,
      }, ...prev]);
    }
    await loadSkus(record.product);
    priceForm.setFieldsValue({
      product: record.product,
      sku: record.sku || undefined,
      price: Number(record.price),
    });
  };

  const handleSavePrice = async (values: PriceFormValues) => {
    if (!priceGroup) return;
    const payload = {
      group: priceGroup.id,
      product: values.product,
      sku: values.sku || null,
      price: values.price,
    };
    try {
      if (editingPrice) {
        await updateStoreCustomerGroupPrice(editingPrice.id, payload);
        message.success('价格已更新');
      } else {
        await createStoreCustomerGroupPrice(payload);
        message.success('价格已添加');
      }
      resetPriceForm();
      await loadPrices(priceGroup);
    } catch (error) {
      message.error('保存价格失败');
    }
  };

  const handleDeletePrice = async (record: StoreCustomerGroupPrice) => {
    if (!priceGroup) return;
    try {
      await deleteStoreCustomerGroupPrice(record.id);
      message.success('价格已删除');
      if (editingPrice?.id === record.id) resetPriceForm();
      await loadPrices(priceGroup);
    } catch (error) {
      message.error('删除价格失败');
    }
  };

  const groupColumns: ProColumns<StoreCustomerGroup>[] = [
    { title: 'ID', dataIndex: 'id', width: 70, hideInSearch: true },
    {
      title: '店铺',
      dataIndex: 'store',
      hideInSearch: !isPlatformAdmin,
      hideInTable: !isPlatformAdmin,
      valueType: 'select',
      fieldProps: { options: storeOptions },
      render: (_, record) => storeNameById.get(record.store) || record.store_name || `店铺 #${record.store}`,
    },
    { title: '分组名称', dataIndex: 'name', width: 180 },
    { title: '说明', dataIndex: 'description', hideInSearch: true, ellipsis: true },
    {
      title: '成员',
      dataIndex: 'member_count',
      hideInSearch: true,
      width: 120,
      render: (_, record) => `${record.active_member_count || 0}/${record.member_count || 0}`,
    },
    {
      title: '价格规则',
      dataIndex: 'price_count',
      hideInSearch: true,
      width: 110,
      render: (_, record) => record.price_count || 0,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: statusValueEnum,
      render: (_, record) => statusTag(record.status),
    },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', hideInSearch: true, width: 170 },
    {
      title: '操作',
      valueType: 'option',
      width: 220,
      fixed: 'right',
      render: (_, record) => [
        <a key="members" onClick={() => openMembers(record)}>成员</a>,
        <a key="prices" onClick={() => openPrices(record)}>价格表</a>,
        <a key="edit" onClick={() => openEditGroup(record)}>编辑</a>,
        <Popconfirm key="delete" title="确定删除该分组?" onConfirm={async () => {
          await deleteStoreCustomerGroup(record.id);
          message.success('删除成功');
          actionRef.current?.reload();
        }}>
          <a style={{ color: 'red' }}>删除</a>
        </Popconfirm>,
      ],
    },
  ];

  const memberColumns: ColumnsType<StoreCustomerGroupMember> = [
    { title: '手机号', dataIndex: 'phone' },
    { title: '小程序用户', dataIndex: 'username', render: value => value || '未注册' },
    { title: '状态', dataIndex: 'status', width: 110, render: (_, record) => statusTag(record.status) },
    { title: '加入时间', dataIndex: 'created_at', width: 170, render: value => value ? new Date(String(value)).toLocaleString() : '-' },
    {
      title: '操作',
      width: 150,
      render: (_, record) => (
        <Space>
          <Switch
            checked={record.status === 'active'}
            checkedChildren="启用"
            unCheckedChildren="停用"
            onChange={checked => handleUpdateMemberStatus(record, checked ? 'active' : 'disabled')}
          />
          <Popconfirm title="确定移除该成员?" onConfirm={() => handleDeleteMember(record)}>
            <a style={{ color: 'red' }}>移除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const priceColumns: ColumnsType<StoreCustomerGroupPrice> = [
    {
      title: '商品',
      dataIndex: 'product_name',
      width: 360,
      ellipsis: true,
      render: (_, record) => record.product_name || `商品 #${record.product}`,
    },
    {
      title: '参考价',
      dataIndex: 'product_price',
      width: 120,
      render: (_, record) => formatMoney(record.sku ? record.sku_price : record.product_price),
    },
    {
      title: 'SKU',
      dataIndex: 'sku_name',
      width: 220,
      ellipsis: true,
      render: (_, record) => record.sku ? `${record.sku_name || 'SKU'}${record.sku_code ? ` (${record.sku_code})` : ''}` : '整品默认',
    },
    { title: '分组价', dataIndex: 'price', width: 120, render: value => `¥${value}` },
    { title: '更新时间', dataIndex: 'updated_at', width: 170, render: value => value ? new Date(String(value)).toLocaleString() : '-' },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => openEditPrice(record)}>编辑</a>
          <Popconfirm title="确定删除该价格?" onConfirm={() => handleDeletePrice(record)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <ProTable<StoreCustomerGroup>
        headerTitle="客户分组"
        actionRef={actionRef}
        columns={groupColumns}
        rowKey="id"
        scroll={{ x: 'max-content' }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const res: any = await getStoreCustomerGroups({ page: current, page_size: pageSize, ...rest });
          const data = getList<StoreCustomerGroup>(res);
          return { data, success: true, total: res?.count || res?.total || data.length };
        }}
        search={{ labelWidth: 'auto', defaultCollapsed: false, collapseRender: false }}
        toolBarRender={() => [
          <Space key="actions" wrap>
            {currentStore && (
              <Space>
                <span>小程序展示分组名称</span>
                <Switch
                  checked={Boolean(currentStore.show_customer_group_name)}
                  loading={displaySwitchLoading}
                  onChange={handleToggleGroupNameDisplay}
                />
              </Space>
            )}
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateGroup}>
              新建分组
            </Button>
          </Space>,
        ]}
      />

      <ModalForm<GroupFormValues>
        title={editingGroup ? '编辑客户分组' : '新建客户分组'}
        open={modalVisible}
        form={groupForm}
        width={640}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) {
            setEditingGroup(null);
            groupForm.resetFields();
          }
        }}
        onFinish={async (values) => {
          const storeId = values.store || getDefaultStoreId();
          if (!storeId) {
            message.warning('请先选择店铺');
            return false;
          }
          const payload = { ...values, store: storeId };
          if (editingGroup) {
            await updateStoreCustomerGroup(editingGroup.id, payload);
            message.success('更新成功');
          } else {
            await createStoreCustomerGroup(payload);
            message.success('创建成功');
          }
          actionRef.current?.reload();
          return true;
        }}
      >
        {isPlatformAdmin && (
          <ProFormSelect
            name="store"
            label="所属店铺"
            options={storeOptions}
            rules={[{ required: true, message: '请选择店铺' }]}
          />
        )}
        <ProFormText name="name" label="分组名称" rules={[{ required: true, message: '请输入分组名称' }]} />
        <ProFormTextArea name="description" label="分组说明" fieldProps={{ rows: 3 }} />
        <ProFormSelect name="status" label="状态" valueEnum={statusValueEnum} rules={[{ required: true, message: '请选择状态' }]} />
      </ModalForm>

      <Drawer
        title={memberGroup ? `${memberGroup.name} - 成员维护` : '成员维护'}
        open={Boolean(memberGroup)}
        onClose={() => {
          setMemberGroup(null);
          setMembers([]);
          memberForm.resetFields();
        }}
        width={760}
      >
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Form form={memberForm} layout="inline" onFinish={handleCreateMember}>
            <Form.Item name="phone" rules={[{ required: true, message: '请输入手机号' }]} style={{ minWidth: 260 }}>
              <Input placeholder="输入客户手机号" />
            </Form.Item>
            <Button type="primary" htmlType="submit">加入分组</Button>
          </Form>
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Input.TextArea
              value={batchPhones}
              onChange={event => setBatchPhones(event.target.value)}
              placeholder="批量粘贴手机号，支持换行、逗号或空格分隔"
              rows={4}
            />
            <Space>
              <Button loading={batchImporting} onClick={handleBatchCreateMembers}>
                批量加入
              </Button>
              <span style={{ color: '#666' }}>已在本店其他分组的手机号会导入失败，并保留在输入框中。</span>
            </Space>
          </Space>
          <Table<StoreCustomerGroupMember>
            rowKey="id"
            loading={membersLoading}
            columns={memberColumns}
            dataSource={members}
            pagination={false}
          />
        </Space>
      </Drawer>

      <Modal
        title={priceGroup ? `${priceGroup.name} - 产品价格表` : '产品价格表'}
        open={Boolean(priceGroup)}
        onCancel={() => {
          setPriceGroup(null);
          setPrices([]);
          resetPriceForm();
        }}
        width={1120}
        centered
        footer={null}
        destroyOnClose
        styles={{ body: { paddingTop: 16 } }}
      >
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            type="info"
            showIcon
            message="分组价会影响用户端展示价和下单锁价；海尔商品分组价不会修改海尔同步基础价。"
          />
          <Form form={priceForm} layout="vertical" onFinish={handleSavePrice}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(420px, 1.6fr) minmax(260px, 1fr) 160px 180px',
                gap: '12px 16px',
                alignItems: 'end',
              }}
            >
              <Form.Item name="product" label="商品" rules={[{ required: true, message: '请选择商品' }]} style={{ marginBottom: 0 }}>
                <Select
                  showSearch
                  filterOption={false}
                  placeholder="搜索本店商品"
                  loading={productSearchLoading}
                  options={productOptions}
                  optionLabelProp="title"
                  style={{ width: '100%' }}
                  onSearch={keyword => searchProducts(keyword)}
                  onFocus={() => searchProducts(undefined)}
                  onChange={productId => {
                    priceForm.setFieldValue('sku', undefined);
                    loadSkus(productId);
                  }}
                />
              </Form.Item>
              <Form.Item name="sku" label="SKU" style={{ marginBottom: 0 }}>
                <Select
                  allowClear
                  placeholder="可留空"
                  options={skuOptions}
                  optionLabelProp="title"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item name="price" label="分组价" rules={[{ required: true, message: '请输入价格' }]} style={{ marginBottom: 0 }}>
                <InputNumber min={0} precision={2} addonBefore="¥" placeholder="分组价" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label=" " colon={false} style={{ marginBottom: 0 }}>
                <Space>
                  <Button type="primary" htmlType="submit">{editingPrice ? '保存价格' : '添加价格'}</Button>
                  {editingPrice && <Button onClick={resetPriceForm}>取消编辑</Button>}
                </Space>
              </Form.Item>
            </div>
          </Form>
          <div style={{ color: '#666' }}>
            SKU 留空表示配置整品统一分组价；选择某个 SKU 时，只覆盖该 SKU 的分组价。
          </div>
          <Table<StoreCustomerGroupPrice>
            rowKey="id"
            loading={pricesLoading}
            columns={priceColumns}
            dataSource={prices}
            pagination={false}
            size="middle"
            tableLayout="fixed"
            scroll={{ x: 1090, y: 420 }}
          />
        </Space>
      </Modal>
    </>
  );
}
