import { useEffect, useRef, useState } from 'react';
import { ProTable, ModalForm, ProFormSelect } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Form, Popconfirm, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { createStoreMember, deleteStoreMember, getCurrentStoreContext, getStoreMemberCandidates, getStoreMembers, getStores, updateStoreMember } from '@/services/api';
import type { CurrentStoreContext, Store, StoreMember, User } from '@/services/types';
import { fetchAllPaginated } from '@/utils/request';

export default function StoreMembers() {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<StoreMember | null>(null);
  const [storeContext, setStoreContext] = useState<CurrentStoreContext | null>(null);
  const [form] = Form.useForm();
  const isPlatformAdmin = Boolean(storeContext?.is_platform_admin);
  const roleOptions = isPlatformAdmin
    ? [
        { label: '平台管理员', value: 'platform_admin' },
        { label: '店铺管理员', value: 'store_admin' },
        { label: '店铺子管理员', value: 'store_sub_admin' },
        { label: '店铺运营', value: 'store_staff' },
      ]
    : [
        { label: '店铺子管理员', value: 'store_sub_admin' },
        { label: '店铺运营', value: 'store_staff' },
      ];

  useEffect(() => {
    let cancelled = false;
    getCurrentStoreContext()
      .then((context) => {
        if (!cancelled) {
          setStoreContext(context);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStoreContext(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const canManageRecord = (record: StoreMember) => {
    if (isPlatformAdmin) return true;
    return ['store_sub_admin', 'store_staff'].includes(record.role);
  };

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({ role: isPlatformAdmin ? 'store_admin' : 'store_sub_admin', status: 'active' });
    setModalVisible(true);
  };

  const openEdit = (record: StoreMember) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const columns: ProColumns<StoreMember>[] = [
    { title: 'ID', dataIndex: 'id', width: 70, hideInSearch: true },
    { title: '用户', dataIndex: 'username' },
    { title: '店铺', dataIndex: 'store_name' },
    {
      title: '角色',
      dataIndex: 'role',
      valueType: 'select',
      valueEnum: {
        platform_admin: { text: '平台管理员' },
        store_admin: { text: '店铺管理员' },
        store_sub_admin: { text: '店铺子管理员' },
        store_staff: { text: '店铺运营' },
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      valueType: 'select',
      valueEnum: {
        active: { text: '启用', status: 'Success' },
        disabled: { text: '停用', status: 'Default' },
      },
    },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', hideInSearch: true },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => canManageRecord(record) ? [
        <a key="edit" onClick={() => openEdit(record)}>编辑</a>,
        <Popconfirm key="delete" title="确定删除该成员关系?" onConfirm={async () => {
          await deleteStoreMember(record.id);
          message.success('删除成功');
          actionRef.current?.reload();
        }}>
          <a style={{ color: 'red' }}>删除</a>
        </Popconfirm>,
      ] : [],
    },
  ];

  return (
    <>
      <ProTable<StoreMember>
        headerTitle="店铺成员管理"
        actionRef={actionRef}
        columns={columns}
        rowKey="id"
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const res: any = await getStoreMembers({ page: current, page_size: pageSize, ...rest });
          const data = Array.isArray(res) ? res : res.results || [];
          return { data, success: true, total: res.count || data.length };
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增成员
          </Button>,
        ]}
      />

      <ModalForm
        title={editingRecord ? '编辑店铺成员' : '新增店铺成员'}
        open={modalVisible}
        form={form}
        width={560}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={setModalVisible}
        onFinish={async (values) => {
          if (editingRecord) {
            await updateStoreMember(editingRecord.id, values);
            message.success('更新成功');
          } else {
            await createStoreMember(values);
            message.success('创建成功');
          }
          setModalVisible(false);
          actionRef.current?.reload();
          return true;
        }}
      >
        <ProFormSelect
          name="user"
          label="用户"
          disabled={Boolean(editingRecord)}
          rules={[{ required: true, message: '请选择用户' }]}
          showSearch
          request={async () => {
            const users = await fetchAllPaginated<User>(getStoreMemberCandidates, {}, 100);
            return users.map(user => ({ label: `${user.username} (#${user.id})`, value: user.id }));
          }}
        />
        <ProFormSelect
          name="store"
          label="店铺"
          disabled={Boolean(editingRecord)}
          rules={[{ required: true, message: '请选择店铺' }]}
          request={async () => {
            const stores = await fetchAllPaginated<Store>(getStores, {}, 100);
            return stores.map(store => ({ label: `${store.name} (${store.code})`, value: store.id }));
          }}
        />
        <ProFormSelect
          name="role"
          label="角色"
          rules={[{ required: true, message: '请选择角色' }]}
          options={roleOptions}
        />
        <ProFormSelect
          name="status"
          label="状态"
          options={[
            { label: '启用', value: 'active' },
            { label: '停用', value: 'disabled' },
          ]}
        />
      </ModalForm>
    </>
  );
}
