import { useRef, useState } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormSwitch } from '@ant-design/pro-components';
import { Tag, Button, Popconfirm, message, Switch } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getUsers, createUser, updateUser, deleteUser, setAdmin, unsetAdmin } from '@/services/api';
import type { ActionType } from '@ant-design/pro-components';

export default function Users() {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);

  const columns: any = [
    { 
      title: '用户名', 
      dataIndex: 'username',
      ellipsis: true,
    },
    { 
      title: 'OpenID', 
      dataIndex: 'openid',
      ellipsis: true,
      hideInSearch: true,
      copyable: true,
    },
    { 
      title: '邮箱', 
      dataIndex: 'email',
      hideInSearch: true,
    },
    { 
      title: '手机号', 
      dataIndex: 'phone',
    },
    {
      title: '用户类型',
      dataIndex: 'user_type',
      hideInSearch: true,
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'admin' ? 'red' : 'blue'}>
          {type === 'admin' ? '管理员' : type === 'wechat' ? '微信' : '其他'}
        </Tag>
      ),
    },
    {
      title: '用户角色',
      dataIndex: 'role',
      hideInSearch: true,
      width: 100,
      render: (role: string) => (
        <Tag color={role === 'dealer' ? 'green' : 'default'}>
          {role === 'dealer' ? '经销商' : '个人用户'}
        </Tag>
      ),
    },
    {
      title: '管理员',
      dataIndex: 'is_staff',
      width: 100,
      valueType: 'select',
      valueEnum: {
        true: { text: '是', status: 'Success' },
        false: { text: '否', status: 'Default' },
      },
      render: (_: any, record: any) => (
        <Switch
          checked={record.is_staff}
          onChange={async (checked) => {
            try {
              if (checked) {
                await setAdmin(record.id);
                message.success('已设置为管理员');
              } else {
                await unsetAdmin(record.id);
                message.success('已取消管理员权限');
              }
              actionRef.current?.reload();
            } catch (error) {
              message.error('操作失败');
            }
          }}
        />
      ),
    },
    { 
      title: '订单数', 
      dataIndex: 'orders_count',
      hideInSearch: true,
      width: 100,
    },
    { 
      title: '收藏数', 
      dataIndex: 'favorites_count',
      hideInSearch: true,
      width: 100,
    },
    { 
      title: '已完成订单', 
      dataIndex: 'completed_orders_count',
      hideInSearch: true,
      width: 120,
    },
    {
      title: '注册时间',
      dataIndex: 'date_joined',
      hideInSearch: true,
      width: 180,
      valueType: 'dateTime',
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      hideInSearch: true,
      width: 180,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_: any, record: any) => [
        <Button
          key="edit"
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => {
            setEditingRecord(record);
            setModalVisible(true);
          }}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定删除该用户?"
          description="删除后无法恢复，该用户的所有数据将被保留但无法登录"
          onConfirm={async () => {
            try {
              await deleteUser(record.id);
              message.success('删除成功');
              actionRef.current?.reload();
            } catch (error) {
              message.error('删除失败');
            }
          }}
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

  return (
    <>
      <ProTable
        headerTitle="用户列表"
        actionRef={actionRef}
        columns={columns}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingRecord(null);
              setModalVisible(true);
            }}
          >
            新增用户
          </Button>,
        ]}
        request={async (params: any) => {
          try {
            const queryParams: any = {
              page: params.current || 1,
              page_size: params.pageSize || 20,
            };

            // 搜索
            if (params.username) {
              queryParams.search = params.username;
            }

            // 手机号筛选
            if (params.phone) {
              queryParams.phone = params.phone;
            }

            // 管理员筛选
            if (params.is_staff !== undefined) {
              queryParams.is_staff = params.is_staff;
            }

            const res: any = await getUsers(queryParams);
            
            // 处理分页响应
            if (res.results) {
              return {
                data: res.results,
                total: res.count || 0,
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
            message.error('加载用户列表失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        rowKey="id"
        scroll={{ x: 1400 }}
        search={{
          labelWidth: 'auto',
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total: number) => `共 ${total} 条`,
        }}
      />
      
      <ModalForm
        title={editingRecord ? '编辑用户' : '新增用户'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={async (values: any) => {
          try {
            if (editingRecord) {
              await updateUser(editingRecord.id, values);
              message.success('更新成功');
            } else {
              await createUser(values);
              message.success('创建成功');
            }
            actionRef.current?.reload();
            return true;
          } catch (error: any) {
            message.error(error.response?.data?.message || '操作失败');
            return false;
          }
        }}
        initialValues={editingRecord || {}}
      >
        <ProFormText
          name="username"
          label="用户名"
          rules={[{ required: true, message: '请输入用户名' }]}
          placeholder="请输入用户名"
        />
        
        <ProFormText
          name="email"
          label="邮箱"
          rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
          placeholder="请输入邮箱"
        />
        
        <ProFormText
          name="phone"
          label="手机号"
          rules={[
            { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号' }
          ]}
          placeholder="请输入手机号"
        />
        
        {!editingRecord && (
          <ProFormText.Password
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
            placeholder="请输入密码"
          />
        )}
        
        <ProFormSwitch
          name="is_staff"
          label="管理员权限"
          tooltip="开启后该用户可以登录商户管理后台"
        />
      </ModalForm>
    </>
  );
}
