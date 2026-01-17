import { useState, useRef, useEffect, useMemo } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormDigit, ProFormDateTimePicker, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Button, Popconfirm, message, Tag, Drawer, Descriptions, Form, Space } from 'antd';
import { PlusOutlined, EyeOutlined } from '@ant-design/icons';
import { getDiscounts, createDiscount, updateDiscount, deleteDiscount, getUsers, getProducts, getBrands, getCategories } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';
import { fetchAllPaginated } from '@/utils/request';

export default function Discounts() {
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentDiscount, setCurrentDiscount] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();

  const selectedBrandIds = (Form.useWatch('brand_ids', form) as number[]) || [];
  const selectedCategoryIds = (Form.useWatch('category_ids', form) as number[]) || [];
  const selectedProductIds = (Form.useWatch('product_ids', form) as number[]) || [];

  // 加载用户、商品、品牌、品类列表
  useEffect(() => {
    const loadData = async () => {
      try {
        const [userData, productData, brandData, categoryData] = await Promise.all([
          fetchAllPaginated<any>(getUsers, {}, 100),
          fetchAllPaginated<any>(getProducts, {}, 100),
          fetchAllPaginated<any>(getBrands, {}, 1000),
          fetchAllPaginated<any>(getCategories, { level: 'item' }, 1000),
        ]);
        setUsers(userData);
        setProducts(productData);
        setBrands(brandData);
        setCategories(categoryData);
      } catch (error) {
        // 静默失败
      }
    };
    loadData();
  }, []);

  useEffect(() => {
    if (!modalVisible) return;
    if (editingRecord) {
      form.resetFields();
      form.setFieldsValue({ ...editingRecord, select_all_products: false });
    } else {
      form.resetFields();
      form.setFieldsValue({ priority: 0, select_all_products: false });
    }
  }, [modalVisible, editingRecord, form]);

  const brandOptions = useMemo(
    () => brands.map((brand) => ({ label: brand.name, value: brand.id })),
    [brands]
  );

  const categoryOptions = useMemo(
    () => categories.map((category) => ({ label: category.name, value: category.id })),
    [categories]
  );

  const filteredProducts = useMemo(() => {
    if (!selectedBrandIds.length && !selectedCategoryIds.length) return products;
    return products.filter((product) => {
      const brandMatch = !selectedBrandIds.length || selectedBrandIds.includes(product.brand_id);
      const categoryMatch = !selectedCategoryIds.length || selectedCategoryIds.includes(product.category_id);
      return brandMatch && categoryMatch;
    });
  }, [products, selectedBrandIds, selectedCategoryIds]);

  const productOptions = useMemo(() => {
    if (!products.length) return [];
    const selectedSet = new Set(selectedProductIds);
    const optionsMap = new Map<number, any>();
    for (const product of filteredProducts) {
      optionsMap.set(product.id, product);
    }
    if (selectedSet.size) {
      for (const product of products) {
        if (selectedSet.has(product.id)) {
          optionsMap.set(product.id, product);
        }
      }
    }
    return Array.from(optionsMap.values()).map((product) => ({
      label: `${product.name} (¥${product.price})`,
      value: product.id,
    }));
  }, [filteredProducts, products, selectedProductIds]);

  const allBrandIds = useMemo(() => brands.map((brand) => brand.id), [brands]);
  const allCategoryIds = useMemo(() => categories.map((category) => category.id), [categories]);

  const handleSelectByBrand = () => {
    const brandIds = selectedBrandIds.length ? selectedBrandIds : allBrandIds;
    form.setFieldsValue({
      brand_ids: brandIds,
      category_ids: [],
      product_ids: [],
      select_all_products: true,
    });
  };

  const handleSelectByCategory = () => {
    const categoryIds = selectedCategoryIds.length ? selectedCategoryIds : allCategoryIds;
    form.setFieldsValue({
      brand_ids: [],
      category_ids: categoryIds,
      product_ids: [],
      select_all_products: true,
    });
  };

  const handleSelectAll = () => {
    form.setFieldsValue({
      brand_ids: selectedBrandIds,
      category_ids: selectedCategoryIds,
      product_ids: [],
      select_all_products: true,
    });
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteDiscount(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleViewDetail = (record: any) => {
    setCurrentDiscount(record);
    setDetailVisible(true);
  };

  const handleEdit = (record: any) => {
    // 提取当前折扣的用户和产品ID
    const userIds = record.targets?.map((t: any) => t.user).filter((v: any, i: any, a: any) => a.indexOf(v) === i) || [];
    const productIds = record.targets?.map((t: any) => t.product).filter((v: any, i: any, a: any) => a.indexOf(v) === i) || [];
    
    setEditingRecord({
      ...record,
      user_ids: userIds,
      product_ids: productIds,
    });
    setModalVisible(true);
  };

  const columns: any = [
    { title: '名称', dataIndex: 'name' },
    { 
      title: '折扣金额', 
      dataIndex: 'amount', 
      search: false, 
      width: 120,
      render: (amount: number) => `¥${amount}`,
    },
    { 
      title: '适用范围',
      search: false,
      width: 150,
      render: (_: any, record: any) => {
        const targets = record.targets || [];
        const userCount = new Set(targets.map((t: any) => t.user)).size;
        const productCount = new Set(targets.map((t: any) => t.product)).size;
        return `${userCount}个用户 × ${productCount}个商品`;
      },
    },
    { 
      title: '生效时间', 
      dataIndex: 'effective_time', 
      search: false, 
      valueType: 'dateTime',
      width: 180,
    },
    { 
      title: '过期时间', 
      dataIndex: 'expiration_time', 
      search: false, 
      valueType: 'dateTime',
      width: 180,
    },
    { 
      title: '优先级', 
      dataIndex: 'priority', 
      search: false, 
      width: 100,
    },
    {
      title: '状态',
      search: false,
      width: 100,
      render: (_: any, record: any) => {
        const now = new Date();
        const effective = new Date(record.effective_time);
        const expiration = new Date(record.expiration_time);
        const isActive = now >= effective && now < expiration;
        return <Tag color={isActive ? 'green' : 'red'}>{isActive ? '生效中' : '已失效'}</Tag>;
      },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_: any, record: any) => [
        <Button
          key="view"
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          查看
        </Button>,
        <Button
          key="edit"
          type="link"
          size="small"
          onClick={() => handleEdit(record)}
        >
          编辑
        </Button>,
        <Popconfirm key="delete" title="确定删除?" onConfirm={() => handleDelete(record.id)}>
          <Button
            type="link"
            size="small"
            danger
          >
            删除
          </Button>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <>
      <ProTable
        headerTitle="折扣列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            const { current, pageSize, ...rest } = params;
            const queryParams: any = {
                page: current,
                page_size: pageSize,
                ...rest
            };
            const res: any = await getDiscounts(queryParams);
            // 处理分页响应
            if (res.results) {
              return {
                data: res.results,
                total: res.pagination?.total || res.total || res.count || 0,
                success: true,
              };
            }
            // 处理数组响应
            const data = Array.isArray(res) ? res : [];
            return {
              data: data,
              total: data.length,
              success: true,
            };
          } catch (error) {
            return { data: [], success: false, total: 0 };
          }
        }}
        rowKey="id"
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalVisible(true); }}>
            新增折扣
          </Button>,
        ]}
      />
      <ModalForm
        title={editingRecord ? '编辑折扣' : '新增折扣'}
        open={modalVisible}
        form={form}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) {
            form.resetFields();
            setEditingRecord(null);
          }
        }}
        width={800}
        onFinish={async (values: any) => {
          try {
            const payload = { ...values };
            if (!payload.select_all_products) {
              delete payload.brand_ids;
              delete payload.category_ids;
            }
            // 验证必填字段
            if (!payload.user_ids || payload.user_ids.length === 0) {
              message.error('请至少选择一个用户');
              return false;
            }
            const hasProductIds = Array.isArray(payload.product_ids) && payload.product_ids.length > 0;
            if (!hasProductIds && !payload.select_all_products) {
              message.error('请至少选择商品，或使用一键全选');
              return false;
            }

            if (editingRecord) {
              await updateDiscount(editingRecord.id, payload);
              message.success('更新成功');
            } else {
              await createDiscount(payload);
              message.success('创建成功');
            }
            actionRef.current?.reload();
            return true;
          } catch (error: any) {
            message.error(error.response?.data?.message || '操作失败');
            return false;
          }
        }}
      >
        <ProFormText 
          name="name" 
          label="折扣名称" 
          rules={[{ required: true, message: '请输入折扣名称' }]}
          placeholder="请输入折扣名称"
        />
        
        <ProFormDigit 
          name="amount" 
          label="折扣金额" 
          rules={[{ required: true, message: '请输入折扣金额' }]} 
          min={0}
          fieldProps={{ 
            precision: 2,
            addonBefore: '¥',
          }}
          placeholder="请输入折扣金额"
        />
        
        <ProFormSelect
          name="user_ids"
          label="适用用户"
          mode="multiple"
          rules={[{ required: true, message: '请选择适用用户' }]}
          options={users.map(user => ({
            label: `${user.username}${user.phone ? ` (${user.phone})` : ''}`,
            value: user.id,
          }))}
          fieldProps={{
            showSearch: true,
            placeholder: '请选择适用用户',
            filterOption: (input: string, option: any) =>
              option.label.toLowerCase().includes(input.toLowerCase()),
          }}
          tooltip="选择可以享受此折扣的用户"
        />

        <ProFormSelect
          name="brand_ids"
          label="品牌筛选"
          mode="multiple"
          options={brandOptions}
          fieldProps={{
            showSearch: true,
            placeholder: '请选择品牌',
            maxTagCount: 'responsive',
            filterOption: (input: string, option: any) =>
              option.label.toLowerCase().includes(input.toLowerCase()),
          }}
          tooltip="按品牌过滤可选商品"
        />

        <ProFormSelect
          name="category_ids"
          label="品类筛选"
          mode="multiple"
          options={categoryOptions}
          fieldProps={{
            showSearch: true,
            placeholder: '请选择品类',
            maxTagCount: 'responsive',
            filterOption: (input: string, option: any) =>
              option.label.toLowerCase().includes(input.toLowerCase()),
          }}
          tooltip="按品类过滤可选商品"
        />

        <ProFormSwitch name="select_all_products" hidden />

        <Form.Item label="快捷选择">
          <Space wrap>
            <Button onClick={handleSelectByBrand}>一键品牌</Button>
            <Button onClick={handleSelectByCategory}>一键品类</Button>
            <Button type="primary" onClick={handleSelectAll}>一键全选</Button>
          </Space>
        </Form.Item>
        
        <ProFormSelect
          name="product_ids"
          label="适用商品"
          mode="multiple"
          options={productOptions}
          fieldProps={{
            showSearch: true,
            placeholder: '请选择适用商品',
            maxTagCount: 'responsive',
            onChange: () => {
              form.setFieldsValue({ select_all_products: false });
            },
            filterOption: (input: string, option: any) =>
              option.label.toLowerCase().includes(input.toLowerCase()),
          }}
          tooltip="选择可以使用此折扣的商品"
        />
        
        <ProFormDateTimePicker 
          name="effective_time" 
          label="生效时间" 
          rules={[{ required: true, message: '请选择生效时间' }]}
          placeholder="请选择生效时间"
        />
        
        <ProFormDateTimePicker 
          name="expiration_time" 
          label="过期时间" 
          rules={[{ required: true, message: '请选择过期时间' }]}
          placeholder="请选择过期时间"
        />
        
        <ProFormDigit 
          name="priority" 
          label="优先级" 
          initialValue={0}
          tooltip="数字越大优先级越高，当多个折扣同时生效时，优先使用优先级高的"
          fieldProps={{ min: 0 }}
        />
      </ModalForm>

      <Drawer
        title="折扣详情"
        width={720}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {currentDiscount && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="折扣名称" span={2}>
              {currentDiscount.name}
            </Descriptions.Item>
            <Descriptions.Item label="折扣金额" span={2}>
              <span style={{ fontSize: 18, fontWeight: 'bold', color: '#ff4d4f' }}>
                ¥{currentDiscount.amount}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="优先级">
              {currentDiscount.priority}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {(() => {
                const now = new Date();
                const effective = new Date(currentDiscount.effective_time);
                const expiration = new Date(currentDiscount.expiration_time);
                const isActive = now >= effective && now < expiration;
                return <Tag color={isActive ? 'green' : 'red'}>{isActive ? '生效中' : '已失效'}</Tag>;
              })()}
            </Descriptions.Item>
            <Descriptions.Item label="生效时间" span={2}>
              {new Date(currentDiscount.effective_time).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="过期时间" span={2}>
              {new Date(currentDiscount.expiration_time).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="适用用户" span={2}>
              {(() => {
                const targets = currentDiscount.targets || [];
                const userIds = [...new Set(targets.map((t: any) => t.user))];
                const userNames = userIds.map(uid => {
                  const user = users.find(u => u.id === uid);
                  return user ? user.username : `用户${uid}`;
                });
                return userNames.length > 0 ? userNames.join('、') : '无';
              })()}
            </Descriptions.Item>
            <Descriptions.Item label="适用商品" span={2}>
              {(() => {
                const targets = currentDiscount.targets || [];
                const productIds = [...new Set(targets.map((t: any) => t.product))];
                const productNames = productIds.map(pid => {
                  const product = products.find(p => p.id === pid);
                  return product ? product.name : `商品${pid}`;
                });
                return productNames.length > 0 ? productNames.join('、') : '无';
              })()}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {new Date(currentDiscount.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间" span={2}>
              {new Date(currentDiscount.updated_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </>
  );
}
