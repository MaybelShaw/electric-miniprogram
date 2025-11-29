import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable, ModalForm, ProFormDigit, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Button, message, Tag } from 'antd';
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCreditAccounts, createCreditAccount, updateCreditAccount, getUsers } from '@/services/api';

export default function CreditAccounts() {
  const actionRef = useRef<ActionType>();
  const navigate = useNavigate();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<any>(null);

  const columns: ProColumns<any>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      search: false,
    },
    {
      title: '经销商',
      dataIndex: 'user_name',
      width: 150,
    },
    {
      title: '公司名称',
      dataIndex: 'company_name',
      width: 200,
    },
    {
      title: '信用额度',
      dataIndex: 'credit_limit',
      width: 120,
      search: false,
      render: (_, record) => `¥${Number(record.credit_limit).toLocaleString()}`,
    },
    {
      title: '未结清欠款',
      dataIndex: 'outstanding_debt',
      width: 120,
      search: false,
      render: (_, record) => (
        <span style={{ color: Number(record.outstanding_debt) > 0 ? '#ff4d4f' : '#52c41a' }}>
          ¥{Number(record.outstanding_debt).toLocaleString()}
        </span>
      ),
    },
    {
      title: '可用额度',
      dataIndex: 'available_credit',
      width: 120,
      search: false,
      render: (_, record) => (
        <span style={{ color: Number(record.available_credit) > 0 ? '#52c41a' : '#ff4d4f' }}>
          ¥{Number(record.available_credit).toLocaleString()}
        </span>
      ),
    },
    {
      title: '账期（天）',
      dataIndex: 'payment_term_days',
      width: 100,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      valueType: 'select',
      valueEnum: {
        true: { text: '启用', status: 'Success' },
        false: { text: '停用', status: 'Error' },
      },
      render: (_, record) => (
        <Tag color={record.is_active ? 'green' : 'red'}>
          {record.is_active ? '启用' : '停用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      search: false,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_, record) => [
        <a
          key="edit"
          onClick={() => {
            setCurrentRecord(record);
            setEditModalVisible(true);
          }}
        >
          编辑
        </a>,
        <a
          key="transactions"
          onClick={() => {
            navigate(`/account-transactions?credit_account=${record.id}`);
          }}
        >
          交易记录
        </a>,
      ],
    },
  ];

  const handleCreate = async (values: any) => {
    try {
      await createCreditAccount(values);
      message.success('创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.response?.data?.error || '创建失败');
    }
  };

  const handleUpdate = async (values: any) => {
    try {
      await updateCreditAccount(currentRecord.id, values);
      message.success('更新成功');
      setEditModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.response?.data?.error || '更新失败');
    }
  };

  return (
    <>
      <ProTable<any>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const response: any = await getCreditAccounts({
            page: params.current,
            page_size: params.pageSize,
            is_active: params.is_active,
            search: params.user_name,
          });
          return {
            data: response.results,
            success: true,
            total: response.total,
          };
        }}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
        dateFormatter="string"
        headerTitle="信用账户管理"
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            创建信用账户
          </Button>,
        ]}
        scroll={{ x: 1200 }}
      />

      <ModalForm
        title="创建信用账户"
        open={createModalVisible}
        onOpenChange={setCreateModalVisible}
        onFinish={handleCreate}
        width={500}
      >
        <ProFormSelect
          name="user"
          label="经销商"
          placeholder="请选择经销商"
          rules={[{ required: true, message: '请选择经销商' }]}
          request={async () => {
            try {
              const response: any = await getUsers({ role: 'dealer' });
              const results = response.results || (Array.isArray(response) ? response : []);
              if (results.length === 0) {
                message.warning('暂无经销商用户，请先审核通过经销商认证');
                return [];
              }
              return results.map((user: any) => ({
                label: `${user.username}${user.company_info?.company_name ? ` - ${user.company_info.company_name}` : ''}`,
                value: user.id,
              }));
            } catch (error) {
              message.error('获取经销商列表失败');
              return [];
            }
          }}
        />
        <ProFormDigit
          name="credit_limit"
          label="信用额度"
          placeholder="请输入信用额度"
          rules={[{ required: true, message: '请输入信用额度' }]}
          fieldProps={{
            precision: 2,
            min: 0,
            addonBefore: '¥',
          }}
        />
        <ProFormDigit
          name="payment_term_days"
          label="账期（天）"
          placeholder="请输入账期天数"
          initialValue={30}
          rules={[{ required: true, message: '请输入账期天数' }]}
          fieldProps={{
            precision: 0,
            min: 1,
          }}
        />
      </ModalForm>

      <ModalForm
        title="编辑信用账户"
        open={editModalVisible}
        onOpenChange={setEditModalVisible}
        onFinish={handleUpdate}
        initialValues={currentRecord}
        width={500}
      >
        <ProFormDigit
          name="credit_limit"
          label="信用额度"
          placeholder="请输入信用额度"
          rules={[{ required: true, message: '请输入信用额度' }]}
          fieldProps={{
            precision: 2,
            min: 0,
            addonBefore: '¥',
          }}
        />
        <ProFormDigit
          name="payment_term_days"
          label="账期（天）"
          placeholder="请输入账期天数"
          rules={[{ required: true, message: '请输入账期天数' }]}
          fieldProps={{
            precision: 0,
            min: 1,
          }}
        />
        <ProFormSwitch
          name="is_active"
          label="账户状态"
          checkedChildren="启用"
          unCheckedChildren="停用"
        />
      </ModalForm>
    </>
  );
}
