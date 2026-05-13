import { Text, View } from '@tarojs/components'
import AppIcon, { AppIconName } from '../AppIcon'
import './index.scss'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: AppIconName
  actionText?: string
  onAction?: () => void
  className?: string
}

export default function EmptyState({
  title,
  description,
  icon = 'empty',
  actionText,
  onAction,
  className = '',
}: EmptyStateProps) {
  return (
    <View className={`empty-state-view ${className}`}>
      <AppIcon name={icon} tone='muted' className='empty-state-icon' />
      <Text className='empty-state-title'>{title}</Text>
      {description ? <Text className='empty-state-description'>{description}</Text> : null}
      {actionText && onAction ? (
        <View className='empty-state-action' onClick={onAction}>{actionText}</View>
      ) : null}
    </View>
  )
}
