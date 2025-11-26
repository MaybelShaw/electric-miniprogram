import { useState, useRef } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormDigit } from '@ant-design/pro-components';
import { Button, Popconfirm, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getCategories, createCategory, updateCategory, deleteCategory } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';

export default function Categories() {
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const actionRef = useRef<ActionType>();

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
      title: '分类名称', 
      dataIndex: 'name',
      formItemProps: {
        rules: [{ required: false }],
      },
      fieldProps: {
        placeholder: '请输入分类名称搜索',
      },
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
        headerTitle="品类列表"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          try {
            // 构建查询参数
            const queryParams: any = {};
            
            // 搜索关键词
            if (params.name) {
              queryParams.search = params.name;
            }

            const res: any = await getCategories(queryParams);
            
            // 后端返回的是数组，需要转换为 ProTable 期望的格式
            const data = Array.isArray(res) ? res : (res.results || res.data || []);
            return { 
              data: data, 
              success: true,
              total: data.length 
            };
          } catch (error) {
            message.error('加载品类列表失败');
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
            新增品类
          </Button>,
        ]}
      />
      <ModalForm
        title={editingRecord ? '编辑品类' : '新增品类'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        initialValues={editingRecord || { order: 0 }}
        onFinish={async (values) => {
          try {
            if (editingRecord) {
              await updateCategory(editingRecord.id, values);
              message.success('更新成功');
            } else {
              await createCategory(values);
              message.success('创建成功');
            }
            actionRef.current?.reload();
            return true;
          } catch (error) {
            return false;
          }
        }}
      >
        <ProFormText name="name" label="分类名称" rules={[{ required: true, message: '请输入分类名称' }]} />
        <ProFormDigit name="order" label="排序" fieldProps={{ min: 0 }} />
      </ModalForm>
    </>
  );
}
