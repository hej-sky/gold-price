# coding: utf-8
"""
黄金价格数据源模块
负责获取和处理黄金价格数据
"""

import time
import requests
from logger_config import get_logger
from playwright.sync_api import sync_playwright
from config import PRICE_CACHE_EXPIRATION

# 获取日志记录器
logger = get_logger(__name__)

# 备选数据源配置
GOLD_PRICE_SOURCES = [
    {
        "name": "新浪财经-黄金频道",
        "url": "https://finance.sina.com.cn/nmetal/",
        "method": "playwright"
    },
    {
        "name": "新浪财经-黄金期货",
        "url": "https://finance.sina.com.cn/futures/quotes/XAU.shtml",
        "method": "playwright"
    },
    {
        "name": "新浪财经-API",
        "url": "https://hq.sinajs.cn/list=njs_gold",
        "method": "api"
    }
]

# 时间变量
TIMEOUT = 10  # 通用超时时间（秒）
RETRY_COUNT = 3  # 重试次数
RETRY_INTERVAL = 2  # 重试间隔（秒）

# 缓存机制
class PriceCache:
    """
    价格缓存类，管理价格数据的缓存
    用于减少重复的网络请求，提高性能
    """
    def __init__(self, expiration=PRICE_CACHE_EXPIRATION):
        self._cache = {}  # 缓存字典
        self._expiration = expiration  # 缓存过期时间（秒）
        
    def get(self, key):
        """
        获取缓存数据，如果过期则返回None
        :param key: 缓存键
        :return: 缓存值或None
        """
        if key in self._cache:
            cached_data = self._cache[key]
            if time.time() < cached_data['expires_at']:
                return cached_data['value']
            else:
                # 缓存已过期，删除它
                del self._cache[key]
        return None
        
    def set(self, key, value):
        """
        设置缓存数据
        :param key: 缓存键
        :param value: 缓存值
        """
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + self._expiration
        }
        
    def clear(self):
        """
        清除所有缓存数据
        """
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"缓存已全部清除，共清除 {cache_size} 条记录")
        
    def clear_key(self, key):
        """
        清除指定键的缓存数据
        :param key: 缓存键
        """
        if key in self._cache:
            del self._cache[key]
            logger.info(f"已清除缓存键: {key}")
            return True
        return False
        


# 创建价格缓存实例
price_cache = PriceCache()  # 使用配置文件中的缓存过期时间



