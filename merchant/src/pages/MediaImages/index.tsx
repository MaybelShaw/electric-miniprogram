import { useRef } from 'react';
import { ProTable } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Image, Popconfirm, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { deleteMediaImage, getMediaImages, uploadImage } from '@/services/api';
import type { MediaImage } from '@/services/types';

function formatSize(size: number) {
  if (!size) return '-';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export default function MediaImages() {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<MediaImage>[] = [
    { title: 'ID', dataIndex: 'id', width: 70, hideInSearch: true },
    {
      title: '预览',
      dataIndex: 'url',
      hideInSearch: true,
      width: 120,
      render: (_, record) => <Image src={record.url} width={72} height={72} style={{ objectFit: 'cover' }} />,
    },
    { title: '文件名', dataIndex: 'original_name' },
    { title: '类型', dataIndex: 'content_type', width: 130 },
    {
      title: '大小',
      dataIndex: 'size',
      width: 110,
      hideInSearch: true,
      render: (_, record) => formatSize(record.size),
    },
    { title: '上传时间', dataIndex: 'created_at', valueType: 'dateTime', width: 170, hideInSearch: true },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      render: (_, record) => (
        <Popconfirm title="确定删除该图片?" onConfirm={async () => {
          await deleteMediaImage(record.id);
          message.success('删除成功');
          actionRef.current?.reload();
        }}>
          <a style={{ color: 'red' }}>删除</a>
        </Popconfirm>
      ),
    },
  ];

  return (
    <ProTable<MediaImage>
      headerTitle="媒体库"
      actionRef={actionRef}
      columns={columns}
      rowKey="id"
      request={async (params) => {
        const { current, pageSize, ...rest } = params;
        const res: any = await getMediaImages({ page: current, page_size: pageSize, ...rest });
        const data = Array.isArray(res) ? res : res.results || [];
        return { data, success: true, total: res.count || data.length };
      }}
      toolBarRender={() => [
        <Upload
          key="upload"
          showUploadList={false}
          customRequest={async ({ file, onSuccess, onError }) => {
            try {
              const res = await uploadImage(file as File);
              onSuccess?.(res);
              message.success('上传成功');
              actionRef.current?.reload();
            } catch (error) {
              onError?.(error as Error);
              message.error('上传失败');
            }
          }}
        >
          <Button type="primary" icon={<UploadOutlined />} title="媒体库不限定比例；按最终使用场景裁剪，建议上传清晰原图">
            上传图片
          </Button>
        </Upload>,
      ]}
    />
  );
}
