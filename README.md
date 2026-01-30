## 黄金价格监控系统
### 一、背景需求
    随着这两年黄金价格大涨，大家想实时关注金价但是有时又不能不方便实时查看手机或电脑，需要一个价格提醒的需求，虽然现有很多app提供价格提醒，但是可能我接触的少，发现很多软件都不是自己需要的，所以基于自己想法和需求想弄一个价格提醒系统。此程序适合做短线黄金交易。投资有风险，购买请谨慎！
### 二、技术实现
#### PS：作为一个白剽党而言想办法节省或者免费才是王道！哈
    服务器：本地运行或云服务器
    域名：（可选）
    开发语言：Python
    主力开发：AI
    消息推送：微信公众号（可申请微信公众平台的测试号-免费）

    整个程序都是基于半吊子全栈开发“AI”训练而来，历经15天左右，因为是业余时间所以比较长哈，现在基本完成也测试了一个月左右，肯定有不尽人意的地方，但是还算满意（声明：本人对于python是大白，所以介意者可忽略本文及代码，自行实现）
### 三、开发思路整理
    补充下一个重要说明，微信公众平台测试号有个坑，就是千万不要设置提醒过于频繁，每天最多100次左右吧，超过了他回缓存，递增给每天的配额，也就是说如果你一次性发1000条消息推送，那未来10天你都看不见新消息了，所以千万谨慎设置。
#### 功能特点
    
- 自动从新浪财经抓取实时黄金价格（每5分钟抓取一次）
- 可配置的价格预警阈值
- 通过微信公众号模板消息向用户发送价格提醒
- 支持价格涨跌预警功能
- 可配置推送间隔时间和推送次数
- 支持定时推送（每小时的01分和31分）
- 预警推送与定时推送互不影响（不太理想有bug）
- 动态更新基准价格（不太理想有bug）
- 增强的日志记录和监控
- 简单的缓存机制提高性能
- 支持缓存清除功能
- 支持生成HTML文件用于Web预览
- 支持生成windows桌面软件

#### 安装依赖

```bash
pip install -r requirements.txt
```

#### 配置说明

在 `config.py` 文件中配置以下信息：

##### 微信公众号配置
- `APP_ID`: 微信公众号 AppID
- `APP_SECRET`: 微信公众号 AppSecret
- `TEMPLATE_ID`: 微信模板消息 ID
- `WEB_URL`: 点击消息跳转的网址

##### 推送时间配置
- `PUSH_START_TIME`: 每天推送开始时间（24小时制）
- `PUSH_END_TIME`: 每天推送结束时间（24小时制）
- `PUSH_INTERVAL_MINUTES`: 推送间隔（分钟）
- `REGULAR_PUSH_MINUTES`: 定期推送的分钟点（每小时的01分和31分）
- `REGULAR_PUSH_WINDOW`: 定期推送的时间窗口（分钟）

##### 推送频率限制配置
- `MAX_PUSH_COUNT`: 每次触发推送的最大次数
- `BATCH_PUSH_INTERVAL`: 批量推送最小间隔（秒）
- `GLOBAL_PUSH_INTERVAL`: 全局推送最小间隔（秒）

##### 黄金价格配置
- `DATA_FETCH_INTERVAL`: 数据抓取间隔（秒）
- `PRICE_CACHE_EXPIRATION`: 价格缓存过期时间（秒）

##### 黄金价格预警配置
- `DEFAULT_GOLD_PRICE`: 默认黄金价格（人民币/克）
- `DEFAULT_PRICE_GAP_HIGH`: 默认价格上涨浮动差额（人民币/克）
- `DEFAULT_PRICE_GAP_LOW`: 默认价格下跌浮动差额（人民币/克）
- `PRICE_CHANGE_THRESHOLD`: 价格变化阈值（元），用于防止重复推送
- `BASE_PRICE_ADJUST_STEP`: 基准价格调整步长

##### 日志配置
- `LOG_LEVEL`: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- `LOG_FILE`: 日志文件路径

##### 测试模式配置
- `TEST_MODE`: 测试模式开关，设为 True 时启用测试模式，False 时启用正式模式

