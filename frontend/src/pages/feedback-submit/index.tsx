import { useEffect, useState } from 'react'
import { View, Text, Input, Textarea, Picker, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { authService } from '../../services/auth'
import { feedbackService, FeedbackTicketType } from '../../services/feedback'
import { Store } from '../../types'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

const TYPE_OPTIONS: Array<{ label: string; value: FeedbackTicketType }> = [
  { label: '问题', value: 'question' },
  { label: '需求', value: 'requirement' },
]

export default function FeedbackSubmit() {
  const [stores, setStores] = useState<Store[]>([])
  const [storeIndex, setStoreIndex] = useState<number>(-1)
  const [ticketType, setTicketType] = useState<FeedbackTicketType>('question')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [images, setImages] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadStores()
    loadUser()
  }, [])

  const loadStores = async () => {
    try {
      const data = await feedbackService.getStores()
      setStores(data)
      if (data.length > 0) setStoreIndex(0)
    } catch (error) {
      Taro.showToast({ title: '店铺加载失败', icon: 'none' })
    }
  }

  const loadUser = async () => {
    try {
      const user = await authService.getUserProfile()
      setContactPhone(user.phone || '')
    } catch {
      // ignore
    }
  }

  const chooseImages = async () => {
    const remain = 9 - images.length
    if (remain <= 0) {
      Taro.showToast({ title: '最多上传9张图片', icon: 'none' })
      return
    }
    try {
      const res = await Taro.chooseMedia({
        count: remain,
        mediaType: ['image'],
        sourceType: ['album', 'camera'],
      })
      const next = res.tempFiles.map(item => item.tempFilePath)
      setImages(prev => [...prev, ...next].slice(0, 9))
    } catch {
      // user cancelled
    }
  }

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  const validate = () => {
    if (storeIndex < 0 || !stores[storeIndex]) {
      Taro.showToast({ title: '请选择店铺', icon: 'none' })
      return false
    }
    if (title.trim().length < 5 || title.trim().length > 60) {
      Taro.showToast({ title: '标题需为5-60字', icon: 'none' })
      return false
    }
    if (content.trim().length < 10 || content.trim().length > 1000) {
      Taro.showToast({ title: '内容需为10-1000字', icon: 'none' })
      return false
    }
    return true
  }

  const submit = async () => {
    if (submitting || !validate()) return
    setSubmitting(true)
    try {
      const ticket = await feedbackService.createTicket(
        {
          store_id: stores[storeIndex].id,
          ticket_type: ticketType,
          title: title.trim(),
          content: content.trim(),
          contact_phone: contactPhone.trim(),
        },
        images,
      )
      Taro.showToast({ title: '提交成功', icon: 'success' })
      setTimeout(() => {
        Taro.redirectTo({ url: `/pages/feedback-detail/index?id=${ticket.id}` })
      }, 300)
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '提交失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View className='feedback-submit-page'>
      <View className='form-card'>
        <View className='field'>
          <Text className='label'>工单类型</Text>
          <View className='type-tabs'>
            {TYPE_OPTIONS.map(option => (
              <View
                key={option.value}
                className={`type-tab ${ticketType === option.value ? 'active' : ''}`}
                onTap={() => setTicketType(option.value)}
              >
                {option.label}
              </View>
            ))}
          </View>
        </View>

        <View className='field'>
          <Text className='label'>选择店铺</Text>
          <Picker
            mode='selector'
            range={stores.map(store => store.name)}
            value={Math.max(storeIndex, 0)}
            onChange={event => setStoreIndex(Number(event.detail.value))}
          >
            <View className='picker-value'>{storeIndex >= 0 ? stores[storeIndex]?.name : '请选择店铺'}</View>
          </Picker>
        </View>

        <View className='field'>
          <Text className='label'>标题</Text>
          <Input
            className='input'
            value={title}
            maxlength={60}
            placeholder='请输入5-60字标题'
            onInput={event => setTitle(event.detail.value)}
          />
        </View>

        <View className='field'>
          <Text className='label'>内容</Text>
          <Textarea
            className='textarea'
            value={content}
            maxlength={1000}
            placeholder='请描述你的问题或需求，至少10字'
            onInput={event => setContent(event.detail.value)}
          />
          <Text className='counter'>{content.length}/1000</Text>
        </View>

        <View className='field'>
          <Text className='label'>联系电话</Text>
          <Input
            className='input'
            value={contactPhone}
            placeholder='选填，便于店铺联系'
            onInput={event => setContactPhone(event.detail.value)}
          />
        </View>

        <View className='field'>
          <View className='label-row'>
            <Text className='label'>图片附件</Text>
            <Text className='hint'>{images.length}/9</Text>
          </View>
          <View className='image-grid'>
            {images.map((image, index) => (
              <View key={`${image}-${index}`} className='image-item'>
                <Image src={resolveLocalMediaUrl(image)} mode='aspectFill' className='image' />
                <View className='remove' onTap={() => removeImage(index)}>×</View>
              </View>
            ))}
            {images.length < 9 && (
              <View className='add-image' onTap={chooseImages}>+</View>
            )}
          </View>
        </View>
      </View>

      <View className={`submit-btn ${submitting ? 'disabled' : ''}`} onTap={submit}>
        {submitting ? '提交中...' : '提交'}
      </View>
    </View>
  )
}
