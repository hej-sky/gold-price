import requests
import json
import time
from logger_config import get_logger
from access_token import AccessToken
from config import TEMPLATE_ID, WEB_URL

# 获取日志记录器
logger = get_logger(__name__)


class MessageSender(AccessToken):
    """定义发送消息的类"""
    
    def __init__(self):
        super().__init__()
        self.opend_ids = []  # 初始化为空列表
        self.last_batch_push_time = 0  # 上次批量推送时间
        self.BATCH_PUSH_INTERVAL = 300  # 批量推送最小间隔（秒）

    def can_send_batch_push(self):
        """
        检查是否可以进行批量推送（防止短时间内推送过多）
        :return: bool 是否可以推送
        """
        current_time = time.time()
        if current_time - self.last_batch_push_time >= self.BATCH_PUSH_INTERVAL:
            return True
        return False

    def update_batch_push_time(self):
        """
        更新批量推送时间
        """
        self.last_batch_push_time = time.time()

    def get_openid(self):
        """
        获取所有用户的openid
        :return: openid列表或带有错误信息的字典
        """
        token = self.get_access_token()  # 确保token有效
        if not token:
            logger.error("Access Token无效，无法获取用户openid")
            return {"error": "Access Token无效", "errcode": "invalid_token"}

        next_openid = ''
        url_openid = 'https://api.weixin.qq.com/cgi-bin/user/get?access_token=%s&next_openid=%s' % (
            token, next_openid)
        try:
            response = requests.get(url_openid, timeout=10)
            response.raise_for_status()  # 检查HTTP状态码
            result = response.json()
            
            # 检查微信API返回的错误码
            if result.get("errcode", 0) != 0:
                logger.error(f"获取openid失败: {result}")
                return {"error": "微信API返回错误", "wechat_result": result, "errcode": result.get("errcode")}
            
            if 'data' in result:
                if 'openid' in result['data']:
                    open_ids = result['data']['openid']
                    logger.info(f"成功获取到 {len(open_ids)} 个用户openid")
                    return open_ids
                else:
                    # 没有用户关注公众号
                    logger.info("当前没有用户关注公众号")
                    return []
            else:
                logger.error(f"获取openid失败: {result}")
                return {"error": "获取openid失败", "wechat_result": result}
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求异常: {e}")
            return {"error": f"HTTP请求异常: {e}"}
        except ValueError as e:
            logger.error(f"响应解析异常: {e}")
            return {"error": f"响应解析异常: {e}"}
        except Exception as e:
            logger.error(f"获取openid发生未知异常: {e}")
            return {"error": f"未知异常: {e}"}

    def send_template_message(self, open_id, data):
        """
        发送模板消息给指定用户
        :param open_id: 用户的openid
        :param data: 消息数据
        :return: 发送结果字典
        """
        token = self.get_access_token()  # 确保token有效
        if not token:
            return {"error": "Access Token无效"}

        url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(token)

        post_data = {
            "touser": open_id,
            "template_id": TEMPLATE_ID,
            "url": WEB_URL,
            "topcolor": "#FF0000",
            "data": data
        }

        try:
            # 直接使用json参数，让requests库处理编码
            response = requests.post(url, json=post_data, timeout=10)
            response.raise_for_status()  # 检查HTTP状态码
            result = response.json()
            
            # 检查微信API返回的错误码
            if result.get("errcode", -1) != 0:
                logger.error(f"微信API消息发送失败: {result}")
                return {"error": "微信API返回错误", "wechat_result": result}
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求异常: {e}")
            return {"error": f"HTTP请求异常: {e}"}
        except ValueError as e:
            logger.error(f"响应解析异常: {e}")
            return {"error": f"响应解析异常: {e}"}
        except Exception as e:
            logger.error(f"发送模板消息发生未知异常: {e}")
            return {"error": f"未知异常: {e}"}

    def send_to_all_users(self, msg):
        """
        给所有用户发送消息
        :param msg: 要发送的消息数据
        :return: 推送结果字典
        """
        # 检查批量推送限制
        if not self.can_send_batch_push():
            logger.warning("为防止消息推送过于频繁，暂时跳过本次批量推送")
            return {"status": "skipped", "reason": "推送过于频繁"}
            
        # 获取用户列表
        open_ids = self.get_openid()
        
        # 检查是否获取openid失败
        if isinstance(open_ids, dict) and open_ids.get("error"):
            logger.error(f"获取openid失败，停止推送: {open_ids}")
            return {"status": "failed", "reason": "获取openid失败", "error": open_ids}
            
        self.opend_ids = open_ids  # 保存到实例变量供后续使用

        if not open_ids:
            logger.info("当前没有用户关注该公众号")
            return {"status": "completed", "total": 0, "success": 0, "failed": 0}

        success_count = 0
        fail_count = 0
        
        logger.info(f"开始向 {len(open_ids)} 个用户发送消息")
        
        # 给每个用户发送消息
        for open_id in open_ids:
            result = self.send_template_message(open_id, msg)
            if "error" not in result and result.get("errcode", -1) == 0:
                success_count += 1
            else:
                logger.error(f"消息发送失败: 用户 {open_id}, 结果: {result}")
                fail_count += 1
                
        # 无论成功失败都记录推送统计
        logger.info(f"批量推送完成: 总计 {len(open_ids)} 个, 成功 {success_count} 个, 失败 {fail_count} 个")
            
        # 更新批量推送时间
        self.update_batch_push_time()
        
        return {"status": "completed", "total": len(open_ids), "success": success_count, "failed": fail_count}