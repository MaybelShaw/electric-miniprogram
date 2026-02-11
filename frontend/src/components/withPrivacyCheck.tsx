import React from 'react'
import { View } from '@tarojs/components'
import PrivacyPopup from './PrivacyPopup'

export function withPrivacyCheck<T = any>(WrappedComponent: React.ComponentType<T>) {
  return (props: T) => {
    return (
      <View style={{ flex: 1, height: '100%' }}>
        <WrappedComponent {...(props as any)} />
        <PrivacyPopup />
      </View>
    )
  }
}
