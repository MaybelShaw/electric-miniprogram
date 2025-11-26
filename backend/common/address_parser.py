"""
地址解析服务
使用JioNLP实现中文地址的智能识别和拆分
"""
import jionlp as jio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AddressParser:
    """地址解析器"""
    
    def __init__(self):
        """初始化地址解析器"""
        try:
            # JioNLP会自动加载地址词典
            self.parser = jio
            logger.info("地址解析器初始化成功")
        except Exception as e:
            logger.error(f"地址解析器初始化失败: {str(e)}")
            raise
    
    def parse_address(self, address_text: str) -> Dict[str, Optional[str]]:
        """
        解析地址文本
        
        Args:
            address_text: 完整的地址文本
            
        Returns:
            包含省、市、区、详细地址等信息的字典
        """
        if not address_text or not address_text.strip():
            return {
                'province': None,
                'city': None,
                'district': None,
                'detail': None,
                'success': False,
                'message': '地址不能为空'
            }
        
        try:
            # 使用JioNLP解析地址
            result = jio.parse_location(address_text)
            
            if not result:
                return {
                    'province': None,
                    'city': None,
                    'district': None,
                    'detail': address_text,
                    'success': False,
                    'message': '无法识别地址，请检查地址格式'
                }
            
            # 提取省市区信息
            province = result.get('province', '')
            city = result.get('city', '')
            county = result.get('county', '')  # JioNLP使用county表示区/县
            town = result.get('town', '')
            village = result.get('village', '')
            detail = result.get('detail', '')
            
            # 构建详细地址（包含街道、村等信息）
            detail_parts = []
            if town:
                detail_parts.append(town)
            if village:
                detail_parts.append(village)
            if detail:
                detail_parts.append(detail)
            
            full_detail = ''.join(detail_parts) if detail_parts else address_text
            
            # 如果没有识别出省市区，尝试使用原始文本
            if not province and not city and not county:
                return {
                    'province': None,
                    'city': None,
                    'district': None,
                    'detail': address_text,
                    'success': False,
                    'message': '无法识别省市区信息，请检查地址格式'
                }
            
            return {
                'province': province or None,
                'city': city or None,
                'district': county or None,
                'detail': full_detail or None,
                'success': True,
                'message': '地址识别成功'
            }
            
        except Exception as e:
            logger.error(f"地址解析失败: {str(e)}, 地址: {address_text}")
            return {
                'province': None,
                'city': None,
                'district': None,
                'detail': address_text,
                'success': False,
                'message': f'地址解析失败: {str(e)}'
            }
    
    def validate_address(self, province: str, city: str, district: str) -> bool:
        """
        验证省市区是否有效
        
        Args:
            province: 省份
            city: 城市
            district: 区县
            
        Returns:
            是否有效
        """
        try:
            # 使用JioNLP验证地址
            # 构建完整地址进行验证
            full_address = f"{province}{city}{district}"
            result = jio.parse_location(full_address)
            
            if result and result.get('province') and result.get('city'):
                return True
            return False
        except Exception as e:
            logger.error(f"地址验证失败: {str(e)}")
            return False
    
    def extract_phone(self, text: str) -> Optional[str]:
        """
        从文本中提取手机号
        
        Args:
            text: 文本内容
            
        Returns:
            手机号或None
        """
        try:
            phones = jio.extract_phone_number(text)
            if phones:
                return phones[0]
            return None
        except Exception as e:
            logger.error(f"手机号提取失败: {str(e)}")
            return None
    
    def extract_id_card(self, text: str) -> Optional[str]:
        """
        从文本中提取身份证号
        
        Args:
            text: 文本内容
            
        Returns:
            身份证号或None
        """
        try:
            id_cards = jio.extract_id_card(text)
            if id_cards:
                return id_cards[0]
            return None
        except Exception as e:
            logger.error(f"身份证号提取失败: {str(e)}")
            return None


# 创建全局实例
address_parser = AddressParser()
