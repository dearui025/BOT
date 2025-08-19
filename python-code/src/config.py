"""
配置文件
包含所有配置参数和API密钥设置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 币安API配置
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', 'your_api_key_here')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'your_secret_key_here')
BINANCE_TESTNET = False  # 使用真实API获取真实数据

# WebSocket配置
WEBSOCKET_URL = 'wss://stream.binance.com:9443/ws'
REAL_WEBSOCKET_URL = 'wss://stream.binance.com:9443/ws'  # 真实WebSocket地址

# 交易配置
TRADING_PAIRS = ['BTCUSDT', 'ETHUSDT']  # 支持的交易对
DEFAULT_TRADING_PAIR = 'BTCUSDT'

# 资金管理
INITIAL_BALANCE = 10000.0   # 初始虚拟资金 (USDT) - 降低到更现实的数额
MAX_POSITION_SIZE = 0.5     # 最大仓位比例 (50%)
MIN_TRADE_AMOUNT = 10.0     # 最小交易金额 (USDT)

# 风险管理
STOP_LOSS_PCT = 2.0         # 止损百分比
TAKE_PROFIT_PCT = 5.0       # 止盈百分比
MAX_DAILY_TRADES = 50       # 每日最大交易次数
MAX_DAILY_LOSS_PCT = 10.0   # 每日最大亏损百分比

# 策略参数
STRATEGY_CONFIG = {
    'dual_ma': {
        'short_period': 10,     # 短期均线周期
        'long_period': 30,      # 长期均线周期
        'signal_threshold': 0.1  # 信号阈值
    },
    'rsi': {
        'period': 14,
        'overbought': 70,
        'oversold': 30
    },
    'macd': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9
    }
}

# 数据配置
KLINE_INTERVALS = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '1h': '1h',
    '4h': '4h',
    '1d': '1d'
}
DEFAULT_INTERVAL = '1m'
MAX_KLINE_LIMIT = 1000

# 更新间隔
UPDATE_INTERVAL = 2         # 数据更新间隔 (秒) - 避免过于频繁
STRATEGY_CHECK_INTERVAL = 5 # 策略检查间隔 (秒)

# 文件路径
DATA_DIR = 'data'
LOG_DIR = 'logs'
TRADE_LOG_FILE = f'{LOG_DIR}/trades.csv'
PERFORMANCE_LOG_FILE = f'{LOG_DIR}/performance.csv'

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 性能分析
BENCHMARK_SYMBOL = 'BTCUSDT'  # 基准对比标的
RISK_FREE_RATE = 0.02         # 无风险收益率

# API限制
API_RATE_LIMIT = 1200         # 每分钟API调用限制 (币安限制)
WEBSOCKET_RECONNECT_DELAY = 5 # WebSocket重连延迟

# 通知配置 (可选)
ENABLE_NOTIFICATIONS = False
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# 回测配置
BACKTEST_START_DATE = '2024-01-01'  # 更新到2024年
BACKTEST_END_DATE = '2024-12-31'
BACKTEST_COMMISSION = 0.001   # 手续费率
BACKTEST_SLIPPAGE = 0.0005    # 滑点

# 数据库配置 (可选)
DATABASE_URL = 'sqlite:///trading_bot.db'
ENABLE_DATABASE = False

# Web界面配置
WEB_HOST = '127.0.0.1'
WEB_PORT = 8501
ENABLE_WEB_UI = True

# 调试模式
DEBUG_MODE = True
ENABLE_PAPER_TRADING = True   # 启用模拟交易模式 (确保安全)

# 真实数据配置
USE_REAL_DATA = True          # 使用真实市场数据
REAL_TIME_UPDATE = True       # 启用实时数据更新
CACHE_DATA = True             # 缓存数据以提高性能