import { Text, View } from '@tarojs/components'
import './index.scss'

interface PriceTextProps {
  value: string | number
  className?: string
  size?: 'sm' | 'md' | 'lg'
  muted?: boolean
}

export default function PriceText({ value, className = '', size = 'md', muted = false }: PriceTextProps) {
  const num = Number(value || 0)
  const safeValue = Number.isFinite(num) ? num.toFixed(2) : '0.00'
  const [integer, decimal] = safeValue.split('.')

  return (
    <View className={`price-text price-text--${size} ${muted ? 'price-text--muted' : ''} ${className}`}>
      <Text className='price-symbol'>¥</Text>
      <Text className='price-integer'>{integer}</Text>
      <Text className='price-decimal'>.{decimal}</Text>
    </View>
  )
}
