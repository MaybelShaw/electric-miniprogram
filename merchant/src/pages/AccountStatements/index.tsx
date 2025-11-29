import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable, ModalForm, ProFormDateRangePicker, ProFormSelect, ProDescriptions } from '@ant-design/pro-components';
import { Button, message, Tag, Drawer, Table } from 'antd';
import { useRef, useState } from 'react';
import { getAccountStatements, createAccountStatement, confirmAccountStatement, settleAccountStatement, exportAccountStatement, getCreditAccounts, getAccountStatement } from '@/services/api';

export default function AccountStatements() {
  const actionRef = useRef<ActionType>();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [currentStatement, setCurrentStatement] = useState<any>(null);

  const statusMap = {
    draft: { text: '草稿', color: 'default' },
    confirmed: { text: '已确认', color: 'blue' },
    settled: { text: '已结清', color: 'green' },
  };

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
      title: '账期开始',
      dataIndex: 'period_start',
      width: 120,
      valueType: 'date',
      search: false,
    },
    {
      title: '账期结束',
      dataIndex: 'period_end',
      width: 120,
      valueType: 'date',
      search: false,
    },
    {
      title: '期末未付',
      dataIndex: 'period_end_balance',
      width: 120,
      search: false,
      render: (_, record) => (
        <span style={{ color: Number(record.period_end_balance) > 0 ? '#ff4d4f' : '#52c41a' }}>
          ¥{Number(record.period_end_balance).toLocaleString()}
        </span>
      ),
    },
    {
      title: '逾期金额',
      dataIndex: 'overdue_amount',
      width: 120,
      search: false,
      render: (_, record) => (
        <span style={{ color: Number(record.overdue_amount) > 0 ? '#ff4d4f' : '#52c41a' }}>
          ¥{Number(record.overdue_amount).toLocaleString()}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        draft: { text: '草稿', status: 'Default' },
        confirmed: { text: '已确认', status: 'Processing' },
        settled: { text: '已结清', status: 'Success' },
      },
      render: (_, record) => (
        <Tag color={statusMap[record.status as keyof typeof statusMap]?.color}>
          {statusMap[record.status as keyof typeof statusMap]?.text}
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
      width: 250,
      fixed: 'right',
      render: (_, record) => [
        <a
          key="view"
          onClick={async () => {
            const response = await getAccountStatement(record.id);
            setCurrentStatement(response);
            setDetailDrawerVisible(true);
          }}
        >
          查看详情
        </a>,
        record.status === 'draft' && (
          <a
            key="confirm"
            onClick={async () => {
              try {
                await confirmAccountStatement(record.id);
                message.success('确认成功');
                actionRef.current?.reload();
              } catch (error: any) {
                message.error(error.response?.data?.error || '确认失败');
              }
            }}
          >
            确认
          </a>
        ),
        record.status !== 'settled' && (
          <a
            key="settle"
            onClick={async () => {
              try {
                await settleAccountStatement(record.id);
                message.success('结清成功');
                actionRef.current?.reload();
              } catch (error: any) {
                message.error(error.response?.data?.error || '结清失败');
              }
            }}
          >
            结清
          </a>
        ),
        <a
          key="export"
          onClick={async () => {
            try {
              const response: any = await exportAccountStatement(record.id);
              const url = window.URL.createObjectURL(new Blob([response]));
              const link = document.createElement('a');
              link.href = url;
              link.setAttribute('download', `statement_${record.id}_${record.period_start}_${record.period_end}.xlsx`);
              document.body.appendChild(link);
              link.click();
              link.remove();
              message.success('导出成功');
            } catch (error: any) {
              message.error('导出失败');
            }
          }}
        >
          导出
        </a>,
      ],
    },
  ];

  const transactionColumns = [
    {
      title: '日期',
      dataIndex: 'created_at',
      render: (text: string) => text.split('T')[0],
    },
    {
      title: '交易类型',
      dataIndex: 'transaction_type_display',
    },
    {
      title: '金额',
      dataIndex: 'amount',
      render: (text: number) => `¥${Number(text).toLocaleString()}`,
    },
    {
      title: '余额',
      dataIndex: 'balance_after',
      render: (text: number) => `¥${Number(text).toLocaleString()}`,
    },
    {
      title: '订单信息',
      dataIndex: 'order_info',
      render: (_: any, record: any) => {
        if (record.order_info) {
          return (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span>{record.order_info.order_number}</span>
              <span style={{ fontSize: '12px', color: '#888' }}>
                {record.order_info.product_name}
              </span>
            </div>
          );
        }
        return record.order_id ? `#${record.order_id}` : '-';
      },
    },
    {
      title: '应付日期',
      dataIndex: 'due_date',
    },
    {
      title: '实付日期',
      dataIndex: 'paid_date',
    },
    {
      title: '付款状态',
      dataIndex: 'payment_status_display',
      render: (text: string, record: any) => {
        const colorMap: any = {
          unpaid: 'orange',
          paid: 'green',
          overdue: 'red',
        };
        return <Tag color={colorMap[record.payment_status]}>{text}</Tag>;
      },
    },
    {
      title: '备注',
      dataIndex: 'description',
    },
  ];

  const handleCreate = async (values: any) => {
    try {
      let [period_start, period_end] = values.period;
      // Ensure dates are strings in YYYY-MM-DD format
      if (period_start && typeof period_start === 'object' && 'format' in period_start) {
        period_start = period_start.format('YYYY-MM-DD');
      }
      if (period_end && typeof period_end === 'object' && 'format' in period_end) {
        period_end = period_end.format('YYYY-MM-DD');
      }

      await createAccountStatement({
        credit_account: values.credit_account,
        period_start,
        period_end,
      });
      message.success('创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.response?.data?.error || '创建失败');
    }
  };

  return (
    <>
      <ProTable<any>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const response: any = await getAccountStatements({
            page: params.current,
            page_size: params.pageSize,
            status: params.status,
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
        headerTitle="对账单管理"
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            生成对账单
          </Button>,
        ]}
        scroll={{ x: 1400 }}
      />

      <ModalForm
        title="生成对账单"
        open={createModalVisible}
        onOpenChange={setCreateModalVisible}
        onFinish={handleCreate}
        width={500}
      >
        <ProFormSelect
          name="credit_account"
          label="信用账户"
          placeholder="请选择信用账户"
          rules={[{ required: true, message: '请选择信用账户' }]}
          request={async () => {
            const response: any = await getCreditAccounts({ is_active: true });
            return response.results.map((account: any) => ({
              label: `${account.user_name} - ${account.company_name}`,
              value: account.id,
            }));
          }}
        />
        <ProFormDateRangePicker
          name="period"
          label="账期"
          placeholder={['开始日期', '结束日期']}
          rules={[{ required: true, message: '请选择账期' }]}
        />
      </ModalForm>

      <Drawer
        title="对账单详情"
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
        width={1000}
      >
        {currentStatement && (
          <>
            <ProDescriptions
              column={2}
              title="基本信息"
              dataSource={currentStatement}
            >
              <ProDescriptions.Item label="经销商" dataIndex="user_name" />
              <ProDescriptions.Item label="公司名称" dataIndex="company_name" />
              <ProDescriptions.Item label="账期开始" dataIndex="period_start" />
              <ProDescriptions.Item label="账期结束" dataIndex="period_end" />
              <ProDescriptions.Item label="状态">
                <Tag color={statusMap[currentStatement.status as keyof typeof statusMap]?.color}>
                  {statusMap[currentStatement.status as keyof typeof statusMap]?.text}
                </Tag>
              </ProDescriptions.Item>
            </ProDescriptions>

            <ProDescriptions
              column={2}
              title="财务汇总"
              dataSource={currentStatement}
              style={{ marginTop: 24 }}
            >
              <ProDescriptions.Item label="上期结余">
                ¥{Number(currentStatement.previous_balance).toLocaleString()}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="本期采购">
                ¥{Number(currentStatement.current_purchases).toLocaleString()}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="本期付款">
                ¥{Number(currentStatement.current_payments).toLocaleString()}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="本期退款">
                ¥{Number(currentStatement.current_refunds).toLocaleString()}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="期末未付">
                <span style={{ color: Number(currentStatement.period_end_balance) > 0 ? '#ff4d4f' : '#52c41a' }}>
                  ¥{Number(currentStatement.period_end_balance).toLocaleString()}
                </span>
              </ProDescriptions.Item>
              <ProDescriptions.Item label="账期内应付">
                ¥{Number(currentStatement.due_within_term).toLocaleString()}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="账期内已付">
                ¥{Number(currentStatement.paid_within_term).toLocaleString()}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="往来余额（逾期）">
                <span style={{ color: Number(currentStatement.overdue_amount) > 0 ? '#ff4d4f' : '#52c41a' }}>
                  ¥{Number(currentStatement.overdue_amount).toLocaleString()}
                </span>
              </ProDescriptions.Item>
            </ProDescriptions>

            <div style={{ marginTop: 24 }}>
              <h3>交易明细</h3>
              <Table
                columns={transactionColumns}
                dataSource={currentStatement.transactions}
                rowKey="id"
                pagination={false}
                scroll={{ x: 1000 }}
              />
            </div>
          </>
        )}
      </Drawer>
    </>
  );
}
