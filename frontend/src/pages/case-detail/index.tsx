import { useState, useEffect } from 'react'
import { View, Text, Image } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { caseService } from '../../services/case'
import { Case } from '../../types'
import './index.scss'

export default function CaseDetail() {
  const router = useRouter()
  const { id } = router.params
  const [caseDetail, setCaseDetail] = useState<Case | null>(null)

  useEffect(() => {
    if (id) {
      loadCaseDetail(parseInt(id))
    }
  }, [id])

  const loadCaseDetail = async (id: number) => {
    try {
      const data = await caseService.getCaseDetail(id)
      setCaseDetail(data)
      Taro.setNavigationBarTitle({ title: data.title })
    } catch (error) {
      Taro.showToast({ title: '加载案例详情失败', icon: 'none' })
    }
  }

  if (!caseDetail) return null

  return (
    <View className='case-detail'>
      <View className='header'>
        <Text className='title'>{caseDetail.title}</Text>
        <Text className='date'>{caseDetail.created_at?.split('T')[0]}</Text>
      </View>
      
      <View className='content'>
        {caseDetail.detail_blocks?.map((block, index) => (
          <View key={index} className='block-item'>
            {block.block_type === 'text' && (
              <Text className='block-text' userSelect>{block.text}</Text>
            )}
            {block.block_type === 'image' && block.image_url && (
              <Image 
                src={block.image_url} 
                className='block-image' 
                mode='widthFix'
                onClick={() => Taro.previewImage({ urls: [block.image_url!] })}
              />
            )}
          </View>
        ))}
      </View>
    </View>
  )
}
