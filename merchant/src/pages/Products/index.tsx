import { useRef, useState, useEffect } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormDigit, ProFormSelect, ProFormSwitch, ProFormTextArea } from '@ant-design/pro-components';
import { Tag, Image, Button, Popconfirm, message, Form } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getProducts, getBrands, getCategories, createProduct, updateProduct, deleteProduct, getProduct } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';
import ImageUpload from '@/components/ImageUpload';
import { normalizeImageList } from '@/utils/image';

export default function Products() {
  const actionRef = useRef<ActionType>();
  const [brands, setBrands] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [form] = Form.useForm();

  // 加载品牌和分类数据用于筛选
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const [brandsRes, categoriesRes]: any = await Promise.all([
          getBrands(),
          getCategories(),
        ]);
        
        // 处理品牌数据
        const brandData = Array.isArray(brandsRes) ? brandsRes : (brandsRes.results || []);
        setBrands(brandData);
        
        // 处理分类数据
        const categoryData = Array.isArray(categoriesRes) ? categoriesRes : (categoriesRes.results || []);
        setCategories(categoryData);
      } catch (error) {
        // 静默失败
      }
    };
    loadFilters();
  }, []);

  const columns: any = [
    {
      title: '主图',
      dataIndex: 'main_images',
      hideInSearch: true,
      width: 80,
      render: (images: string[]) => 
        images?.[0] ? <Image src={images[0]} width={50} height={50} style={{ objectFit: 'cover' }} /> : '-',
    },
    { 
      title: '产品名称', 
      dataIndex: 'name',
      ellipsis: true,
    },
    { 
      title: '品牌', 
      dataIndex: 'brand',
      hideInSearch: true,
      width: 120,
    },
    { 
      title: '品牌筛选',
      dataIndex: 'brand',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        placeholder: '请选择品牌',
      },
      valueEnum: brands.reduce((acc: any, item: any) => {
        acc[item.name] = { text: item.name };
        return acc;
      }, {}),
    },
    { 
      title: '分类', 
      dataIndex: 'category',
      hideInSearch: true,
      width: 120,
    },
    { 
      title: '分类筛选',
      dataIndex: 'category',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        placeholder: '请选择分类',
      },
      valueEnum: categories.reduce((acc: any, item: any) => {
        acc[item.name] = { text: item.name };
        return acc;
      }, {}),
    },
    { 
      title: '价格', 
      dataIndex: 'price', 
      hideInSearch: true,
      width: 100,
      render: (price: number) => `¥${price}`,
    },
    { 
      title: '最低价格',
      dataIndex: 'min_price',
      hideInTable: true,
      valueType: 'digit',
      fieldProps: {
        placeholder: '最低价格',
        min: 0,
      },
    },
    { 
      title: '最高价格',
      dataIndex: 'max_price',
      hideInTable: true,
      valueType: 'digit',
      fieldProps: {
        placeholder: '最高价格',
        min: 0,
      },
    },
    { 
      title: '库存', 
      dataIndex: 'stock', 
      hideInSearch: true,
      width: 100,
      render: (stock: number) => (
        <Tag color={stock > 0 ? 'green' : 'red'}>{stock}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      valueType: 'select',
      valueEnum: {
        true: { text: '上架', status: 'Success' },
        false: { text: '下架', status: 'Error' },
      },
      render: (_: any, record: any) => (
        <Tag color={record.is_active ? 'green' : 'red'}>
          {record.is_active ? '上架' : '下架'}
        </Tag>
      ),
    },
    { 
      title: '销量', 
      dataIndex: 'sales_count', 
      hideInSearch: true,
      width: 100,
      sorter: true,
    },
    { 
      title: '浏览量', 
      dataIndex: 'view_count', 
      hideInSearch: true,
      width: 100,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_: any, record: any) => [
        <Button
          key="edit"
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => handleEdit(record)}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定删除该产品?"
          onConfirm={() => handleDelete(record.id)}
        >
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
          >
            删除
          </Button>
        </Popconfirm>,
      ],
    },
  ];

  const handleEdit = async (record: any) => {
    try {
      // 获取完整的产品信息
      const res: any = await getProduct(record.id);
      setEditingRecord(res);
      
      // 先打开模态框
      setModalVisible(true);
      
      // 延迟设置表单值，确保模态框已渲染
      setTimeout(() => {
        form.setFieldsValue({
          name: res.name,
          category_id: res.category_id,
          brand_id: res.brand_id,
          price: parseFloat(res.price),
          stock: res.stock,
          description: res.description || '',
          main_images: res.main_images || [],
          detail_images: res.detail_images || [],
          is_active: res.is_active,
        });
      }, 100);
    } catch (error) {
      message.error('获取产品信息失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteProduct(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleAdd = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({
      is_active: true,
      stock: 0,
      main_images: [],
      detail_images: [],
    });
    setModalVisible(true);
  };

  // 同步表单值（用于图片上传/删除后同步表单）
  const handleImageUpdate = async (productId: number, fieldName: string, urls: string[], skipDbUpdate: boolean = false) => {
    // 同步更新表单值，避免提交时被覆盖
    const currentValues = form.getFieldsValue();
    form.setFieldsValue({
      ...currentValues,
      [fieldName]: urls,
    });
    
    // 如果需要更新数据库（仅用于删除图片时）
    if (!skipDbUpdate) {
      try {
        const updateData: any = {};
        updateData[fieldName] = normalizeImageList(urls);
        
        await updateProduct(productId, updateData);
        
        // 刷新列表
        actionRef.current?.reload();
      } catch (error) {
        // 不抛出错误，避免影响用户体验
      }
    }
  };

  return (
    <>
      <ProTable
        headerTitle="产品列表"
        actionRef={actionRef}
        columns={columns}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            新增产品
          </Button>,
        ]}
      request={async (params, sort) => {
        try {
          // 构建查询参数
          const queryParams: any = {
            page: params.current || 1,
            page_size: params.pageSize || 20,
          };

          // 搜索关键词
          if (params.name) {
            queryParams.search = params.name;
          }

          // 品牌筛选
          if (params.brand) {
            queryParams.brand = params.brand;
          }

          // 分类筛选
          if (params.category) {
            queryParams.category = params.category;
          }

          // 价格筛选
          if (params.min_price) {
            queryParams.min_price = params.min_price;
          }
          if (params.max_price) {
            queryParams.max_price = params.max_price;
          }

          // 状态筛选
          if (params.is_active !== undefined) {
            queryParams.is_active = params.is_active;
          }

          // 排序
          if (sort && Object.keys(sort).length > 0) {
            const sortField = Object.keys(sort)[0];
            const sortOrder = sort[sortField];
            if (sortField === 'sales_count') {
              queryParams.sort_by = sortOrder === 'ascend' ? 'sales' : 'sales';
            }
          }

          const res: any = await getProducts(queryParams);
          
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
          message.error('加载产品列表失败');
          return { data: [], success: false, total: 0 };
        }
      }}
      rowKey="id"
      scroll={{ x: 1200 }}
      search={{
        labelWidth: 'auto',
        defaultCollapsed: false,
        optionRender: (_: any, formProps: any, dom: any[]) => [
          ...dom.reverse(),
          <Button
            key="reset"
            onClick={() => {
              formProps?.form?.resetFields();
              actionRef.current?.reload();
            }}
          >
            重置
          </Button>,
        ],
      }}
      pagination={{
        defaultPageSize: 20,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total) => `共 ${total} 条`,
      }}
      options={{
        reload: true,
        density: true,
        setting: true,
      }}
    />
      
      <ModalForm
        title={editingRecord ? '编辑产品' : '新增产品'}
        open={modalVisible}
        form={form}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) {
            // 关闭时清空表单和编辑记录
            form.resetFields();
            setEditingRecord(null);
          }
        }}
        width={800}
        onFinish={async (values) => {
          try {
            // 如果是编辑模式，先从后端获取最新的图片数据
            let finalData = { ...values };
            
            if (editingRecord) {
              try {
                const latestProduct: any = await getProduct(editingRecord.id);
                
                // 使用后端的图片数据（因为上传时已经自动更新了）
                finalData.main_images = latestProduct.main_images || [];
                finalData.detail_images = latestProduct.detail_images || [];
              } catch (error) {
                finalData.main_images = values.main_images || [];
                finalData.detail_images = values.detail_images || [];
              }
            } else {
              // 创建模式：使用表单值
              finalData.main_images = values.main_images || [];
              finalData.detail_images = values.detail_images || [];
            }
            
            const payload = {
              ...finalData,
              main_images: normalizeImageList(finalData.main_images),
              detail_images: normalizeImageList(finalData.detail_images),
            };
            
            if (editingRecord) {
              await updateProduct(editingRecord.id, payload);
              message.success('更新成功');
            } else {
              await createProduct(payload);
              message.success('创建成功');
            }
            
            actionRef.current?.reload();
            return true;
          } catch (error: any) {
            message.error(error.response?.data?.message || '操作失败');
            return false;
          }
        }}
        onFinishFailed={() => {
          message.error('请检查表单填写是否正确');
        }}
      >
        <ProFormText
          name="name"
          label="产品名称"
          rules={[{ required: true, message: '请输入产品名称' }]}
          placeholder="请输入产品名称"
        />
        
        <ProFormSelect
          name="brand_id"
          label="品牌"
          rules={[{ required: true, message: '请选择品牌' }]}
          options={brands.map(item => ({ label: item.name, value: item.id }))}
          placeholder="请选择品牌"
          showSearch
        />
        
        <ProFormSelect
          name="category_id"
          label="分类"
          rules={[{ required: true, message: '请选择分类' }]}
          options={categories.map(item => ({ label: item.name, value: item.id }))}
          placeholder="请选择分类"
          showSearch
        />
        
        <ProFormDigit
          name="price"
          label="价格"
          rules={[{ required: true, message: '请输入价格' }]}
          fieldProps={{ min: 0, precision: 2, addonBefore: '¥' }}
          placeholder="请输入价格"
        />
        
        <ProFormDigit
          name="stock"
          label="库存"
          rules={[{ required: true, message: '请输入库存' }]}
          fieldProps={{ min: 0, precision: 0 }}
          placeholder="请输入库存数量"
        />
        
        <ProFormTextArea
          name="description"
          label="产品描述"
          placeholder="请输入产品描述"
          fieldProps={{ rows: 4 }}
        />
        
        <Form.Item
          name="main_images"
          label="主图"
          tooltip="建议尺寸：800x800，最多5张。编辑时上传或删除图片会立即保存"
        >
          <ImageUpload 
            maxCount={5}
            productId={editingRecord?.id}
            fieldName="main_images"
            onImageUpdate={editingRecord ? handleImageUpdate : undefined}
          />
        </Form.Item>
        
        <Form.Item
          name="detail_images"
          label="详情图"
          tooltip="建议尺寸：750x1000，最多10张。编辑时上传或删除图片会立即保存"
        >
          <ImageUpload 
            maxCount={10}
            productId={editingRecord?.id}
            fieldName="detail_images"
            onImageUpdate={editingRecord ? handleImageUpdate : undefined}
          />
        </Form.Item>
        
        <ProFormSwitch
          name="is_active"
          label="是否上架"
          tooltip="上架后用户可见"
        />
      </ModalForm>
    </>
  );
}