def get_gold_price_from_sina_page_playwright(url):
    """
    使用 Playwright 从新浪财经页面获取黄金价格
    :param url: 数据源URL
    :return: 价格数据字典或None
    """
    browser = None
    page = None
    try:
        with sync_playwright() as p:
            # 启动浏览器 (增加超时时间)
            browser = p.chromium.launch(headless=True, timeout=15000)
            page = browser.new_page()

            # 设置用户代理
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            })

            # 访问页面 (增加超时时间)
            page.goto(url, timeout=20000)

            # 等待元素出现 (增加超时时间)
            page.wait_for_selector("#realtimeGC", timeout=20000)

            # 获取价格链接元素，通过CSS选择器精确定位
            price_link_element = page.locator("#realtimeGC > .r_g_price_c_r > a")

            # 获取人民币价格
            price_text = price_link_element.locator(".r_g_price_now").text_content(timeout=10000)
            # 获取价格变化
            price_change_text = price_link_element.locator(".r_g_price_change").text_content(timeout=10000)

            # 解析价格文本
            if price_text:
                # 移除可能的空格和换行符
                price_text = price_text.strip()
                try:
                    price = float(price_text)
                    if price <= 0:
                        logger.error("Playwright获取页面价格数据异常，获取到的价格为0或负数")
                        return None

                    # 返回包含所有价格相关信息的对象
                    result = {
                        "price": price,
                        "change": price_change_text.strip() if price_change_text else "",
                        "timestamp": int(time.time()),
                        "readable_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    }
                    return result
                except ValueError as e:
                    logger.error(f"价格文本转换为数字失败: {e}, 原始文本: {price_text}")
                    return None
            else:
                logger.error("无法解析页面价格数据（Playwright方式），未找到有效价格文本")
                return None

    except Exception as e:
        logger.error(f"使用Playwright抓取页面失败: {e}")
        return None
    finally:
        # 确保浏览器和页面总是被关闭
        # 注意：在 with sync_playwright() 上下文内，Playwright 会自动关闭资源
        # 这里的关闭操作可能会因为事件循环已关闭而失败，所以添加 try-except
        if page:
            try:
                page.close()
            except Exception as e:
                logger.debug(f"关闭页面失败（可能是因为事件循环已关闭）: {e}")
        if browser:
            try:
                browser.close()
            except Exception as e:
                logger.debug(f"关闭浏览器失败（可能是因为事件循环已关闭）: {e}")


def get_gold_price_from_api(url):
    """
    使用API方式获取黄金价格（更轻量级，速度更快）
    :param url: API数据源URL
    :return: 价格数据字典或None
    """
    try:
        # 发送HTTP请求获取数据
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()  # 检查HTTP状态码
        
        # 解析新浪财经API返回的数据
        # 新浪财经API返回格式：var hq_str_njs_gold="黄金T+D,453.50,453.50,453.50,453.50,0.00,0.00,09:29:59,2023-12-01";
        data = response.text.strip()
        if data and "=" in data and "\"" in data:
            # 提取引号内的数据部分
            data_part = data.split("=")[1].strip().strip("\"")
            # 分割数据字段
            fields = data_part.split(",")
            if len(fields) >= 8:
                # 新浪财经API数据格式：产品名称,最新价,开盘价,最高价,最低价,涨跌额,涨跌幅,时间,日期
                price_str = fields[1].strip()
                try:
                    price = float(price_str)
                    if price <= 0:
                        logger.error(f"API获取价格数据异常，获取到的价格为0或负数: {price}")
                        return None
                    
                    # 返回包含所有价格相关信息的对象
                    result = {
                        "price": price,
                        "change": fields[5].strip() if len(fields) > 5 else "",
                        "timestamp": int(time.time()),
                        "readable_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    }
                    return result
                except ValueError as e:
                    logger.error(f"API价格文本转换为数字失败: {e}, 原始文本: {price_str}")
                    return None
            else:
                logger.error(f"API返回数据格式异常，字段数量不足: {fields}")
                return None
        else:
            logger.error(f"API返回数据格式异常，无法解析: {data}")
            return None
    except Exception as e:
        logger.error(f"使用API获取数据失败: {e}")
        return None


def get_gold_price():
    """
    获取黄金价格的主函数，尝试多个数据源
    使用缓存机制以提高性能
    :return: 黄金价格（元/克）或None
    """
    # 检查缓存
    cached_price = price_cache.get('gold_price')
    if cached_price is not None:
        logger.info("使用缓存的金价数据")
        return cached_price
    
    # 遍历所有备选数据源
    for source in GOLD_PRICE_SOURCES:
        source_name = source["name"]
        source_url = source["url"]
        source_method = source["method"]
        
        logger.info(f"尝试从 {source_name} 获取黄金价格")
        
        # 根据数据源类型选择不同的获取方式
        for retry in range(RETRY_COUNT):
            try:
                if source_method == "api":
                    # 使用API方式获取数据（更轻量级）
                    price_data = get_gold_price_from_api(source_url)
                else:
                    # 使用Playwright方式获取数据
                    price_data = get_gold_price_from_sina_page_playwright(source_url)
                
                if price_data is not None:
                    # 更新缓存
                    price_cache.set('gold_price', price_data["price"])
                    logger.info(f"成功获取黄金价格: ¥{price_data['price']}/克")
                    return price_data["price"]
                else:
                    logger.warning(f"从 {source_name} 获取数据失败，第 {retry + 1} 次尝试")
                    if retry < RETRY_COUNT - 1:
                        time.sleep(RETRY_INTERVAL)
            except Exception as e:
                logger.error(f"从 {source_name} 获取数据时发生异常: {e}, 第 {retry + 1} 次尝试")
                if retry < RETRY_COUNT - 1:
                    time.sleep(RETRY_INTERVAL)

    # 所有方案都失败
    logger.error("所有数据源获取失败，无法获取黄金价格")
    return None


def display_price_info(price, last_price=None):
    """
    显示价格信息和涨跌情况
    """
    # 获取价格涨跌箭头
    arrow, direction = get_price_arrow(price, last_price)

    # 获取当前时间
    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    return arrow, direction


def get_price_arrow(price, last_price):
    """
    根据当前价格与基准价格比较，判断价格上涨或下跌
    返回相应的箭头符号和描述文字
    """
    # 如果没有上一次价格记录，则认为是持平
    if last_price is None:
        return "(持平)", "持平"

    # 判断涨跌
    if price > last_price:
        return "(上涨)", "上涨"
    elif price < last_price:
        return "(下跌)", "下跌"
    else:
        return "(持平)", "持平"