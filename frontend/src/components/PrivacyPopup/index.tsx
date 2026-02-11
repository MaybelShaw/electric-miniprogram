import React, { useEffect, useState } from 'react'
import { View, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import './index.scss'

const PrivacyPopup = () => {
  const [show, setShow] = useState(false)
  const [privacyContractName, setPrivacyContractName] = useState('《小程序隐私保护指引》')

  useEffect(() => {
    // 1. 小程序启动时，检查当前用户是否需要授权
    if (Taro.getPrivacySetting) {
      Taro.getPrivacySetting({
        success: (res) => {
          console.log('getPrivacySetting success:', res)
          if (res.needAuthorization) {
            setPrivacyContractName(res.privacyContractName || '《小程序隐私保护指引》')
            setShow(true)
          } else {
            console.log('无需授权，可能是以下原因：1. 已授权 2. 基础库版本过低 3. AppID 为游客模式或未在后台配置隐私协议')
          }
        },
        fail: (err) => {
          console.error('getPrivacySetting fail:', err)
        }
      })
    } else {
      console.warn('当前基础库版本不支持 Taro.getPrivacySetting，请检查详情-本地设置-调试基础库')
    }

    // 2. 监听隐私接口调用被拦截的事件
    if (Taro.onNeedPrivacyAuthorization) {
      Taro.onNeedPrivacyAuthorization((resolve) => {
        console.log('触发 onNeedPrivacyAuthorization')
        setShow(true)
      })
    }
  }, [])

  const handleAgree = () => {
    // 用户点击同意，组件状态关闭
    // 微信会自动记录授权状态，下次不会再弹
    setShow(false)
  }

  const handleDisagree = () => {
    // 用户拒绝，提示必须同意
    Taro.showToast({
      title: '需同意后才可继续使用',
      icon: 'none',
      duration: 2000
    })
  }

  const openContract = () => {
    // 跳转至微信官方的隐私协议页面
    Taro.openPrivacyContract({
      success: () => {
        console.log('隐私协议页面打开成功')
      },
      fail: (err) => {
        console.error('隐私协议页面打开失败:', err)
        Taro.showToast({
          title: '打开隐私协议失败',
          icon: 'none'
        })
      }
    })
  }

  if (!show) return null

  console.log('PrivacyPopup rendering, show:', show)

  return (
    <View className="privacy-popup-overlay">
      <View className="privacy-popup-content">
        <View className="privacy-title">用户隐私保护提示</View>
        <View className="privacy-body">
          <Text className="privacy-text">
            感谢您使用本小程序。在使用前，请您仔细阅读
            <Text className="privacy-link" onClick={openContract}>
              {privacyContractName}
            </Text>
            。当您点击“同意”并开始使用产品服务时，即表示您已理解并同意该条款内容。
          </Text>
        </View>
        <View className="privacy-footer">
          <Button className="btn-disagree" onClick={handleDisagree}>
            拒绝
          </Button>
          <Button
            className="btn-agree"
            id="agree-btn"
            openType="agreePrivacyAuthorization"
            onAgreePrivacyAuthorization={handleAgree}
          >
            同意
          </Button>
        </View>
      </View>
    </View>
  )
}

export default PrivacyPopup
