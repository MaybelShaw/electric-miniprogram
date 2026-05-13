import type { ReactNode } from 'react'
import { View } from '@tarojs/components'
import './index.scss'

interface PageShellProps {
  children: ReactNode
  className?: string
}

export default function PageShell({ children, className = '' }: PageShellProps) {
  return <View className={`page-shell ${className}`}>{children}</View>
}
