# coding: utf-8
"""
工具函数模块
包含项目中使用的各种工具函数
"""

import time
import os
from datetime import datetime, timedelta
from logger_config import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 禁止运行文件路径
BLOCK_FILE_PATH = "./push_blocked.txt"


def is_push_blocked():
    """
    检查是否被禁止推送
    :return: bool 是否被禁止推送
    """
    if not os.path.exists(BLOCK_FILE_PATH):
        return False
    
    try:
        # 使用utf-8编码读取文件，处理Windows系统上的编码问题
        with open(BLOCK_FILE_PATH, 'r', encoding='utf-8') as f:
            blocked_date_str = f.read().strip()
        
        if not blocked_date_str:
            os.remove(BLOCK_FILE_PATH)
            return False
        
        blocked_date = datetime.strptime(blocked_date_str, "%Y-%m-%d")
        today = datetime.now().date()
        
        # 检查是否是当天的禁止记录
        if blocked_date.date() == today:
            logger.warning(f"当天已被禁止推送，禁止日期: {blocked_date_str}")
            return True
        else:
            # 过期记录，删除文件
            os.remove(BLOCK_FILE_PATH)
            return False
    except Exception as e:
        logger.error(f"检查禁止推送状态失败: {e}")
        # 出错时删除文件，避免无限禁止
        if os.path.exists(BLOCK_FILE_PATH):
            os.remove(BLOCK_FILE_PATH)
        return False

def set_push_blocked():
    """
    设置当天禁止推送
    """
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        # 使用utf-8编码写入文件，处理Windows系统上的编码问题
        with open(BLOCK_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(today_str)
        logger.error(f"已设置当天禁止推送: {today_str}")
    except Exception as e:
        logger.error(f"设置禁止推送状态失败: {e}")

class PushStatusManager:
    """
    推送状态管理器
    统一管理定期推送和预警推送的状态
    """
    def __init__(self):
        # 定期推送状态
        self.last_regular_push_time = 0  # 上次定期推送时间
        self.last_sent_price = 0  # 上次推送的价格，用于防止重复推送
        self.last_regular_push_minute = -1  # 上次推送的分钟，用于防止同一分钟内重复推送
        
        # 预警推送状态
        self.alerted_high = False  # 高价预警状态
        self.alerted_low = False  # 低价预警状态
        self.last_push_time_high = 0  # 上次高价推送时间
        self.last_push_time_low = 0  # 上次低价推送时间
        self.push_count_high = 0  # 高价推送次数
        self.push_count_low = 0  # 低价推送次数
        self.last_alert_price_high = 0  # 最近一次高价预警推送的价格
        self.last_alert_price_low = 0  # 最近一次低价预警推送的价格
        
        # 全局推送限制
        self.last_global_push_time = 0  # 上次全局推送时间
        
    def reset_regular_push_status(self, current_minute, current_price):
        """
        重置定期推送状态
        :param current_minute: 当前分钟
        :param current_price: 当前价格
        """
        self.last_regular_push_time = time.time()
        self.last_sent_price = current_price
        # 存储当前小时和分钟，格式为：小时*100 + 分钟（例如：10点01分存储为1001）
        # 这样可以判断当前小时是否已经推送过
        current_hour = time.localtime().tm_hour
        self.last_regular_push_minute = current_hour * 100 + current_minute
    
    def reset_alert_push_status(self, direction, price):
        """
        重置预警推送状态
        :param direction: 价格变动方向
        :param price: 当前价格
        """
        current_time = time.time()
        if direction == "上涨":
            self.last_push_time_high = current_time
            self.last_alert_price_high = price
            self.push_count_high += 1
        else:
            self.last_push_time_low = current_time
            self.last_alert_price_low = price
            self.push_count_low += 1
    
    def reset_daily_push_counts(self):
        """
        重置每日推送计数
        """
        self.push_count_high = 0
        self.push_count_low = 0
    
    def update_global_push_time(self):
        """
        更新全局推送时间
        """
        self.last_global_push_time = time.time()


def build_message_data(price, arrow, gold_alert_manager, direction=None, push_type="regular"):
    """
    构建微信模板消息的数据
    :param price: 当前黄金价格
    :param arrow: 价格变化箭头
    :param gold_alert_manager: 黄金预警管理器实例
    :param direction: 价格变动方向（可选，用于预警消息）
    :param push_type: 推送类型，"regular" 或 "alert"
    :return: 消息数据字典
    """
    # 获取当前时间，格式化为友好的显示格式
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # 构建消息数据 - 根据提供的模板格式
    message_data = {
        "type": {
            "value": "定时消息" if push_type == "regular" else "预警消息"
        },
        "price": {
            "value": f"¥{price:.2f}/克"
        },
        "trend": {
            "value": f"{arrow}"
        },
        "source": {
            "value": "新浪财经"
        },
        "base": {
            "value": f"={gold_alert_manager.config.default_gold_price}"
        },
        "high": {
            "value": f"+{gold_alert_manager.config.price_gap_high}"
        },
        "low": {
            "value": f"-{gold_alert_manager.config.price_gap_low}"
        },
        "dynamic_base": {
            "value": f"¥{gold_alert_manager.dynamic_base_price:.2f}/克"
        },
        "time": {
            "value": current_time
        }
    }
    
    # 如果是预警消息，添加颜色属性
    if direction:
        message_data["dynamic_base"]["color"] = "#FF0000" if direction == "上涨" else "#00FF00"
    
    return message_data


def send_push_message(message_sender, message_data, push_type="regular"):
    """
    发送推送消息的通用函数
    :param message_sender: 消息发送实例
    :param message_data: 消息数据字典
    :param push_type: 推送类型，"regular" 或 "alert"
    :return: 推送结果字典
    """
    try:
        result = message_sender.send_to_all_users(message_data)
        
        # 检查推送结果
        if result.get("status") == "skipped":
            logger.warning(f"{push_type}消息推送被跳过: {result.get('reason')}")
            return {'success': False, 'reason': result.get('reason'), 'result': result}
        elif result.get("status") == "failed":
            logger.error(f"{push_type}消息推送失败: {result.get('reason')}")
            # 设置当天禁止推送
            set_push_blocked()
            return {'success': False, 'reason': result.get('reason'), 'result': result}
        elif result.get("total", 0) > 0 and result.get("success", 0) == 0:
            logger.error(f"{push_type}消息推送失败: 所有用户发送失败")
            # 设置当天禁止推送
            set_push_blocked()
            return {'success': False, 'reason': '所有用户发送失败', 'result': result}
        elif result.get("error"):
            logger.error(f"{push_type}消息推送失败: {result.get('error')}")
            # 设置当天禁止推送
            set_push_blocked()
            return {'success': False, 'error': result.get('error'), 'result': result}
        
        # 推送成功
        if push_type == "regular":
            logger.info("定期价格更新消息已发送")
        else:
            logger.info("价格预警消息已推送")
        return {'success': True, 'result': result}
    except Exception as e:
        logger.error(f"发送{push_type}消息失败: {e}")
        # 设置当天禁止推送
        set_push_blocked()
        return {'success': False, 'error': str(e)}
