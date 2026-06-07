import { useState } from 'react'
import { View, ScrollView, Text, Image, Textarea } from '@tarojs/components'
import Taro, { useLoad, useDidShow } from '@tarojs/taro'
import { feedbackService, FeedbackTicket } from '../../services/feedback'
import { resolveLocalMediaUrl } from '../../utils/media'
import './index.scss'

const STATUS_CLASS: Record<string, string> = {
  pending: 'pending',
  replied: 'replied',
  closed: 'closed',
}

export default function FeedbackDetail() {
  const [ticketId, setTicketId] = useState<string>('')
  const [ticket, setTicket] = useState<FeedbackTicket | null>(null)
  const [content, setContent] = useState('')
  const [images, setImages] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  useLoad((params) => {
    setTicketId(String(params.id || ''))
  })

  useDidShow(() => {
    const id = ticketId || Taro.getCurrentInstance().router?.params?.id
    if (id) loadTicket(String(id))
  })

  const loadTicket = async (id = ticketId) => {
    if (!id) return
    try {
      const data = await feedbackService.getTicket(id)
      setTicket(data)
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '加载失败', icon: 'none' })
    }
  }

  const preview = (url: string, urls: string[]) => {
    Taro.previewImage({
      current: resolveLocalMediaUrl(url),
      urls: urls.map(resolveLocalMediaUrl).filter(Boolean),
    })
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
      setImages(prev => [...prev, ...res.tempFiles.map(item => item.tempFilePath)].slice(0, 9))
    } catch {
      // cancelled
    }
  }

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  const submitSupplement = async () => {
    if (!ticket || submitting) return
    if (!content.trim() && images.length === 0) {
      Taro.showToast({ title: '请填写补充内容或上传图片', icon: 'none' })
      return
    }
    setSubmitting(true)
    try {
      const data = await feedbackService.supplementTicket(ticket.id, { content: content.trim() }, images)
      setTicket(data)
      setContent('')
      setImages([])
      Taro.showToast({ title: '已补充', icon: 'success' })
    } catch (error: any) {
      Taro.showToast({ title: error?.message || '提交失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  const renderImages = (items: string[]) => {
    if (!items?.length) return null
    return (
      <View className='image-grid'>
        {items.map((image, index) => (
          <Image
            key={`${image}-${index}`}
            className='record-image'
            src={resolveLocalMediaUrl(image)}
            mode='aspectFill'
            onTap={() => preview(image, items)}
          />
        ))}
      </View>
    )
  }

  if (!ticket) {
    return <View className='feedback-detail-page'><View className='loading'>加载中...</View></View>
  }

  const isClosed = ticket.status === 'closed'

  return (
    <View className='feedback-detail-page'>
      <ScrollView className='detail-scroll' scrollY>
        <View className='summary-card'>
          <View className='summary-top'>
            <Text className='ticket-no'>{ticket.ticket_number}</Text>
            <Text className={`status ${STATUS_CLASS[ticket.status]}`}>{ticket.status_display}</Text>
          </View>
          <Text className='title'>{ticket.title}</Text>
          <View className='meta'>
            <Text>{ticket.ticket_type_display}</Text>
            <Text>{ticket.store_name}</Text>
            <Text>{ticket.created_at?.replace('T', ' ').slice(0, 16)}</Text>
          </View>
        </View>

        <View className='records-card'>
          <View className='section-title'>处理记录</View>
          <View className='record-item'>
            <View className='dot' />
            <View className='record-body'>
              <View className='record-head'>
                <Text className='record-type'>用户提交</Text>
                <Text className='record-time'>{ticket.created_at?.replace('T', ' ').slice(0, 16)}</Text>
              </View>
              <Text className='record-content'>{ticket.content}</Text>
              {renderImages(ticket.attachments || [])}
            </View>
          </View>

          {ticket.replies.map(reply => (
            <View key={reply.id} className='record-item'>
              <View className={`dot ${reply.record_type}`} />
              <View className='record-body'>
                <View className='record-head'>
                  <Text className='record-type'>{reply.record_type_display}</Text>
                  <Text className='record-time'>{reply.created_at?.replace('T', ' ').slice(0, 16)}</Text>
                </View>
                {reply.content ? <Text className='record-content'>{reply.content}</Text> : <Text className='record-content muted'>工单已关闭</Text>}
                {renderImages(reply.attachments || [])}
              </View>
            </View>
          ))}
        </View>

        {!isClosed && (
          <View className='supplement-card'>
            <View className='section-title'>补充材料</View>
            <Textarea
              className='textarea'
              value={content}
              maxlength={1000}
              placeholder='可继续补充说明，也可以只上传图片'
              onInput={event => setContent(event.detail.value)}
            />
            <View className='selected-grid'>
              {images.map((image, index) => (
                <View key={`${image}-${index}`} className='selected-image'>
                  <Image src={resolveLocalMediaUrl(image)} mode='aspectFill' className='image' />
                  <View className='remove' onTap={() => removeImage(index)}>×</View>
                </View>
              ))}
              {images.length < 9 && <View className='add-image' onTap={chooseImages}>+</View>}
            </View>
          </View>
        )}
      </ScrollView>

      {!isClosed && (
        <View className='bottom-bar'>
          <View className='submit-btn' onTap={submitSupplement}>{submitting ? '提交中...' : '提交补充'}</View>
        </View>
      )}
    </View>
  )
}
