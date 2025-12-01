import React, { useState, useEffect, useRef } from 'react';
import { Button, message, Select, DatePicker, Table, Space, Card, Tabs, Empty, Radio } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import { Pie } from '@ant-design/plots';
import { getRegionalSales, getProductRegionDistribution, getProducts, getRegionProductStats } from '@/services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

export default function SalesStats() {
  const [activeTab, setActiveTab] = useState('regional');

  // Regional Stats State
  const [regionalData, setRegionalData] = useState<any[]>([]);
  const [regionalLoading, setRegionalLoading] = useState(false);
  const [regionalLevel, setRegionalLevel] = useState('province');
  const [regionalDates, setRegionalDates] = useState<any>(null);
  const [regionalProduct, setRegionalProduct] = useState<number | undefined>(undefined);
  const [regionalMetric, setRegionalMetric] = useState('amount');

  // Product Distribution State
  const [distData, setDistData] = useState<any[]>([]);
  const [distLoading, setDistLoading] = useState(false);
  const [distProduct, setDistProduct] = useState<number | undefined>(undefined);
  const [distLevel, setDistLevel] = useState('province');
  const [distDates, setDistDates] = useState<any>(null);
  const [distMetric, setDistMetric] = useState('total_quantity');

  // Product Search State
  const [productOptions, setProductOptions] = useState<any[]>([]);
  const [productSearchLoading, setProductSearchLoading] = useState(false);
  const searchTimeoutRef = useRef<any>(null);

  // Regional Product Stats State
  const [regionProductData, setRegionProductData] = useState<any[]>([]);
  const [regionProductLoading, setRegionProductLoading] = useState(false);
  const [targetRegion, setTargetRegion] = useState<string | undefined>(undefined);
  const [targetLevel, setTargetLevel] = useState('province');
  const [regionProductDates, setRegionProductDates] = useState<any>(null);
  const [regionProductMetric, setRegionProductMetric] = useState('total_quantity');
  const [regionOptions, setRegionOptions] = useState<any[]>([]);

  const fetchProducts = async (search: string) => {
     if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
     searchTimeoutRef.current = setTimeout(async () => {
        setProductSearchLoading(true);
        try {
            const res: any = await getProducts({ search, page_size: 20 });
            const list = res.results || (Array.isArray(res) ? res : []);
            setProductOptions(list.map((p: any) => ({ label: p.name, value: p.id })));
        } catch (e) {
            console.error(e);
        } finally {
            setProductSearchLoading(false);
        }
     }, 500);
  };

  useEffect(() => {
      fetchProducts('');
  }, []);

  const fetchRegionalStats = async () => {
      setRegionalLoading(true);
      try {
          const params: any = {
              level: regionalLevel,
              start_date: regionalDates ? regionalDates[0].format('YYYY-MM-DD') : undefined,
              end_date: regionalDates ? regionalDates[1].format('YYYY-MM-DD') : undefined,
              product_id: regionalProduct,
              limit: 50
          };
          const res: any = await getRegionalSales(params);
          setRegionalData(Array.isArray(res) ? res : []);
      } catch (error) {
          message.error('获取地区销售统计失败');
      } finally {
          setRegionalLoading(false);
      }
  };

  const fetchDistStats = async () => {
      if (!distProduct) return;
      setDistLoading(true);
      try {
          const params: any = {
              product_id: distProduct,
              level: distLevel,
              start_date: distDates ? distDates[0].format('YYYY-MM-DD') : undefined,
              end_date: distDates ? distDates[1].format('YYYY-MM-DD') : undefined,
          };
          const res: any = await getProductRegionDistribution(params);
          setDistData(Array.isArray(res) ? res : []);
      } catch (error) {
          message.error('获取商品地区分布失败');
      } finally {
          setDistLoading(false);
      }
  };

  const fetchRegions = async () => {
      try {
          const params: any = {
              level: targetLevel,
              limit: 1000
          };
          if (regionProductDates) {
             params.start_date = regionProductDates[0].format('YYYY-MM-DD');
             params.end_date = regionProductDates[1].format('YYYY-MM-DD');
          }
          const res: any = await getRegionalSales(params);
          const list = Array.isArray(res) ? res : [];
          setRegionOptions(list.map((r: any) => ({ label: r.region_name, value: r.region_name })));
      } catch (e) {
          console.error(e);
      }
  };

  const fetchRegionProductStats = async () => {
      if (!targetRegion) return;
      setRegionProductLoading(true);
      try {
          const params: any = {
              region_name: targetRegion,
              level: targetLevel,
              start_date: regionProductDates ? regionProductDates[0].format('YYYY-MM-DD') : undefined,
              end_date: regionProductDates ? regionProductDates[1].format('YYYY-MM-DD') : undefined,
              order_by: regionProductMetric,
              limit: 20
          };
          const res: any = await getRegionProductStats(params);
          setRegionProductData(Array.isArray(res) ? res : []);
      } catch (error) {
          message.error('获取地区商品统计失败');
      } finally {
          setRegionProductLoading(false);
      }
  };

  useEffect(() => {
      if (activeTab === 'regional') fetchRegionalStats();
  }, [activeTab, regionalLevel, regionalDates, regionalProduct]);

  useEffect(() => {
      if (activeTab === 'distribution' && distProduct) fetchDistStats();
  }, [activeTab, distProduct, distLevel, distDates]);

  useEffect(() => {
      if (activeTab === 'region_product') {
          fetchRegions();
      }
  }, [activeTab, targetLevel, regionProductDates]);

  useEffect(() => {
      if (activeTab === 'region_product' && targetRegion) {
          fetchRegionProductStats();
      }
  }, [activeTab, targetRegion, targetLevel, regionProductDates, regionProductMetric]);

  const getCurrentTotal = (isDist: boolean) => {
      const data = isDist ? distData : regionalData;
      const metric = isDist ? distMetric : regionalMetric;
      return data.reduce((sum: number, item: any) => sum + Number(item[metric] || 0), 0);
  };

  const getRegionProductTotal = () => {
      return regionProductData.reduce((sum: number, item: any) => sum + Number(item[regionProductMetric] || 0), 0);
  };

  const columns: any[] = [
      { title: '地区', dataIndex: 'region_name', key: 'region_name' },
      { title: '订单数', dataIndex: 'orders', key: 'orders', sorter: (a: any, b: any) => a.orders - b.orders },
      { title: '销售数量', dataIndex: 'total_quantity', key: 'total_quantity', sorter: (a: any, b: any) => a.total_quantity - b.total_quantity },
      { title: '销售金额', dataIndex: 'amount', key: 'amount', render: (val: number) => `¥${Number(val).toFixed(2)}`, sorter: (a: any, b: any) => a.amount - b.amount },
      {
        title: '占比',
        key: 'percent',
        render: (_: any, record: any) => {
            const isDist = activeTab === 'distribution';
            const metric = isDist ? distMetric : regionalMetric;
            const total = getCurrentTotal(isDist);
            const val = Number(record[metric] || 0);
            return total > 0 ? `${(val / total * 100).toFixed(1)}%` : '0.0%';
        }
      }
  ];

  const regionProductColumns: any[] = [
      { title: '商品名称', dataIndex: 'product__name', key: 'product__name' },
      { title: '订单数', dataIndex: 'orders', key: 'orders', sorter: (a: any, b: any) => a.orders - b.orders },
      { title: '销售数量', dataIndex: 'total_quantity', key: 'total_quantity', sorter: (a: any, b: any) => a.total_quantity - b.total_quantity },
      { title: '销售金额', dataIndex: 'amount', key: 'amount', render: (val: number) => `¥${Number(val).toFixed(2)}`, sorter: (a: any, b: any) => a.amount - b.amount },
      {
        title: '占比',
        key: 'percent',
        render: (_: any, record: any) => {
            const total = getRegionProductTotal();
            const val = Number(record[regionProductMetric] || 0);
            return total > 0 ? `${(val / total * 100).toFixed(1)}%` : '0.0%';
        }
      }
  ];

  const regionalConfig = {
    data: regionalData,
    angleField: regionalMetric,
    colorField: 'region_name',
    radius: 0.8,
    height: 400,
    autoFit: true,
    label: {
      text: (data: any) => {
          const total = getCurrentTotal(false);
          const val = Number(data[regionalMetric] || 0);
          const p = total > 0 ? (val / total * 100).toFixed(1) : '0.0';
          return `${data.region_name} ${p}%`;
      },
      position: 'outside',
    },
    interactions: [
      {
        type: 'element-active',
      },
    ],
    meta: {
      region_name: { alias: '地区' },
      amount: { alias: '销售金额' },
      orders: { alias: '订单数' },
      total_quantity: { alias: '销售数量' },
    },
  };

  const regionProductConfig = {
    data: regionProductData,
    angleField: regionProductMetric,
    colorField: 'product__name',
    radius: 0.8,
    height: 400,
    autoFit: true,
    label: {
      text: (data: any) => {
          const total = getRegionProductTotal();
          const val = Number(data[regionProductMetric] || 0);
          const p = total > 0 ? (val / total * 100).toFixed(1) : '0.0';
          return `${data.product__name} ${p}%`;
      },
      position: 'outside',
    },
    interactions: [{ type: 'element-active' }],
    meta: {
      product__name: { alias: '商品名称' },
      amount: { alias: '销售金额' },
      orders: { alias: '订单数' },
      total_quantity: { alias: '销售数量' },
    },
  };

  const distConfig = {
    data: distData,
    angleField: distMetric,
    colorField: 'region_name',
    radius: 0.8,
    height: 400,
    autoFit: true,
    label: {
      text: (data: any) => {
          const total = getCurrentTotal(true);
          const val = Number(data[distMetric] || 0);
          const p = total > 0 ? (val / total * 100).toFixed(1) : '0.0';
          return `${data.region_name} ${p}%`;
      },
      position: 'outside',
    },
    interactions: [
      {
        type: 'element-active',
      },
    ],
    meta: {
      region_name: { alias: '地区' },
      amount: { alias: '销售金额' },
      orders: { alias: '订单数' },
      total_quantity: { alias: '销售数量' },
    },
  };

  return (
    <ProCard title="销售统计" ghost gutter={16} direction="column">
      <Tabs activeKey={activeTab} onChange={setActiveTab} type="card">
        <Tabs.TabPane tab="地区销售统计" key="regional">
           <Card bordered={false}>
              <Space style={{ marginBottom: 16 }} wrap>
                  <Select value={regionalLevel} onChange={setRegionalLevel} style={{ width: 120 }}>
                      <Option value="province">按省份</Option>
                      <Option value="city">按城市</Option>
                  </Select>
                  <RangePicker value={regionalDates} onChange={setRegionalDates} />
                  <Select
                      showSearch
                      placeholder="选择商品（可选）"
                      allowClear
                      style={{ width: 200 }}
                      filterOption={false}
                      onSearch={fetchProducts}
                      loading={productSearchLoading}
                      options={productOptions}
                      value={regionalProduct}
                      onChange={setRegionalProduct}
                  />
                  <Button type="primary" onClick={fetchRegionalStats}>查询</Button>
              </Space>
              
              <div style={{ marginBottom: 24 }}>
                <div style={{ marginBottom: 16, textAlign: 'right' }}>
                   <Radio.Group value={regionalMetric} onChange={e => setRegionalMetric(e.target.value)}>
                      <Radio.Button value="amount">销售金额</Radio.Button>
                      <Radio.Button value="orders">订单数</Radio.Button>
                      <Radio.Button value="total_quantity">销售数量</Radio.Button>
                   </Radio.Group>
                </div>
                {regionalData.length > 0 && <Pie {...regionalConfig} />}
              </div>

              <Table 
                  columns={columns} 
                  dataSource={regionalData} 
                  loading={regionalLoading} 
                  rowKey="region_name" 
                  pagination={{ pageSize: 20 }}
              />
           </Card>
        </Tabs.TabPane>
        <Tabs.TabPane tab="商品地区分布" key="distribution">
            <Card bordered={false}>
              <Space style={{ marginBottom: 16 }} wrap>
                  <Select
                      showSearch
                      placeholder="选择商品（必选）"
                      style={{ width: 200 }}
                      filterOption={false}
                      onSearch={fetchProducts}
                      loading={productSearchLoading}
                      options={productOptions}
                      value={distProduct}
                      onChange={setDistProduct}
                  />
                  <Select value={distLevel} onChange={setDistLevel} style={{ width: 120 }}>
                      <Option value="province">按省份</Option>
                      <Option value="city">按城市</Option>
                  </Select>
                  <RangePicker value={distDates} onChange={setDistDates} />
                  <Button type="primary" onClick={fetchDistStats} disabled={!distProduct}>查询</Button>
              </Space>
              {!distProduct ? (
                  <Empty description="请选择一个商品查看分布" />
              ) : (
                  <>
                    <div style={{ marginBottom: 24 }}>
                        <div style={{ marginBottom: 16, textAlign: 'right' }}>
                           <Radio.Group value={distMetric} onChange={e => setDistMetric(e.target.value)}>
                              <Radio.Button value="total_quantity">销售数量</Radio.Button>
                              <Radio.Button value="amount">销售金额</Radio.Button>
                              <Radio.Button value="orders">订单数</Radio.Button>
                           </Radio.Group>
                        </div>
                        {distData.length > 0 && <Pie {...distConfig} />}
                    </div>
                    <Table 
                        columns={columns} 
                        dataSource={distData} 
                        loading={distLoading} 
                        rowKey="region_name"
                        pagination={{ pageSize: 20 }}
                    />
                  </>
              )}
            </Card>
        </Tabs.TabPane>
        <Tabs.TabPane tab="地区热销商品" key="region_product">
            <Card bordered={false}>
              <Space style={{ marginBottom: 16 }} wrap>
                  <Select value={targetLevel} onChange={setTargetLevel} style={{ width: 120 }}>
                      <Option value="province">按省份</Option>
                      <Option value="city">按城市</Option>
                  </Select>
                  <Select
                      showSearch
                      placeholder="选择地区（必选）"
                      style={{ width: 200 }}
                      options={regionOptions}
                      value={targetRegion}
                      onChange={setTargetRegion}
                      optionFilterProp="label"
                  />
                  <RangePicker value={regionProductDates} onChange={setRegionProductDates} />
                  <Button type="primary" onClick={fetchRegionProductStats} disabled={!targetRegion}>查询</Button>
              </Space>
              {!targetRegion ? (
                  <Empty description="请选择一个地区查看商品统计" />
              ) : (
                  <>
                    <div style={{ marginBottom: 24 }}>
                        <div style={{ marginBottom: 16, textAlign: 'right' }}>
                           <Radio.Group value={regionProductMetric} onChange={e => setRegionProductMetric(e.target.value)}>
                              <Radio.Button value="total_quantity">销售数量</Radio.Button>
                              <Radio.Button value="amount">销售金额</Radio.Button>
                              <Radio.Button value="orders">订单数</Radio.Button>
                           </Radio.Group>
                        </div>
                        {regionProductData.length > 0 && <Pie {...regionProductConfig} />}
                    </div>
                    <Table 
                        columns={regionProductColumns} 
                        dataSource={regionProductData} 
                        loading={regionProductLoading} 
                        rowKey="product__id"
                        pagination={{ pageSize: 20 }}
                    />
                  </>
              )}
            </Card>
        </Tabs.TabPane>
      </Tabs>
    </ProCard>
  );
}
