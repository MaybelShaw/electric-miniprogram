import { Text } from '@tarojs/components'
import './index.scss'

interface StatusBadgeProps {
  children: string | number
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'muted'
  className?: string
}

export default function StatusBadge({ children, variant = 'default', className = '' }: StatusBadgeProps) {
  return <Text className={`status-badge status-badge--${variant} ${className}`}>{children}</Text>
}
