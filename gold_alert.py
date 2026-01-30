# coding: utf-8
"""
黄金价格预警模块
负责处理黄金价格预警逻辑
"""

import time
from dataclasses import dataclass

from config import MAX_PUSH_COUNT, DEFAULT_GOLD_PRICE, DEFAULT_PRICE_GAP_HIGH, DEFAULT_PRICE_GAP_LOW, PRICE_CHANGE_THRESHOLD, GLOBAL_PUSH_INTERVAL
from message import MessageSender
from logger_config import get_logger
from utils import build_message_data, send_push_message, PushStatusManager

# 获取日志记录器
logger = get_logger(__name__)

@dataclass
class GoldAlertConfig:
    """黄金预警配置类"""
    default_gold_price: float = DEFAULT_GOLD_PRICE  # 默认黄金价格（人民币/克）
    price_gap_high: float = DEFAULT_PRICE_GAP_HIGH  # 默认价格上涨浮动差额（人民币/克）
    price_gap_low: float = DEFAULT_PRICE_GAP_LOW  # 默认价格下跌浮动差额（人民币/克）
    price_change_threshold: float = PRICE_CHANGE_THRESHOLD  # 价格变化阈值（元），用于防止重复推送
    global_push_interval: int = GLOBAL_PUSH_INTERVAL  # 全局推送最小间隔（秒）
    base_price_adjust_step: float = 5  # 基准价格调整步长

