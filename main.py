import time
from datetime import datetime, time as dt_time

# 导入配置文件
from config import PUSH_START_TIME, PUSH_END_TIME, REGULAR_PUSH_MINUTES, REGULAR_PUSH_WINDOW, DATA_FETCH_INTERVAL
# 延迟导入TEST_MODE，需要时重新导入
import importlib
import config
# 导入数据获取和处理模块
from data_source import get_gold_price, display_price_info
# 导入黄金预警管理器
from gold_alert import gold_alert_manager
# 导入消息发送模块
from message import MessageSender
# 导入日志配置
from logger_config import get_logger
# 导入工具函数
from utils import build_message_data, send_push_message, is_push_blocked

# 获取日志记录器
logger = get_logger(__name__)

# 全局变量
last_price = None  # 记录上一次的价格，用于比较价格变化
first_run = True  # 标记是否为首次运行

# 消息发送实例 - 延迟初始化，在run_gold_price_monitor函数中创建
message_sender = None



def is_within_push_time():
    """
    检查当前时间是否在推送时间范围内（工作日）
    :return: bool 是否在推送时间范围内
    """
    # 获取当前日期和时间
    current_datetime = datetime.now()
    now = current_datetime.time()
    weekday = current_datetime.weekday()  # 获取星期几，0=周一，4=周五，5=周六，6=周日
    
    # 检查是否为工作日（周一到周五）
    if weekday > 4:  # 周六或周日
        logger.debug(f"当前为非工作日（{weekday}），跳过推送")
        return False
    
    # 如果是测试模式，记录日志但不忽略时间限制
    if config.TEST_MODE:
        logger.info("[测试模式] 按照正常时间范围进行推送")
    
    start_time = dt_time.fromisoformat(PUSH_START_TIME)
    end_time = dt_time.fromisoformat(PUSH_END_TIME)
    
    # 处理跨日期的情况（例如：22:00 到 06:00）
    if start_time <= end_time:
        # 不跨日期，正常区间判断
        return start_time <= now <= end_time
    else:
        # 跨日期，例如 22:00 到 06:00
        return now >= start_time or now <= end_time



def is_push_minute():
    """
    检查当前时间是否应该进行定期推送
    逻辑：
    1. 检查当前时间是否在配置的推送分钟点的时间窗口内
    2. 确保每个推送周期只推送一次
    :return: bool 是否为推送分钟
    """
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    # 获取上次推送的状态
    last_push_status = gold_alert_manager.push_status_manager.last_regular_push_minute
    
    # 解析上次推送的小时和分钟
    if last_push_status > 100:
        last_push_hour = last_push_status // 100
        last_push_min = last_push_status % 100
    else:
        # 兼容旧格式
        last_push_hour = -1
        last_push_min = last_push_status
    
    # 检查当前推送周期是否已经推送过
    # 推送周期是指：当前小时的当前分钟（测试模式下）或配置的推送分钟点（正式模式下）
    if config.TEST_MODE:
        # 测试模式下，每个小时只推送一次
        current_push_cycle = current_hour
        last_push_cycle = last_push_hour
        logger.info("[测试模式] 忽略推送分钟限制，允许随时推送，但每个小时只推送一次")
    else:
        # 正式模式下，检查当前时间是否在配置的推送分钟点的时间窗口内
        # 计算当前应该推送的分钟点
        should_push = False
        target_minute = None
        
        for push_min in REGULAR_PUSH_MINUTES:
            # 计算推送窗口的开始和结束时间
            window_start = push_min
            window_end = push_min + REGULAR_PUSH_WINDOW
            
            # 检查当前分钟是否在推送窗口内
            if window_start <= current_minute <= window_end:
                should_push = True
                target_minute = push_min
                break
        
        if not should_push:
            return False
        
        # 正式模式下，推送周期是当前小时的当前推送分钟点
        current_push_cycle = current_hour * 100 + target_minute
        last_push_cycle = last_push_hour * 100 + last_push_min if last_push_hour != -1 else -1
    
    # 如果当前推送周期已经推送过，直接返回False
    if current_push_cycle == last_push_cycle:
        logger.debug(f"当前推送周期 {current_push_cycle} 已经推送过，跳过本次推送")
        return False
    
    # 当前时间符合推送条件，允许推送
    return True



def send_regular_price_update(price, arrow):
    """
    发送定期价格更新消息
    :param price: 当前价格
    :param arrow: 价格变化箭头
    """
    # 使用工具函数构建消息数据
    message_data = build_message_data(price, arrow, gold_alert_manager, push_type="regular")
    
    # 使用通用推送函数发送消息
    result = send_push_message(message_sender, message_data, push_type="regular")
    return result['success']



