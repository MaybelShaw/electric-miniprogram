import { useState } from 'react'
import { View, Text, Button, Input, Image } from '@tarojs/components'
import Taro, { useLoad } from '@tarojs/taro'
import { orderService } from '../../services/order'
import { uploadService } from '../../services/upload'
import './index.scss'

export default function ReturnTracking() {
  const [orderId, setOrderId] = useState<number>(0)
  const [trackingNumber, setTrackingNumber] = useState('')
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
    if (!trackingNumber.trim()) {
      Taro.showToast({ title: '请填写快递单号', icon: 'none' })
      return
    }

    setSubmitting(true)
    try {
      await orderService.addReturnTracking(orderId, {
        tracking_number: trackingNumber.trim(),
        evidence_images: images
      })
      Taro.showToast({ title: '提交成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error: any) {
      Taro.showToast({ title: error.message || '提交失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View className='return-tracking'>
      <View className='form-group'>
        <View className='form-item'>
          <View className='label'>
            快递单号 <Text style={{ color: '#ff4d4f' }}>*</Text>
          </View>
          <Input
            className='input'
            placeholder='请输入快递单号'
            value={trackingNumber}
            onInput={(e) => setTrackingNumber(e.detail.value)}
          />
        </View>
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
        {submitting ? '提交中...' : '提交物流信息'}
      </Button>
    </View>
  )
}