class GoldAlert:
    """
    黄金价格预警管理器
    """
    def __init__(self):
        self.config = GoldAlertConfig()
        self.message_sender = MessageSender()
        
        # 集成推送状态管理器
        self.push_status_manager = PushStatusManager()
        
        # 预警状态
        self.alerted_high = False
        self.alerted_low = False
        
        # 基准价格
        self.original_base_price = self.config.default_gold_price  # 原始基准价格
        self.dynamic_base_price = self.config.default_gold_price   # 动态基准价格
    
    def can_send_global_push(self):
        """
        检查是否可以进行全局推送（防止短时间内推送过多）
        :return: bool 是否可以推送
        """
        current_time = time.time()
        if current_time - self.push_status_manager.last_global_push_time >= self.config.global_push_interval:
            return True
        return False
    
    def update_global_push_time(self):
        """
        更新全局推送时间
        """
        self.push_status_manager.update_global_push_time()
    
    def update_default_gold_price(self, new_price):
        """
        更新默认黄金价格为新的预警价格
        :param new_price: 新的价格
        :return: None
        """
        old_dynamic_price = self.dynamic_base_price
        self.dynamic_base_price = new_price
        # 同时更新默认黄金价格
        self.config.default_gold_price = new_price
        
        logger.info(f"动态黄金价格已更新: {old_dynamic_price} -> {new_price}")
        logger.info(f"新的预警阈值: 高价={self.dynamic_base_price + self.config.price_gap_high:.2f}, 低价={self.dynamic_base_price - self.config.price_gap_low:.2f}")
    

    
    def adjust_base_price_gradually(self, price):
        """
        渐进式调整基准价格
        当基准价加上浮动阈值仍小于当前价时，逐步增加基准价
        使基准价与当前价的差值保持在浮动阈值的合理范围内
        :param price: 当前黄金价格
        :return: bool 是否进行了调整
        """
        # 定义步长和目标差值
        STEP_SIZE = self.config.base_price_adjust_step  # 每次调整的步长
        TARGET_GAP = (self.config.price_gap_high + self.config.price_gap_low) / 2  # 目标差值为上下浮动的中间值
        
        # 计算当前的预警阈值
        alert_high_threshold = self.dynamic_base_price + self.config.price_gap_high
        alert_low_threshold = self.dynamic_base_price - self.config.price_gap_low
        
        # 处理价格上涨情况
        if price > alert_high_threshold:
            # 计算当前差值
            current_gap = price - self.dynamic_base_price
            # 如果当前差值大于目标差值，则调整基准价
            if current_gap > TARGET_GAP:
                # 计算需要调整的量
                adjustment = min(STEP_SIZE, current_gap - TARGET_GAP)
                # 更新基准价
                new_base_price = self.dynamic_base_price + adjustment
                self.update_default_gold_price(new_base_price)
                logger.info(f"渐进式上调基准价: {self.dynamic_base_price - adjustment:.2f} -> {new_base_price:.2f}，当前价格: {price:.2f}")
                return True  # 表示进行了调整
        
        # 处理价格下跌情况
        elif price < alert_low_threshold:
            # 计算当前差值
            current_gap = self.dynamic_base_price - price
            # 如果当前差值大于目标差值，则调整基准价
            if current_gap > TARGET_GAP:
                # 计算需要调整的量
                adjustment = min(STEP_SIZE, current_gap - TARGET_GAP)
                # 更新基准价
                new_base_price = self.dynamic_base_price - adjustment
                self.update_default_gold_price(new_base_price)
                logger.info(f"渐进式下调基准价: {self.dynamic_base_price + adjustment:.2f} -> {new_base_price:.2f}，当前价格: {price:.2f}")
                return True  # 表示进行了调整
        
        return False  # 表示未进行调整
    
    def send_price_alert(self, price, direction):
        """
        发送价格预警消息
        :param price: 当前价格
        :param direction: 价格变动方向 ("上涨" 或 "下跌")
        :return: 推送结果字典
        """
        # 检查全局推送限制
        if not self.can_send_global_push():
            logger.warning("为防止消息推送过于频繁，暂时跳过本次推送")
            return {'success': False, 'reason': '全局推送频率限制'}
        
        # 获取价格涨跌图标
        arrow = "(上涨)" if direction == "上涨" else "(下跌)"
        
        # 使用工具函数构建消息数据
        message_data = build_message_data(price, arrow, self, direction, push_type="alert")
        
        # 使用通用推送函数发送消息
        result = send_push_message(self.message_sender, message_data, push_type="alert")
        if result['success']:
            # 更新全局推送时间
            self.update_global_push_time()
            logger.info(f"价格预警消息已推送，价格: ¥{price:.2f}/克，方向: {direction}")
        return result
    
    def check_alert_conditions(self, price):
        """
        检查预警条件（使用固定阈值方式）
        当价格达到阈值时立即推送，不影响定时推送规则
        :param price: 当前黄金价格
        :return: 处理结果字典
        """
        try:
            # 验证价格数据类型
            float_price = float(price)
        except (ValueError, TypeError) as e:
            logger.error(f"价格数据格式无效: {price}", exc_info=True)
            return {'success': False, 'reason': '价格数据格式错误'}
        
        # 使用固定阈值方式
        alert_high_threshold = self.dynamic_base_price + self.config.price_gap_high  # 预警高价（人民币/克）
        alert_low_threshold = self.dynamic_base_price - self.config.price_gap_low   # 预警低价（人民币/克）
        
        logger.debug(f"检查预警条件 - 当前价格: {float_price:.2f}, 高价阈值: {alert_high_threshold:.2f}, 低价阈值: {alert_low_threshold:.2f}")
        
        # 获取当前时间戳
        current_time = time.time()
        
        # 高价预警
        if float_price >= alert_high_threshold and not self.alerted_high:
            # 无论推送是否成功，都先更新动态基准价
            self.update_default_gold_price(float_price)
            logger.info(f"高价预警触发，基础金价可变量已更新为: {float_price:.2f}")
            
            # 检查是否需要推送消息（推送次数未达到上限）
            if self.push_status_manager.push_count_high < MAX_PUSH_COUNT:
                # 防止推送过于接近的价格
                if abs(float_price - self.push_status_manager.last_alert_price_high) >= self.config.price_change_threshold:
                    result = self.send_price_alert(float_price, "上涨")
                    if result['success']:
                        # 更新预警推送状态
                        self.push_status_manager.reset_alert_push_status("上涨", float_price)
                else:
                    logger.debug(f"价格变化过小，不推送: {abs(float_price - self.push_status_manager.last_alert_price_high):.2f} < {self.config.price_change_threshold}")
            else:
                logger.warning(f"高价推送次数已达上限: {self.push_status_manager.push_count_high}/{MAX_PUSH_COUNT}")
            
            self.alerted_high = True
            return {'success': True, 'action': '设置高价预警状态'}
        
        # 低价预警
        elif float_price <= alert_low_threshold and not self.alerted_low:
            # 无论推送是否成功，都先更新动态基准价
            self.update_default_gold_price(float_price)
            logger.info(f"低价预警触发，基础金价可变量已更新为: {float_price:.2f}")
            
            # 检查是否需要推送消息（推送次数未达到上限）
            if self.push_status_manager.push_count_low < MAX_PUSH_COUNT:
                # 防止推送过于接近的价格
                if abs(float_price - self.push_status_manager.last_alert_price_low) >= self.config.price_change_threshold:
                    result = self.send_price_alert(float_price, "下跌")
                    if result['success']:
                        # 更新预警推送状态
                        self.push_status_manager.reset_alert_push_status("下跌", float_price)
                else:
                    logger.debug(f"价格变化过小，不推送: {abs(float_price - self.push_status_manager.last_alert_price_low):.2f} < {self.config.price_change_threshold}")
            else:
                logger.warning(f"低价推送次数已达上限: {self.push_status_manager.push_count_low}/{MAX_PUSH_COUNT}")
            
            self.alerted_low = True
            return {'success': True, 'action': '设置低价预警状态'}
        
        # 重置预警状态（允许反复触发）
        # 当价格回落到正常范围时，重置预警状态
        if self.alerted_high and float_price < (self.dynamic_base_price + self.config.price_gap_high) - self.config.price_gap_high * 0.8:
            self.alerted_high = False
            self.push_status_manager.push_count_high = 0  # 重置推送次数
            logger.info(f"高价预警状态重置，当前价格: {float_price:.2f}, 基准价格: {self.dynamic_base_price:.2f}")
            return {'success': True, 'action': '重置高价预警状态'}
        
        if self.alerted_low and float_price > (self.dynamic_base_price - self.config.price_gap_low) + self.config.price_gap_low * 0.8:
            self.alerted_low = False
            self.push_status_manager.push_count_low = 0  # 重置推送次数
            logger.info(f"低价预警状态重置，当前价格: {float_price:.2f}, 基准价格: {self.dynamic_base_price:.2f}")
            return {'success': True, 'action': '重置低价预警状态'}
        
        return {'success': True, 'action': '无预警动作'}
    


# 创建全局黄金预警管理器实例
gold_alert_manager = GoldAlert()
