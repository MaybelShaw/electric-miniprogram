import { useState, useRef } from 'react'
import { ProTable, ProColumns, ActionType } from '@ant-design/pro-components'
import { Button, Space, Tag, Modal, Descriptions, message, Input } from 'antd'
import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons'
import { getCompanyInfoList, approveCompanyInfo, rejectCompanyInfo } from '@/services/api'

interface CompanyInfo {
  id: number
  user: number
  company_name: string
  business_license: string
  legal_representative: string
  contact_person: string
  contact_phone: string
  contact_email: string
  province: string
  city: string
  district: string
  detail_address: string
  business_scope: string
  status: 'pending' | 'approved' | 'rejected' | 'withdrawn'
  reject_reason?: string
  created_at: string
  updated_at: string
  approved_at: string | null
}

const CompanyCertification = () => {
  const actionRef = useRef<ActionType>()
  const [detailVisible, setDetailVisible] = useState(false)
  const [currentRecord, setCurrentRecord] = useState<CompanyInfo | null>(null)

  const statusMap = {
    pending: { text: '待审核', color: 'orange' },
    approved: { text: '已通过', color: 'green' },
    rejected: { text: '已拒绝', color: 'red' },
    withdrawn: { text: '已撤回', color: undefined }
  }

  const handleView = (record: CompanyInfo) => {
    setCurrentRecord(record)
    setDetailVisible(true)
  }

  const handleApprove = async (record: CompanyInfo) => {
    Modal.confirm({
      title: '确认审核通过',
      content: `确定要通过 ${record.company_name} 的认证申请吗？通过后该用户将升级为经销商。`,
      onOk: async () => {
        try {
          await approveCompanyInfo(record.id)
          message.success('审核通过，用户已升级为经销商')
          actionRef.current?.reload()
        } catch (error: any) {
          message.error(error.message || '操作失败')
        }
      }
    })
  }

  const handleReject = async (record: CompanyInfo) => {
    let reason = ''
    Modal.confirm({
      title: '确认拒绝',
      content: (
        <div>
          <div style={{ marginBottom: 12 }}>
            确定要拒绝 {record.company_name} 的认证申请吗？用户可以修改信息后重新提交。
          </div>
          <Input.TextArea
            placeholder="请输入拒绝原因（将展示给用户）"
            rows={3}
            onChange={(event) => {
              reason = event.target.value
            }}
          />
        </div>
      ),
      onOk: async () => {
        try {
          await rejectCompanyInfo(record.id, { reason })
          message.success('已拒绝该认证申请，用户可重新提交')
          actionRef.current?.reload()
        } catch (error: any) {
          message.error(error.message || '操作失败')
        }
      }
    })
  }

  const columns: ProColumns<CompanyInfo>[] = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      width: 200,
      ellipsis: true,
      fixed: 'left'
    },
    {
      title: '营业执照号',
      dataIndex: 'business_license',
      width: 180,
      ellipsis: true
    },
    {
      title: '联系人',
      dataIndex: 'contact_person',
      width: 100,
      search: false
    },
    {
      title: '联系电话',
      dataIndex: 'contact_phone',
      width: 120,
      search: false
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueType: 'select',
      valueEnum: {
        pending: { text: '待审核', status: 'Warning' },
        approved: { text: '已通过', status: 'Success' },
        rejected: { text: '已拒绝', status: 'Error' },
        withdrawn: { text: '已撤回', status: 'Default' }
      },
      render: (_, record) => (
        <Tag color={statusMap[record.status].color}>
          {statusMap[record.status].text}
        </Tag>
      )
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      width: 160,
      valueType: 'dateTime',
      search: false
    },
    {
      title: '操作',
      width: 180,
      fixed: 'right',
      search: false,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          {record.status === 'pending' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
              >
                通过
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<CloseOutlined />}
                onClick={() => handleReject(record)}
              >
                拒绝
              </Button>
            </>
          )}
        </Space>
      )
    }
  ]

  return (
    <>
      <ProTable<CompanyInfo>
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const { current, pageSize, ...filters } = params
          const response: any = await getCompanyInfoList({
            page: current,
            page_size: pageSize,
            ...filters
          })
          return {
            data: response.data?.results || response.results || [],
            success: true,
            total: response.data?.total || response.total || 0
          }
        }}
        rowKey="id"
        scroll={{ x: 1200 }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`
        }}
        search={{
          labelWidth: 'auto',
          span: 6
        }}
        dateFormatter="string"
        headerTitle="公司认证管理"
        toolBarRender={false}
      />

      <Modal
        title="公司信息详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
      >
        {currentRecord && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="公司名称" span={2}>
              {currentRecord.company_name}
            </Descriptions.Item>
            <Descriptions.Item label="营业执照号" span={2}>
              {currentRecord.business_license}
            </Descriptions.Item>
            <Descriptions.Item label="法人代表">
              {currentRecord.legal_representative}
            </Descriptions.Item>
            <Descriptions.Item label="联系人">
              {currentRecord.contact_person}
            </Descriptions.Item>
            <Descriptions.Item label="联系电话">
              {currentRecord.contact_phone}
            </Descriptions.Item>
            <Descriptions.Item label="联系邮箱">
              {currentRecord.contact_email || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="省份">
              {currentRecord.province}
            </Descriptions.Item>
            <Descriptions.Item label="城市">
              {currentRecord.city}
            </Descriptions.Item>
            <Descriptions.Item label="区县">
              {currentRecord.district}
            </Descriptions.Item>
            <Descriptions.Item label="详细地址" span={2}>
              {currentRecord.detail_address}
            </Descriptions.Item>
            <Descriptions.Item label="经营范围" span={2}>
              {currentRecord.business_scope || '-'}
            </Descriptions.Item>
            {currentRecord.status === 'rejected' && currentRecord.reject_reason && (
              <Descriptions.Item label="拒绝原因" span={2}>
                {currentRecord.reject_reason}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="审核状态">
              <Tag color={statusMap[currentRecord.status].color}>
                {statusMap[currentRecord.status].text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="提交时间">
              {new Date(currentRecord.created_at).toLocaleString()}
            </Descriptions.Item>
            {currentRecord.approved_at && (
              <Descriptions.Item label="审核时间" span={2}>
                {new Date(currentRecord.approved_at).toLocaleString()}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
        
        {currentRecord?.status === 'pending' && (
          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <Space>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => {
                  setDetailVisible(false)
                  handleApprove(currentRecord)
                }}
              >
                审核通过
              </Button>
              <Button
                danger
                icon={<CloseOutlined />}
                onClick={() => {
                  setDetailVisible(false)
                  handleReject(currentRecord)
                }}
              >
                拒绝申请
              </Button>
            </Space>
          </div>
        )}
      </Modal>
    </>
  )
}

export default CompanyCertification
