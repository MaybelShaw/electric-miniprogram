import type { ReactNode } from 'react'
import { View } from '@tarojs/components'
import './index.scss'

interface BottomActionBarProps {
  children: ReactNode
  className?: string
}

export default function BottomActionBar({ children, className = '' }: BottomActionBarProps) {
  return <View className={`bottom-action-bar ${className}`}>{children}</View>
}
