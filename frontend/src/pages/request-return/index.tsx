import { useState, useEffect } from 'react'
import { View, Text, Button, Textarea, Image } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'
import { orderService } from '../../services/order'
import { uploadService } from '../../services/upload'
import './index.scss'

export default function RequestReturn() {
  const [orderId, setOrderId] = useState<number>(0)
  const [reason, setReason] = useState('')
  const [images, setImages] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  useLoad((options) => {
    if (options.id) {
      setOrderId(Number(options.id))
    }
  })

  const handleChooseImage = () => {
    Taro.chooseImage({
      count: 3 - images.length,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: async (res) => {
        Taro.showLoading({ title: '上传中...' })
        try {
          const uploadPromises = res.tempFilePaths.map(path => uploadService.uploadImage(path))
          const urls = await Promise.all(uploadPromises)
          setImages([...images, ...urls])
        } catch (error) {
          Taro.showToast({ title: '上传失败', icon: 'none' })
        } finally {
          Taro.hideLoading()
        }
      }
    })
  }

  const handleRemoveImage = (index: number) => {
    const newImages = [...images]
    newImages.splice(index, 1)
    setImages(newImages)
  }

  const handleSubmit = async () => {
    if (!reason.trim()) {
      Taro.showToast({ title: '请填写退货原因', icon: 'none' })
      return
    }

    setSubmitting(true)
    try {
      await orderService.requestReturn(orderId, {
        reason: reason.trim(),
        evidence_images: images
      })
      Taro.showToast({ title: '申请成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error: any) {
      Taro.showToast({ title: error.message || '申请失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View className='request-return'>
      <View className='form-group'>
        <View className='label'>
          退货原因 <Text style={{ color: '#ff4d4f' }}>*</Text>
        </View>
        <Textarea
          className='textarea'
          placeholder='请详细描述退货原因'
          value={reason}
          onInput={(e) => setReason(e.detail.value)}
          maxlength={200}
        />
      </View>

      <View className='form-group'>
        <View className='label'>凭证图片 (可选，最多3张)</View>
        <View className='image-list'>
          {images.map((url, index) => (
            <View key={index} className='image-item'>
              <Image className='image' src={url} mode='aspectFill' />
              <View className='delete-btn' onClick={() => handleRemoveImage(index)}>×</View>
            </View>
          ))}
          {images.length < 3 && (
            <View className='upload-btn' onClick={handleChooseImage}>
              <Text className='plus'>+</Text>
            </View>
          )}
        </View>
      </View>

      <Button 
        className='submit-btn' 
        onClick={handleSubmit}
        disabled={submitting}
      >
        {submitting ? '提交中...' : '提交申请'}
      </Button>
    </View>
  )
}
