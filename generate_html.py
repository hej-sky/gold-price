# 生成黄金价格监控HTML文件
import os
import sys
from datetime import datetime

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_GOLD_PRICE, DEFAULT_PRICE_GAP_HIGH, DEFAULT_PRICE_GAP_LOW

class HTMLGenerator:
    """
    黄金价格HTML生成器
    """
    def __init__(self):
        self.template_path = os.path.join(os.path.dirname(__file__), 'templates', 'gold_price_template.html')
        self.output_path = os.path.join(os.path.dirname(__file__), 'index.html')
        
    def generate_html(self, price_data):
        """
        生成HTML文件
        :param price_data: 包含价格信息的字典
        :return: str 生成的HTML文件路径
        """
        try:
            # 读取模板文件
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # 准备模板数据
            template_data = self._prepare_template_data(price_data)
            
            # 替换模板变量
            html_content = template
            for key, value in template_data.items():
                placeholder = f"{{{{ {key} }}}}"
                html_content = html_content.replace(placeholder, str(value))
            
            # 写入HTML文件
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return self.output_path
        except Exception as e:
            print(f"生成HTML文件失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    def _prepare_template_data(self, price_data):
        """
        准备模板数据
        :param price_data: 包含价格信息的字典
        :return: dict 模板数据
        """
        # 获取当前价格
        current_price = price_data.get('current_price', DEFAULT_GOLD_PRICE)
        base_price = price_data.get('base_price', DEFAULT_GOLD_PRICE)
        
        # 计算预警阈值
        high_threshold = base_price + DEFAULT_PRICE_GAP_HIGH
        low_threshold = base_price - DEFAULT_PRICE_GAP_LOW
        
        # 计算价格趋势
        trend_text = "价格稳定"
        trend_arrow = "→"
        trend_class = "trend-stable"
        
        if 'last_price' in price_data and price_data['last_price'] is not None:
            price_diff = current_price - price_data['last_price']
            if price_diff > 0:
                trend_text = f"上涨 {abs(price_diff):.2f} 元"
                trend_arrow = "↑"
                trend_class = "trend-up"
            elif price_diff < 0:
                trend_text = f"下跌 {abs(price_diff):.2f} 元"
                trend_arrow = "↓"
                trend_class = "trend-down"
        
        # 准备预警信息
        alerts = []
        if current_price >= high_threshold:
            alerts.append({
                'class': 'alert-high',
                'title': '高价预警',
                'description': f'当前黄金价格 ¥{current_price:.2f}/克 已超过预警阈值 ¥{high_threshold:.2f}/克'
            })
        if current_price <= low_threshold:
            alerts.append({
                'class': 'alert-low',
                'title': '低价预警',
                'description': f'当前黄金价格 ¥{current_price:.2f}/克 已低于预警阈值 ¥{low_threshold:.2f}/克'
            })
        
        # 处理预警信息，生成HTML字符串
        alerts_html = ""
        if alerts:
            for alert in alerts:
                alerts_html += f"<div class='alert-item {alert['class']}'>"
                alerts_html += f"<div class='alert-title'>{alert['title']}</div>"
                alerts_html += f"<div class='alert-desc'>{alert['description']}</div>"
                alerts_html += "</div>"
        else:
            alerts_html = "<div class='alert-item'><div class='alert-title'>暂无预警</div><div class='alert-desc'>当前黄金价格处于正常波动范围</div></div>"
        
        # 模板数据
        return {
            'update_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'current_price': f"{current_price:.2f}",
            'base_price': f"{base_price:.2f}",
            'high_threshold': f"{high_threshold:.2f}",
            'low_threshold': f"{low_threshold:.2f}",
            'trend_text': trend_text,
            'trend_arrow': trend_arrow,
            'trend_class': trend_class,
            'data_source': '新浪财经',
            'current_year': datetime.now().year,
            'alerts': alerts_html
        }