##### 生成HTML配置
- `GENERATE_TYPE`: 生成HTML文件配置
  - 0: 默认，不生成HTML文件
  - 1: 生成HTML文件
  - 2: 不生成HTML文件，编译Windows运行文件

#### 使用方法

##### 1. 运行监控程序

```bash
python main.py
```

程序将：
1. 持续监控黄金价格（每5分钟抓取一次）
2. 当价格达到预设阈值时立即发送预警消息
3. 在每天09:00-23:00期间的每小时01分和31分发送定期价格更新
4. 如果配置了 `GENERATE_TYPE=1`，会每5分钟生成一次HTML文件
5. 如果配置了 `GENERATE_TYPE=2`，会在启动时编译Windows运行文件

##### 2. 生成HTML文件

在 `config.py` 中设置 `GENERATE_TYPE=1`，然后运行 `main.py`，程序会在当前目录生成 `gold_price.html` 文件，可直接用浏览器打开查看实时黄金价格信息。

### 3. 编译Windows运行文件

在 `config.py` 中设置 `GENERATE_TYPE=2`，然后运行 `main.py`，程序会在 `dist` 目录生成可执行文件，可直接在Windows系统上运行，无需安装Python环境。

或者直接运行编译脚本：

```bash
python windows_compile.py -y
```

##### 4. 清除缓存

项目支持缓存清除功能，可通过以下方式使用：

###### 4.1 运行缓存清除脚本

```bash
python clear_cache.py
```

这将运行缓存清除演示脚本，展示缓存清除的功能和效果。

###### 4.2 在代码中使用缓存清除功能

```python
from data_source import price_cache

# 清除所有缓存
def clear_all_cache():
    price_cache.clear()
    print("所有缓存已清除")

# 清除指定键的缓存
def clear_specific_cache():
    price_cache.clear_key('gold_price')
    print("指定键的缓存已清除")
```

###### 4.3 缓存清除功能说明

- **`price_cache.clear()`**: 清除所有缓存数据，返回清除的记录数量
- **`price_cache.clear_key(key)`**: 清除指定键的缓存数据，返回清除结果

## 项目逻辑说明

##### 1. 项目推送开始和结束时间
- 由 `PUSH_START_TIME` 和 `PUSH_END_TIME` 配置项控制
- 默认为 09:00-23:00
- 在推送时间范围外，程序会等待并定期检查
- 生成HTML文件功能不受此限制

##### 2. 项目推送的时间
- 定时推送：每小时的01分和31分
- 预警推送：当价格达到阈值时立即推送
- 生成HTML文件：每5分钟生成一次

##### 3. 项目推送的次数限制
- 每个预警条件（高价或低价）最多推送 `MAX_PUSH_COUNT` 次
- 添加了全局推送限制，防止短时间内推送过多消息
- 生成HTML文件功能不受此限制

##### 4. 数据抓取逻辑
- 每5分钟抓取一次数据
- 持续监控价格变化
- 实现了简单的缓存机制以提高性能

##### 5. 预警推送规则
- 当价格达到 `默认黄金价格+上涨浮动差额` 或 `默认黄金价格-下跌浮动差额` 时立即推送
- 预警推送不影响定时推送的时间规则
- 预警后自动更新默认黄金价格为预警价格

#### 消息模板格式

为了确保消息能正确显示，微信模板消息应具有以下字段：

```
黄金价格
消息类型：{{type.DATA}}
当前价格：{{price.DATA}}
行情走势：{{trend.DATA}}
数据来源：{{source.DATA}}
基价：{{base.DATA}}
上浮价：{{high.DATA}}
下浮价：{{low.DATA}}
动态基准价：{{dynamic_base.DATA}}
推送时间：{{time.DATA}}
```

字段说明：
- `type`：消息类型（定时消息/预警消息）
- `price`：当前价格信息
- `trend`：价格趋势（上涨/下跌/持平）
- `source`：数据来源（新浪财经）
- `base`：基准价格
- `high`：上涨阈值
- `low`：下跌阈值
- `dynamic_base`：动态基准价格
- `time`：推送时间

