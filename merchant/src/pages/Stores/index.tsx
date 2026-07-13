import { useRef, useState } from 'react';
import { ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Form, message } from 'antd';
import { PlusOutlined, SettingOutlined } from '@ant-design/icons';
import ImageUrlUpload from '@/components/ImageUrlUpload';
import { createStore, getPartnerEntryConfig, getStores, updatePartnerEntryConfig, updateStore } from '@/services/api';
import type { Store } from '@/services/types';

export default function Stores() {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [entryConfigVisible, setEntryConfigVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Store | null>(null);
  const [form] = Form.useForm();
  const [entryForm] = Form.useForm();

  const openCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    form.setFieldsValue({
      status: 'active',
      store_type: 'partner',
      is_visible: true,
      show_on_home: true,
      home_order: 0,
      allow_haier: false,
      is_main: false,
    });
    setModalVisible(true);
  };

  const openEdit = (record: Store) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const openEntryConfig = async () => {
    const config = await getPartnerEntryConfig();
    entryForm.setFieldsValue(config);
    setEntryConfigVisible(true);
  };

  const columns: ProColumns<Store>[] = [
    { title: 'ID', dataIndex: 'id', width: 70, hideInSearch: true },
    { title: '店铺名称', dataIndex: 'name' },
    { title: '店铺编码', dataIndex: 'code' },
    {
      title: '类型',
      dataIndex: 'store_type',
      valueType: 'select',
      valueEnum: {
        self_operated: { text: '自营店铺' },
        partner: { text: '合作方店铺' },
        supplier: { text: '供应商' },
      },
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      valueType: 'select',
      valueEnum: {
        active: { text: '启用', status: 'Success' },
        disabled: { text: '停用', status: 'Default' },
      },
      width: 100,
    },
    { title: '展示', dataIndex: 'is_visible', valueType: 'switch', width: 90, hideInSearch: true },
    { title: '首页展示', dataIndex: 'show_on_home', valueType: 'switch', width: 100, hideInSearch: true },
    { title: '排序', dataIndex: 'home_order', width: 80, hideInSearch: true },
    { title: '联系电话', dataIndex: 'contact_phone', hideInSearch: true },
    { title: '更新时间', dataIndex: 'updated_at', valueType: 'dateTime', width: 170, hideInSearch: true },
    {
      title: '操作',
      valueType: 'option',
      width: 90,
      render: (_, record) => <a onClick={() => openEdit(record)}>编辑</a>,
    },
  ];

  return (
    <>
      <ProTable<Store>
        headerTitle="店铺管理"
        actionRef={actionRef}
        columns={columns}
        rowKey="id"
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const res: any = await getStores({ page: current, page_size: pageSize, ...rest });
          const data = Array.isArray(res) ? res : res.results || [];
          return { data, success: true, total: res.count || data.length };
        }}
        toolBarRender={() => [
          <Button key="entry-copy" icon={<SettingOutlined />} onClick={openEntryConfig}>
            首页配置
          </Button>,
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增店铺
          </Button>,
        ]}
      />

      <ModalForm
        title={editingRecord ? '编辑店铺' : '新增店铺'}
        open={modalVisible}
        form={form}
        width={720}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={setModalVisible}
        onFinish={async (values) => {
          if (editingRecord) {
            await updateStore(editingRecord.id, values);
            message.success('更新成功');
          } else {
            await createStore(values);
            message.success('创建成功');
          }
          setModalVisible(false);
          actionRef.current?.reload();
          return true;
        }}
      >
        <ProFormText name="name" label="店铺名称" rules={[{ required: true, message: '请输入店铺名称' }]} />
        <ProFormText name="code" label="店铺编码" rules={[{ required: true, message: '请输入店铺编码' }]} disabled={Boolean(editingRecord)} />
        <ProFormSelect
          name="status"
          label="状态"
          options={[
            { label: '启用', value: 'active' },
            { label: '停用', value: 'disabled' },
          ]}
        />
        <ProFormSelect
          name="store_type"
          label="店铺类型"
          options={[
            { label: '自营店铺', value: 'self_operated' },
            { label: '合作方店铺', value: 'partner' },
            { label: '供应商', value: 'supplier' },
          ]}
        />
        <Form.Item name="logo" label="店铺Logo">
          <ImageUrlUpload buttonText="上传Logo" previewWidth={72} previewHeight={72} objectFit="contain" />
        </Form.Item>
        <Form.Item name="cover_image" label="封面图">
          <ImageUrlUpload buttonText="上传封面图" previewWidth={160} previewHeight={90} />
        </Form.Item>
        <ProFormTextArea name="description" label="店铺简介" />
        <ProFormText name="contact_phone" label="联系电话" />
        <ProFormText name="address" label="地址" />
        <ProFormDigit name="home_order" label="首页排序" fieldProps={{ min: 0 }} />
        <ProFormSwitch name="is_visible" label="展示" />
        <ProFormSwitch name="show_on_home" label="首页展示" />
        <ProFormSwitch name="allow_haier" label="启用海尔能力" />
        <ProFormSwitch name="is_main" label="主店" disabled={Boolean(editingRecord)} />
      </ModalForm>

      <ModalForm
        title="配置合作方入口"
        open={entryConfigVisible}
        form={entryForm}
        width={560}
        modalProps={{ destroyOnClose: true }}
        onOpenChange={setEntryConfigVisible}
        onFinish={async (values) => {
          await updatePartnerEntryConfig(values);
          message.success('配置成功');
          setEntryConfigVisible(false);
          return true;
        }}
      >
        <ProFormText
          name="entry_title"
          label="首页入口标题"
          placeholder="例如：战略伙伴"
          tooltip="对应首页上方入口卡片标题"
        />
        <ProFormText
          name="entry_subtitle"
          label="首页入口副标题"
          placeholder="例如：供应链优选"
          tooltip="对应首页上方入口卡片副标题"
        />
        <ProFormText
          name="section_title"
          label="首页板块标题"
          placeholder="例如：供应链伙伴"
          tooltip="对应首页下方合作店铺板块标题"
        />
      </ModalForm>
    </>
  );
}
