import { useRef, useState } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormSwitch, ProFormSelect } from '@ant-design/pro-components';
import { Tag, Button, Popconfirm, message, Switch, Form, Modal } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, DownloadOutlined } from '@ant-design/icons';
import { getUsers, createUser, updateUser, deleteUser, forceDeleteUser, setAdmin, unsetAdmin, exportUsers } from '@/services/api';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import type { User } from '@/services/types';
import { downloadBlob } from '@/utils/download';
import ExportLoadingModal from '@/components/ExportLoadingModal';

export default function Users() {
  const [form] = Form.useForm();
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<User | null>(null);
  const [exportParams, setExportParams] = useState<Record<string, any>>({});
  const [exporting, setExporting] = useState(false);
  const exportLockRef = useRef(false);

  const handleExport = async () => {
    if (exportLockRef.current) return;
    exportLockRef.current = true;
    setExporting(true);
    try {
      const res: any = await exportUsers(exportParams);
      const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
      downloadBlob(res, `users_${timestamp}.xlsx`);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    } finally {
      exportLockRef.current = false;
      setExporting(false);
    }
  };

  const confirmForceDelete = (record: User) => {
    let seconds = 5;
    let timer: ReturnType<typeof setInterval> | undefined;
    const getContent = (countdown: number) => (
      <div>
        <div>将删除用户及其订单、支付、退款、对账单等所有关联数据，无法恢复。</div>
        <div style={{ marginTop: 8, color: countdown > 0 ? '#faad14' : '#52c41a' }}>
          {countdown > 0 ? `请等待 ${countdown} 秒后确认` : '可以确认删除'}
        </div>
      </div>
    );

    const modal = Modal.confirm({
      title: '二次确认：强制删除用户',
      content: getContent(seconds),
      okText: `请等待 ${seconds} 秒`,
      okType: 'danger',
      okButtonProps: { disabled: true, danger: true },
      cancelText: '取消',
      onOk: async () => {
        if (timer) {
          clearInterval(timer);
        }
        try {
          await forceDeleteUser(record.id);
          message.success('强制删除成功');
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.response?.data?.message || '强制删除失败');
        }
      },
      onCancel: () => {
        if (timer) {
          clearInterval(timer);
        }
      },
    });

    timer = setInterval(() => {
      seconds -= 1;
      if (seconds <= 0) {
        clearInterval(timer);
        modal.update({
          content: getContent(0),
          okText: '确认删除',
          okButtonProps: { disabled: false, danger: true },
        });
        return;
      }
      modal.update({
        content: getContent(seconds),
        okText: `请等待 ${seconds} 秒`,
        okButtonProps: { disabled: true, danger: true },
      });
    }, 1000);
  };

  const columns: ProColumns<User>[] = [
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
      title: '用户角色',
      dataIndex: 'role',
      width: 100,
      valueType: 'select',
      valueEnum: {
        individual: { text: '个人用户', status: 'Default' },
        dealer: { text: '经销商', status: 'Success' },
        admin: { text: '管理员', status: 'Error' },
        support: { text: '客服', status: 'Processing' },
      },
      render: (_, record) => {
        const roleMap: Record<string, { text: string; color: string }> = {
          individual: { text: '个人用户', color: 'default' },
          dealer: { text: '经销商', color: 'green' },
          admin: { text: '管理员', color: 'red' },
          support: { text: '客服', color: 'blue' },
        }
        const roleInfo = roleMap[record.role] || { text: record.role, color: 'default' }
        return <Tag color={roleInfo.color}>{roleInfo.text}</Tag>
      },
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
      render: (_, record) => (
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
      width: 220,
      fixed: 'right',
      render: (_, record) => [
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
        <Popconfirm
          key="force-delete"
          title="确定强制删除该用户?"
          description="将进入二次确认并倒计时后才可执行"
          onConfirm={() => {
            confirmForceDelete(record);
          }}
        >
          <Button
            type="link"
            size="small"
            danger
          >
            强制删除
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
          <Button key="export" icon={<DownloadOutlined />} onClick={handleExport} loading={exporting} disabled={exporting}>
            导出
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

            // 角色筛选
            if (params.role) {
              queryParams.role = params.role;
            }

            const exportQuery = { ...queryParams };
            delete exportQuery.page;
            delete exportQuery.page_size;
            setExportParams(exportQuery);

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
        form={form}
        title={editingRecord ? '编辑用户' : '新增用户'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onValuesChange={(changedValues, allValues) => {
          if (changedValues.role) {
            if (changedValues.role === 'admin') {
              form.setFieldValue('is_staff', true);
            } else {
              form.setFieldValue('is_staff', false);
            }
          }
          if (changedValues.is_staff !== undefined) {
            if (changedValues.is_staff) {
              form.setFieldValue('role', 'admin');
            } else if (allValues.role === 'admin') {
              form.setFieldValue('role', 'individual');
            }
          }
        }}
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

        <ProFormSelect
          name="role"
          label="用户角色"
          rules={[{ required: true, message: '请选择用户角色' }]}
          valueEnum={{
            individual: '个人用户',
            dealer: '经销商',
            admin: '管理员',
            support: '客服',
          }}
          placeholder="请选择用户角色"
          initialValue="individual"
        />
        
        <ProFormSwitch
          name="is_staff"
          label="管理员权限"
          tooltip="开启后该用户可以登录商户管理后台"
        />
      </ModalForm>
      <ExportLoadingModal open={exporting} />
    </>
  );
}
