import { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button, message, Select, DatePicker, Table, Space, Checkbox, Typography, Statistic, Row, Col, Tabs, Empty, Progress, Tag } from 'antd';
import { DownloadOutlined, UserOutlined, PayCircleOutlined, ShoppingCartOutlined, RiseOutlined } from '@ant-design/icons';
import { ProCard } from '@ant-design/pro-components';
import { getUserTransactionStats, getCustomersTransactionStats, exportUserTransactionStats, exportCustomersTransactionStats, getUser, getUsers } from '@/services/api';
import dayjs from 'dayjs';

export default function UserStats() {
  const [searchParams, setSearchParams] = useSearchParams();
  const userId = searchParams.get('userId');
  
  const [activeTab, setActiveTab] = useState<'platform' | 'user'>(userId ? 'user' : 'platform');

  const [statsTargetUser, setStatsTargetUser] = useState<any>(null);
  const [statsData, setStatsData] = useState<any[]>([]);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsPeriod, setStatsPeriod] = useState<'month' | 'year'>('month');
  const [statsYear, setStatsYear] = useState<string>(dayjs().format('YYYY'));
  const [statsIncludePaid, setStatsIncludePaid] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  
  // Search state
  const [userOptions, setUserOptions] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchTimeoutRef = useRef<any>(null);

  // Sync activeTab with userId
  useEffect(() => {
    if (userId) {
      setActiveTab('user');
    }
  }, [userId]);

  const handleTabChange = (key: string) => {
    setActiveTab(key as 'platform' | 'user');
    if (key === 'platform') {
      setSearchParams({});
      setStatsTargetUser(null);
    }
  };

  const handleSearch = (value: string) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(async () => {
      if (!value) {
        setUserOptions([]);
        return;
      }
      setSearchLoading(true);
      try {
        const res: any = await getUsers({ search: value, page_size: 10 });
        const list = res.results || (Array.isArray(res) ? res : []);
        setUserOptions(list.map((u: any) => ({ 
          label: `${u.username} ${u.phone ? `(${u.phone})` : ''}`, 
          value: u.id 
        })));
      } catch (error) {
        console.error(error);
      } finally {
        setSearchLoading(false);
      }
    }, 500);
  };

  // Fetch user info if userId is present
  useEffect(() => {
    const fetchUser = async () => {
      if (userId) {
        try {
          const res: any = await getUser(Number(userId));
          setStatsTargetUser(res);
          // Update options to ensure selected value is displayed correctly
          setUserOptions(prev => {
            if (prev.find(u => u.value === res.id)) return prev;
            return [...prev, { 
              label: `${res.username} ${res.phone ? `(${res.phone})` : ''}`, 
              value: res.id 
            }];
          });
        } catch (error) {
          message.error('获取用户信息失败');
        }
      } else {
        setStatsTargetUser(null);
      }
    };
    fetchUser();
  }, [userId]);

  const fetchStats = async () => {
    // If in user tab but no user selected, don't fetch
    if (activeTab === 'user' && !userId) {
      setStatsData([]);
      return;
    }

    setStatsLoading(true);
    try {
      const params: any = {
        period: statsPeriod,
        include_paid: statsIncludePaid,
      };
      if (statsYear) {
        params.year = statsYear;
      }
      
      let res;
      if (activeTab === 'user' && userId) {
        res = await getUserTransactionStats(Number(userId), params);
      } else {
        res = await getCustomersTransactionStats(params);
      }
      setStatsData(Array.isArray(res) ? res : []);
    } catch (error) {
      message.error('获取统计数据失败');
      setStatsData([]);
    } finally {
      setStatsLoading(false);
    }
  };

  // Auto-fetch when filters or target user changes
  useEffect(() => {
    // If active tab is user, wait for user to be loaded
    if (activeTab === 'user' && userId && !statsTargetUser) return;
    fetchStats();
  }, [userId, statsTargetUser, statsPeriod, statsYear, statsIncludePaid, activeTab]);

  const handleExport = async () => {
    if (activeTab === 'user' && !userId) {
      message.warning('请先选择用户');
      return;
    }

    setExportLoading(true);
    try {
      const params: any = {
        period: statsPeriod,
        include_paid: statsIncludePaid,
      };
      if (statsYear) {
        params.year = statsYear;
      }

      let res: any;
      if (activeTab === 'user' && userId) {
        res = await exportUserTransactionStats(Number(userId), params);
      } else {
        res = await exportCustomersTransactionStats(params);
      }
      
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([res]));
      const link = document.createElement('a');
      link.href = url;
      const timestamp = dayjs().format('YYYYMMDDHHmmss');
      const filename = activeTab === 'user' && statsTargetUser
        ? `user_${statsTargetUser.id}_stats_${statsPeriod}_${statsYear || 'all'}_${timestamp}.xlsx`
        : `platform_stats_${statsPeriod}_${statsYear || 'all'}_${timestamp}.xlsx`;
        
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      message.success('导出成功');
    } catch (error) {
      console.error(error);
      message.error('导出失败');
    } finally {
      setExportLoading(false);
    }
  };

  // Calculate totals
  const { totalOrders, totalAmount, maxAmount } = useMemo(() => {
    let orders = 0;
    let amount = 0;
    let max = 0;
    statsData.forEach(item => {
      orders += item.orders;
      amount += item.amount;
      if (item.amount > max) max = item.amount;
    });
    return { totalOrders: orders, totalAmount: amount, maxAmount: max };
  }, [statsData]);

  const renderFilters = () => (
    <ProCard ghost style={{ marginBottom: 16 }} size="small">
      <Space wrap>
        <Select value={statsPeriod} onChange={setStatsPeriod} style={{ width: 120 }}>
          <Select.Option value="month">按月统计</Select.Option>
          <Select.Option value="year">按年统计</Select.Option>
        </Select>
        <DatePicker 
          picker="year" 
          value={statsYear ? dayjs(statsYear, 'YYYY') : null} 
          onChange={(date) => setStatsYear(date ? date.format('YYYY') : '')}
          allowClear
          placeholder="选择年份"
        />
        <Checkbox checked={statsIncludePaid} onChange={(e) => setStatsIncludePaid(e.target.checked)}>
          包含已支付未完成
        </Checkbox>
        <Button type="primary" onClick={fetchStats} loading={statsLoading}>
          查询
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleExport} loading={exportLoading}>
          导出Excel
        </Button>
      </Space>
    </ProCard>
  );

  const renderSummaryCards = () => (
    <Row gutter={16} style={{ marginBottom: 24 }}>
      <Col span={12}>
        <ProCard layout="center" bordered>
          <Statistic 
            title="总订单数" 
            value={totalOrders} 
            prefix={<ShoppingCartOutlined style={{ color: '#1890ff' }} />} 
            valueStyle={{ color: '#1890ff' }}
          />
        </ProCard>
      </Col>
      <Col span={12}>
        <ProCard layout="center" bordered>
          <Statistic 
            title="总交易金额" 
            value={totalAmount} 
            precision={2} 
            prefix={<PayCircleOutlined style={{ color: '#52c41a' }} />} 
            suffix="元"
            valueStyle={{ color: '#52c41a' }}
          />
        </ProCard>
      </Col>
    </Row>
  );

  const renderTable = () => (
    <Table
      dataSource={statsData}
      columns={[
        ...(activeTab === 'platform' ? [{ title: '用户名', dataIndex: 'username', key: 'username' }] : []),
        { title: statsPeriod === 'year' ? '年份' : '月份', dataIndex: 'period', key: 'period' },
        { 
          title: '订单数', 
          dataIndex: 'orders', 
          key: 'orders', 
          sorter: (a: any, b: any) => a.orders - b.orders,
          render: (v) => <Tag color="blue">{v}</Tag>
        },
        { 
          title: '交易金额', 
          dataIndex: 'amount', 
          key: 'amount', 
          sorter: (a: any, b: any) => a.amount - b.amount,
          width: 400,
          render: (v: number) => (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ width: 100 }}>¥{v.toFixed(2)}</span>
              <Progress 
                percent={maxAmount > 0 ? Math.round((v / maxAmount) * 100) : 0} 
                size="small" 
                showInfo={false}
                strokeColor="#52c41a"
                style={{ width: 200, margin: 0 }}
              />
            </div>
          ) 
        },
      ]}
      loading={statsLoading}
      rowKey={(record) => `${record.period}-${record.username || ''}`}
      pagination={{ pageSize: 20 }}
      summary={(pageData) => {
        let tOrders = 0;
        let tAmount = 0;
        pageData.forEach(({ orders, amount }) => {
          tOrders += orders;
          tAmount += amount;
        });
        return (
          <Table.Summary.Row style={{ background: '#fafafa', fontWeight: 'bold' }}>
            <Table.Summary.Cell index={0}>本页总计</Table.Summary.Cell>
            {activeTab === 'platform' && <Table.Summary.Cell index={1} />}
            <Table.Summary.Cell index={activeTab === 'platform' ? 2 : 1}>{tOrders}</Table.Summary.Cell>
            <Table.Summary.Cell index={activeTab === 'platform' ? 3 : 2}>¥{tAmount.toFixed(2)}</Table.Summary.Cell>
          </Table.Summary.Row>
        );
      }}
    />
  );

  return (
    <ProCard 
      tabs={{
        activeKey: activeTab,
        onChange: handleTabChange,
        items: [
          {
            key: 'platform',
            label: '平台统计',
            children: (
              <div style={{ paddingTop: 16 }}>
                {renderSummaryCards()}
                {renderFilters()}
                {renderTable()}
              </div>
            ),
          },
          {
            key: 'user',
            label: '用户统计',
            children: (
              <div style={{ paddingTop: 16 }}>
                <ProCard bordered style={{ marginBottom: 24 }}>
                  <Select
                    showSearch
                    placeholder="搜索用户查看统计"
                    filterOption={false}
                    onSearch={handleSearch}
                    onChange={(val) => setSearchParams(val ? { userId: String(val) } : {})}
                    notFoundContent={null}
                    options={userOptions}
                    loading={searchLoading}
                    style={{ width: 300 }}
                    value={userId ? Number(userId) : undefined}
                    allowClear
                    onClear={() => setSearchParams({})}
                  />
                </ProCard>

                {userId && statsTargetUser ? (
                  <>
                    <Row gutter={16} style={{ marginBottom: 24 }}>
                      <Col span={8}>
                        <ProCard layout="center" bordered>
                          <Statistic title="订单总数" value={statsTargetUser.orders_count} prefix={<UserOutlined />} />
                        </ProCard>
                      </Col>
                      <Col span={8}>
                        <ProCard layout="center" bordered>
                          <Statistic title="已完成订单" value={statsTargetUser.completed_orders_count} prefix={<ShoppingCartOutlined />} />
                        </ProCard>
                      </Col>
                      <Col span={8}>
                        <ProCard layout="center" bordered>
                          <Statistic title="收藏数" value={statsTargetUser.favorites_count} prefix={<RiseOutlined />} />
                        </ProCard>
                      </Col>
                    </Row>
                    {renderFilters()}
                    {renderTable()}
                  </>
                ) : (
                  <Empty 
                    image={Empty.PRESENTED_IMAGE_SIMPLE} 
                    description="请搜索并选择用户以查看统计数据" 
                    style={{ margin: '48px 0' }}
                  />
                )}
              </div>
            ),
          },
        ],
      }}
    />
  );
}