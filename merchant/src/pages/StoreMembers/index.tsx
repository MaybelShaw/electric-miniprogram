import { useEffect, useRef, useState } from 'react';
import { ProTable, ModalForm, ProFormSelect, ProFormText } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Form, Popconfirm, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { createStoreMemberUser, deleteStoreMember, getCurrentStoreContext, getStoreMembers, getStores, updateStoreMember } from '@/services/api';
import type { CurrentStoreContext, Store, StoreMember } from '@/services/types';
import { fetchAllPaginated } from '@/utils/request';

export default function StoreMembers() {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<StoreMember | null>(null);
  const [storeContext, setStoreContext] = useState<CurrentStoreContext | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<number | undefined>();
  const [form] = Form.useForm();
  const isPlatformAdmin = Boolean(storeContext?.is_platform_admin);
  const roleOptions = isPlatformAdmin
    ? [
        { label: '平台管理员', value: 'platform_admin' },
        { label: '店铺管理员', value: 'store_admin' },
      ]
    : [
        { label: '店铺管理员', value: 'store_admin' },
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
    return record.role !== 'platform_admin';
  };

  const isMainStore = (storeId?: number) => {
    if (!storeId) return false;
    return storeContext?.stores.some(store => store.id === storeId && store.is_main) || false;
  };

  const getRoleLabel = (record: Pick<StoreMember, 'role' | 'store_is_main'>) => {
    if (record.role === 'platform_admin' || (record.role === 'store_admin' && record.store_is_main)) {
      return '平台管理员';
    }
    return '店铺管理员';
  };

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    const defaultStoreId = storeContext?.default_store?.id;
    setSelectedStoreId(defaultStoreId);
    form.setFieldsValue({
      store: defaultStoreId,
      role: 'store_admin',
      status: 'active',
    });
    setModalVisible(true);
  };

  const openEdit = (record: StoreMember) => {
    setEditingRecord(record);
    setSelectedStoreId(record.store);
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
        store_sub_admin: { text: '店铺管理员' },
        store_staff: { text: '店铺管理员' },
      },
      renderText: (_, record) => getRoleLabel(record),
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
        title={editingRecord ? '编辑店铺成员' : '新增店铺管理员'}
        open={modalVisible}
        form={form}
        width={560}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={(open) => {
          setModalVisible(open);
          if (!open) {
            setSelectedStoreId(undefined);
          }
        }}
        onFinish={async (values) => {
          if (editingRecord) {
            await updateStoreMember(editingRecord.id, values);
            message.success('更新成功');
          } else {
            await createStoreMemberUser({
              ...values,
              store: values.store || storeContext?.default_store?.id,
              role: 'store_admin',
            });
            message.success('创建成功');
          }
          setModalVisible(false);
          actionRef.current?.reload();
          return true;
        }}
      >
        {editingRecord ? (
          <ProFormText name="username" label="用户" disabled />
        ) : (
          <>
            <ProFormText
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
              placeholder="用于登录商户后台"
            />
            <ProFormText
              name="phone"
              label="手机号"
              rules={[{ pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' }]}
              placeholder="请输入手机号"
            />
            <ProFormText
              name="email"
              label="邮箱"
              rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
              placeholder="可选"
            />
            <ProFormText.Password
              name="password"
              label="初始密码"
              rules={[{ required: true, message: '请输入初始密码' }]}
              placeholder="用于首次登录"
            />
          </>
        )}
        <ProFormSelect
          name="store"
          label="店铺"
          disabled={Boolean(editingRecord) || !isPlatformAdmin}
          rules={[{ required: true, message: '请选择店铺' }]}
          fieldProps={{
            onChange: (value) => {
              setSelectedStoreId(value as number);
              form.setFieldValue('role', 'store_admin');
            },
          }}
          request={async () => {
            const stores = await fetchAllPaginated<Store>(getStores, {}, 100);
            return stores.map(store => ({ label: `${store.name} (${store.code})`, value: store.id }));
          }}
        />
        <ProFormSelect
          name="role"
          label="角色"
          disabled={!editingRecord}
          rules={[{ required: true, message: '请选择角色' }]}
          options={
            editingRecord
              ? roleOptions
              : [{ label: isMainStore(selectedStoreId) ? '平台管理员' : '店铺管理员', value: 'store_admin' }]
          }
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
