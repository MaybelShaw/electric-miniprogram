import { useState, useEffect } from 'react';
import { Upload, Modal, App } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import { uploadImage } from '@/services/api';
import './index.css';

interface ImageUploadProps {
  value?: string[];
  onChange?: (urls: string[]) => void;
  maxCount?: number;
  listType?: 'picture-card' | 'picture';
  productId?: number; // 产品ID，用于编辑时立即更新
  fieldName?: 'main_images' | 'detail_images'; // 字段名
  onImageUpdate?: (productId: number, fieldName: string, urls: string[], skipDbUpdate?: boolean) => Promise<void>; // 立即更新回调
}

export default function ImageUpload({ 
  value = [], 
  onChange, 
  maxCount = 5,
  listType = 'picture-card',
  productId,
  fieldName,
  onImageUpdate
}: ImageUploadProps) {
  const { message } = App.useApp();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  
  // 当 value 变化时更新 fileList
  useEffect(() => {
    if (value && value.length > 0) {
      const newFileList = value.map((url, index) => ({
        uid: `existing-${index}-${url}`,
        name: `image-${index}`,
        status: 'done' as const,
        url: url,
      }));
      setFileList(newFileList);
    } else {
      setFileList([]);
    }
  }, [value]);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewImage, setPreviewImage] = useState('');

  const handlePreview = (file: UploadFile) => {
    setPreviewImage(file.url || '');
    setPreviewOpen(true);
  };

  const handleChange: UploadProps['onChange'] = async ({ fileList: newFileList }) => {
    // 更新 fileList（用于显示）
    setFileList(newFileList);
    
    // 检查是否有图片被删除
    if (newFileList.length < fileList.length && productId && fieldName && onImageUpdate) {
      // 提取当前所有已上传的图片URL
      const urls = newFileList
        .filter(file => file.status === 'done' && file.url)
        .map(file => file.url as string);
      
      try {
        // 立即更新数据库
        await onImageUpdate(productId, fieldName, urls, false);
        message.success('图片已删除');
      } catch (error) {
        message.error('删除图片失败');
      }
    }
  };

  const customUpload = async ({ file, onSuccess, onError }: any) => {
    try {
      // 如果是编辑模式，传递产品ID和字段名
      const res: any = await uploadImage(file, productId, fieldName);
      
      // 确保响应中有 url 字段
      if (!res.url) {
        throw new Error('服务器响应中缺少图片URL');
      }
      
      // 重要：需要将 URL 添加到 response 中，这样 Upload 组件才能正确处理
      const response = {
        ...res,
        url: res.url, // 确保 url 字段存在
      };
      
      // 写入 file.url 以便 Upload 组件在列表与预览中使用
      file.url = res.url;
      // 调用 onSuccess 会触发 Upload 组件的 onChange
      // onSuccess 的第一个参数会被设置为 file.response
      onSuccess(response, file);
      
      // 强制同步表单值（无论是否自动更新产品）
      // 使用 setTimeout 确保 handleChange 已经执行
      setTimeout(() => {
        const currentValue = value || [];
        
        if (!currentValue.includes(res.url)) {
          const newValue = [...currentValue, res.url];
          onChange?.(newValue);
          
          // 通知父组件同步（跳过数据库更新）
          if (productId && fieldName && onImageUpdate) {
            (onImageUpdate as any)(productId, fieldName, newValue, true).catch(() => {
              // 忽略错误
            });
          }
        }
      }, 300);
      
      // 显示成功消息
      if (res.product_updated) {
        message.success('图片已上传并保存到产品');
      } else {
        message.success('图片上传成功');
      }
    } catch (error: any) {
      onError(error);
      message.error(error.response?.data?.message || error.message || '上传失败');
    }
  };

  const beforeUpload = (file: File) => {
    const isImage = file.type.startsWith('image/');
    if (!isImage) {
      message.error('只能上传图片文件！');
      return false;
    }
    
    const isLt2M = file.size / 1024 / 1024 < 2;
    if (!isLt2M) {
      message.error('图片大小不能超过 2MB！');
      return false;
    }
    
    return true;
  };

  const uploadButton = (
    <div>
      <PlusOutlined />
      <div style={{ marginTop: 8 }}>上传图片</div>
    </div>
  );

  return (
    <>
      <Upload
        listType={listType}
        fileList={fileList}
        onPreview={handlePreview}
        onChange={handleChange}
        customRequest={customUpload}
        beforeUpload={beforeUpload}
        maxCount={maxCount}
        multiple
      >
        {fileList.length >= maxCount ? null : uploadButton}
      </Upload>
      <Modal
        open={previewOpen}
        title="图片预览"
        footer={null}
        onCancel={() => setPreviewOpen(false)}
      >
        <img alt="preview" style={{ width: '100%' }} src={previewImage} />
      </Modal>
    </>
  );
}
