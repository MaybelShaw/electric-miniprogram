import { Text, View } from '@tarojs/components'
import './index.scss'

interface QuantityStepperProps {
  value: number
  min?: number
  max?: number
  onChange: (value: number) => void
  className?: string
}

export default function QuantityStepper({
  value,
  min = 1,
  max,
  onChange,
  className = '',
}: QuantityStepperProps) {
  const canMinus = value > min
  const canAdd = max === undefined || value < max

  const change = (delta: number) => {
    const next = value + delta
    if (next < min) return
    if (max !== undefined && next > max) return
    onChange(next)
  }

  return (
    <View className={`quantity-stepper ${className}`}>
      <View className={`quantity-btn ${!canMinus ? 'disabled' : ''}`} onClick={() => canMinus && change(-1)}>
        <Text>-</Text>
      </View>
      <Text className='quantity-value'>{value}</Text>
      <View className={`quantity-btn ${!canAdd ? 'disabled' : ''}`} onClick={() => canAdd && change(1)}>
        <Text>+</Text>
      </View>
    </View>
  )
}
