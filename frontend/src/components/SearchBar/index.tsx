import { Input, View } from '@tarojs/components'
import AppIcon from '../AppIcon'
import './index.scss'

interface SearchBarProps {
  value: string
  placeholder?: string
  buttonText?: string
  focus?: boolean
  onInput: (value: string) => void
  onConfirm: () => void
  className?: string
}

export default function SearchBar({
  value,
  placeholder = '搜索商品',
  buttonText,
  focus = false,
  onInput,
  onConfirm,
  className = '',
}: SearchBarProps) {
  return (
    <View className={`app-search-bar ${className}`}>
      <View className='app-search-input'>
        <AppIcon name='search' className='app-search-icon' />
        <Input
          className='app-search-field'
          placeholder={placeholder}
          value={value}
          focus={focus}
          onInput={(event) => onInput(event.detail.value)}
          onConfirm={onConfirm}
        />
      </View>
      {buttonText ? (
        <View className='app-search-button' onClick={onConfirm}>{buttonText}</View>
      ) : null}
    </View>
  )
}