def run_gold_price_monitor():
    """
    运行黄金价格监控循环
    根据需求调整逻辑：
    1. 每5分钟抓取一次黄金价格数据
    2. 在指定时间点（每小时01分和31分）进行定期推送
    3. 当价格达到预警阈值时立即推送（不影响定时推送规则）
    4. 生成HTML文件用于Web预览（根据配置）
    5. 编译Windows运行文件（根据配置）
    """
    # 声明全局变量
    global last_price, message_sender, first_run
    
    # 初始化消息发送实例
    if message_sender is None:
        message_sender = MessageSender()
    
    # 编译Windows运行文件（根据配置，只执行一次）
    import config
    if config.GENERATE_TYPE == 2:
        logger.info("开始编译Windows运行文件...")
        from windows_compile import WindowsCompiler
        compiler = WindowsCompiler()
        if compiler.compile(onefile=True, console=True):
            logger.info("Windows运行文件编译成功")
        else:
            logger.error("Windows运行文件编译失败")
            logger.error("编译失败，程序将停止运行")
            return  # 编译失败，停止程序运行
    
    # 主循环
    while True:
        try:
            # 检查是否被禁止推送
            if is_push_blocked():
                logger.error("当天已被禁止推送，程序将停止运行")
                return  # 被禁止推送，停止程序运行
            
            # 1. 获取当前金价
            price = get_gold_price()

            if price is not None:
                # 2. 显示价格信息并获取价格变化趋势
                arrow, direction = display_price_info(price, last_price)
                
                # 3. 记录当前价格用于下次比较
                last_price = price
                
                # 4. 获取当前时间信息
                now = datetime.now()
                current_minute = now.minute
                
                # 5. 保存原始的dynamic_base_price，用于HTML生成
                # 这样可以在预警触发时正确显示预警信息
                original_base_price = gold_alert_manager.dynamic_base_price
                
                # 6. 检查预警条件（立即推送）
                # 这会更新dynamic_base_price
                within_push_time = is_within_push_time()
                if not is_push_blocked() and within_push_time:
                    alert_result = gold_alert_manager.check_alert_conditions(price)
                
                # 7. 生成HTML文件（根据配置，不受时间范围和微信推送逻辑影响）
                import config
                if config.GENERATE_TYPE == 1:
                    from generate_html import HTMLGenerator
                    html_generator = HTMLGenerator()
                    
                    # 生成HTML时使用原始的base_price，这样可以显示预警信息
                    html_data = {
                        'current_price': price,
                        'last_price': last_price,
                        'base_price': original_base_price
                    }
                    html_path = html_generator.generate_html(html_data)
                    if html_path:
                        logger.info(f"成功生成HTML文件: {html_path}")
                    else:
                        logger.error("生成HTML文件失败")
                        logger.error("HTML生成失败，程序将停止运行")
                        return  # HTML生成失败，停止程序运行

                # 8. 检查是否需要进行定期推送
                if within_push_time:
                    # 检查当前是否为推送分钟
                    if is_push_minute():
                        # 发送定期价格更新
                        if send_regular_price_update(price, arrow):
                            # 更新推送状态
                            gold_alert_manager.push_status_manager.reset_regular_push_status(current_minute, price)
                            logger.info(f"定期推送完成，重置推送状态: 分钟={current_minute}")
                        else:
                            # 如果定期推送失败，可能表示推送服务出现问题
                            logger.warning("定期推送失败，检查是否被禁止推送")
                            if is_push_blocked():
                                logger.error("当天已被禁止推送，程序将停止运行")
                                return  # 被禁止推送，停止程序运行
                
                # 9. 每5分钟抓取一次数据
                time.sleep(DATA_FETCH_INTERVAL)
            else:
                # 10. 无法获取金价数据时的处理
                logger.error(f"无法获取金价数据，程序将停止运行")
                return  # 无法获取价格数据，停止程序运行

        except KeyboardInterrupt:
            # 9. 处理用户中断
            logger.info("程序已退出")
            break
        except Exception as e:
            # 10. 处理其他异常
            logger.error(f"程序运行异常: {e}", exc_info=True)  # 记录完整的异常信息
            # 检查是否被禁止推送
            if is_push_blocked():
                logger.error("当天已被禁止推送，程序将停止运行")
                return
            time.sleep(10)  # 短暂休眠后重试


if __name__ == "__main__":
    run_gold_price_monitor()