#### 代码结构

- `access_token.py`: 微信 Access Token 管理
- `config.py`: 配置文件
- `data_source.py`: 黄金价格数据源模块（负责获取和处理黄金价格数据）
- `gold_alert.py`: 黄金价格预警模块（负责处理黄金价格预警逻辑）
- `generate_html.py`: 生成HTML文件功能（负责生成黄金价格监控HTML文件）
- `logger_config.py`: 日志配置模块
- `main.py`: 主程序（黄金价格监控主循环）
- `message.py`: 微信消息发送功能（负责发送模板消息）
- `utils.py`: 工具函数（包含各种辅助函数）
- `windows_compile.py`: Windows可执行文件编译功能
- `templates/`: HTML模板目录
- `gold_price_template.html`: 黄金价格监控HTML模板

#### 部署到宝塔面板

1. 在宝塔面板中创建新的Python项目
2. 上传所有代码文件到项目目录
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 安装Playwright浏览器驱动：
   ```bash
   playwright install chromium
   ```
5. 配置环境变量和定时任务（根据需要）
6. 启动项目并设置开机自启

## 注意事项

- 需要安装 Playwright 并下载浏览器驱动：
  ```bash
  playwright install chromium
  ```
- 确保网络连接正常
- 避免过于频繁的请求导致被反爬虫机制拦截
- 微信公众号需通过认证并开启相关接口权限
- 生成的HTML文件可直接用浏览器打开查看
- 编译的Windows可执行文件会保存在 `dist` 目录
- 
#### 项目结构

```
.
├── README.md                  # 项目说明文档
├── access_token.py           # 微信 Access Token 管理
├── config.py                 # 配置文件
├── data_source.py            # 黄金价格数据源模块
├── gold_alert.py             # 黄金价格预警模块
├── generate_html.py          # 生成HTML文件功能
├── logger_config.py          # 日志配置模块
├── main.py                   # 主程序
├── message.py                # 微信消息发送功能
├── utils.py                  # 工具函数
├── windows_compile.py        # Windows可执行文件编译功能
├── requirements.txt          # 项目依赖列表
├── templates/                # HTML模板目录
│   └── gold_price_template.html  # 黄金价格监控HTML模板
└── 部署到宝塔面板.md          # 宝塔面板部署指南
```

#### 常见问题

##### 1. 为什么无法获取黄金价格？

- 检查网络连接是否正常
- 检查Playwright是否正确安装
- 检查新浪财经网站是否可以正常访问

##### 2. 为什么没有发送微信消息？

- 检查微信公众号配置是否正确
- 检查是否在推送时间范围内
- 检查是否被禁止推送（查看 `push_blocked.txt` 文件）
- 检查微信公众号是否已认证并开启相关接口权限

##### 3. 如何修改推送时间？

在 `config.py` 文件中修改 `PUSH_START_TIME` 和 `PUSH_END_TIME` 配置项。

##### 4. 如何修改预警阈值？

在 `config.py` 文件中修改 `DEFAULT_PRICE_GAP_HIGH` 和 `DEFAULT_PRICE_GAP_LOW` 配置项。

##### 5. 如何生成HTML文件？

在 `config.py` 文件中设置 `GENERATE_TYPE=1`，然后运行 `main.py`。

### 6. 如何编译Windows运行文件？

在 `config.py` 文件中设置 `GENERATE_TYPE=2`，然后运行 `main.py`，或者直接运行 `python windows_compile.py -y`。

#### 错误处理机制

此项目已优化，在出现错误时会停止生成HTML和可执行文件，并结束程序运行。

- 当无法获取金价数据时，程序会停止运行
- 当推送被禁止时，程序会停止运行
- 当HTML生成失败时，程序会停止运行
- 当Windows编译失败时，程序会停止运行
- 当遇到严重异常时，程序会停止运行

#### 技术栈

- Python 3.8+
- Playwright（用于抓取黄金价格）
- Requests（用于HTTP请求）
- PyInstaller（用于编译Windows可执行文件）

### 许可证

MIT License

### 贡献

欢迎提交Issue和Pull Request。