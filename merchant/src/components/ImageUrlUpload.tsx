import { Button, Image, Space, Spin, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { uploadImage } from '@/services/api';

interface ImageUrlUploadProps {
  value?: string;
  onChange?: (value?: string) => void;
  buttonText: string;
  previewWidth?: number;
  previewHeight?: number;
  objectFit?: 'cover' | 'contain';
  allowRemove?: boolean;
}

export default function ImageUrlUpload({
  value,
  onChange,
  buttonText,
  previewWidth = 120,
  previewHeight = 80,
  objectFit = 'cover',
  allowRemove = true,
}: ImageUrlUploadProps) {
  const [loading, setLoading] = useState(false);

  const handleUpload = async ({ file, onSuccess, onError }: any) => {
    setLoading(true);
    try {
      const res: any = await uploadImage(file as File);
      if (!res.url) {
        throw new Error('上传结果缺少图片地址');
      }
      onChange?.(res.url);
      onSuccess?.(res);
      message.success('上传成功');
    } catch (error) {
      onError?.(error);
      message.error('上传失败');
    } finally {
      setLoading(false);
    }
  };

  const beforeUpload = (file: File) => {
    if (!file.type.startsWith('image/')) {
      message.error('只能上传图片文件');
      return false;
    }

    if (file.size / 1024 / 1024 >= 20) {
      message.error('图片大小不能超过 20MB');
      return false;
    }

    return true;
  };

  return (
    <Space align="center" size={16}>
      {value && (
        <Image
          src={value}
          width={previewWidth}
          height={previewHeight}
          style={{ objectFit, borderRadius: 4, border: '1px solid #f0f0f0' }}
        />
      )}
      <Upload
        accept="image/*"
        customRequest={handleUpload}
        beforeUpload={beforeUpload}
        showUploadList={false}
      >
        <Button icon={loading ? <Spin size="small" /> : <UploadOutlined />} disabled={loading}>
          {value ? '更换图片' : buttonText}
        </Button>
      </Upload>
      {allowRemove && value && (
        <Button onClick={() => onChange?.(undefined)}>
          移除
        </Button>
      )}
    </Space>
  );
}
