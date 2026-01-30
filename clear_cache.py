#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存清除演示脚本
演示如何使用项目中的缓存清除功能
"""

import sys
import os
import time

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_source import price_cache, get_gold_price
from logger_config import get_logger

# 获取日志记录器
logger = get_logger(__name__)

def clear_cache_demo():
    """
    清除缓存演示
    """
    print("=== 缓存清除演示 ===")
    
    # 1. 获取初始价格（会触发缓存设置）
    print("\n1. 获取初始黄金价格：")
    price1 = get_gold_price()
    print(f"获取到的价格: {price1} 元/克")
    
    # 2. 再次获取价格（应该使用缓存）
    print("\n2. 再次获取黄金价格（应该使用缓存）：")
    price2 = get_gold_price()
    print(f"获取到的价格: {price2} 元/克")
    
    # 3. 查看当前缓存状态
    print("\n3. 当前缓存状态：")
    print(f"缓存内容: {price_cache._cache}")
    print(f"缓存键数量: {len(price_cache._cache)}")
    
    # 4. 方法1：使用新添加的clear()方法清除所有缓存
    print("\n4. 使用clear()方法清除所有缓存：")
    price_cache.clear()
    print("缓存已清除")
    
    # 5. 再次获取价格（应该重新获取，不使用缓存）
    print("\n5. 再次获取黄金价格（应该重新获取，不使用缓存）：")
    price3 = get_gold_price()
    print(f"获取到的价格: {price3} 元/克")
    
    # 6. 演示清除指定键的缓存
    print("\n6. 演示清除指定键的缓存：")
    # 先获取一次价格，确保缓存中有数据
    price4 = get_gold_price()
    print(f"获取到的价格: {price4} 元/克")
    
    # 清除指定键的缓存
    print("\n7. 使用clear_key()方法清除指定键的缓存：")
    result = price_cache.clear_key('gold_price')
    print(f"清除结果: {'成功' if result else '失败'}")
    
    # 8. 再次获取价格（应该重新获取，不使用缓存）
    print("\n8. 再次获取黄金价格（应该重新获取，不使用缓存）：")
    price5 = get_gold_price()
    print(f"获取到的价格: {price5} 元/克")
    
    # 9. 方法2：直接操作缓存字典（不推荐，了解即可）
    print("\n9. 方法2：直接操作缓存字典（不推荐，了解即可）：")
    # 先获取一次价格，确保缓存中有数据
    price6 = get_gold_price()
    print(f"获取到的价格: {price6} 元/克")
    
    # 直接清空缓存字典
    price_cache._cache = {}
    print("通过直接操作缓存字典清除了缓存")
    
    # 10. 验证缓存是否已清除
    print("\n10. 最终验证缓存状态：")
    print(f"缓存字典内容: {price_cache._cache}")
    print(f"缓存是否为空: {len(price_cache._cache) == 0}")

if __name__ == "__main__":
    clear_cache_demo()