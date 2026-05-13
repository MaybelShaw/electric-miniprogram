import React from 'react'
import { View } from '@tarojs/components'
import PrivacyPopup from './PrivacyPopup'

export function withPrivacyCheck<T = any>(WrappedComponent: React.ComponentType<T>) {
  return (props: T) => {
    return (
      <View className='privacy-check-wrapper'>
        <WrappedComponent {...(props as any)} />
        <PrivacyPopup />
      </View>
    )
  }
}
