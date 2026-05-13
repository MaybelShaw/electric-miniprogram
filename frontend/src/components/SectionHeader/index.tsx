import { Text, View } from '@tarojs/components'
import './index.scss'

interface SectionHeaderProps {
  title: string
  subtitle?: string
  actionText?: string
  onAction?: () => void
  centered?: boolean
  className?: string
}

export default function SectionHeader({
  title,
  subtitle,
  actionText,
  onAction,
  centered = false,
  className = '',
}: SectionHeaderProps) {
  return (
    <View className={`section-header ${centered ? 'section-header--centered' : ''} ${className}`}>
      <View className='section-header-copy'>
        <Text className='section-header-title'>{title}</Text>
        {subtitle ? <Text className='section-header-subtitle'>{subtitle}</Text> : null}
      </View>
      {actionText && onAction ? (
        <View className='section-header-action' onClick={onAction}>{actionText}</View>
      ) : null}
    </View>
  )
}
