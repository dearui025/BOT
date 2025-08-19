"""
日志配置模块
统一管理所有日志记录功能
"""
import logging
import logging.handlers
import os
from datetime import datetime
import colorlog
from config import LOG_LEVEL, LOG_FORMAT, LOG_DIR

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str, level: str = LOG_LEVEL) -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # 清除已有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 控制台处理器 (彩色输出)
    console_handler = colorlog.StreamHandler()
    console_format = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件处理器
    today = datetime.now().strftime('%Y%m%d')
    file_handler = logging.handlers.RotatingFileHandler(
        f'{LOG_DIR}/{name}_{today}.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_format = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # 错误日志单独记录
    if level in ['ERROR', 'CRITICAL']:
        error_handler = logging.handlers.RotatingFileHandler(
            f'{LOG_DIR}/error_{today}.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        logger.addHandler(error_handler)
    
    return logger

# 创建各模块的日志记录器
trading_logger = setup_logger('trading')
data_logger = setup_logger('data')
strategy_logger = setup_logger('strategy')
performance_logger = setup_logger('performance')
system_logger = setup_logger('system')

class TradingLogger:
    """交易日志管理器"""
    
    def __init__(self):
        self.logger = trading_logger
        self.trade_file = f'{LOG_DIR}/trades_{datetime.now().strftime("%Y%m%d")}.csv'
        self._init_trade_log()
    
    def _init_trade_log(self):
        """初始化交易记录文件"""
        if not os.path.exists(self.trade_file):
            with open(self.trade_file, 'w', encoding='utf-8') as f:
                f.write('timestamp,symbol,side,price,quantity,total,fee,strategy,status,pnl\n')
    
    def log_trade(self, trade_data: dict):
        """记录交易信息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 写入CSV文件
        with open(self.trade_file, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp},{trade_data.get('symbol', '')},{trade_data.get('side', '')},"
                   f"{trade_data.get('price', 0)},{trade_data.get('quantity', 0)},"
                   f"{trade_data.get('total', 0)},{trade_data.get('fee', 0)},"
                   f"{trade_data.get('strategy', '')},{trade_data.get('status', '')},"
                   f"{trade_data.get('pnl', 0)}\n")
        
        # 记录到日志
        self.logger.info(f"交易记录: {trade_data}")
    
    def log_signal(self, signal_data: dict):
        """记录交易信号"""
        self.logger.info(f"交易信号: {signal_data}")
    
    def log_error(self, error_msg: str, exception: Exception = None):
        """记录错误信息"""
        if exception:
            self.logger.error(f"{error_msg}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(error_msg)

class PerformanceLogger:
    """性能日志管理器"""
    
    def __init__(self):
        self.logger = performance_logger
        self.performance_file = f'{LOG_DIR}/performance_{datetime.now().strftime("%Y%m%d")}.csv'
        self._init_performance_log()
    
    def _init_performance_log(self):
        """初始化性能记录文件"""
        if not os.path.exists(self.performance_file):
            with open(self.performance_file, 'w', encoding='utf-8') as f:
                f.write('timestamp,total_value,available_balance,position_value,unrealized_pnl,'
                       'realized_pnl,total_pnl,win_rate,max_drawdown,sharpe_ratio\n')
    
    def log_performance(self, performance_data: dict):
        """记录性能数据"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 写入CSV文件
        with open(self.performance_file, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp},{performance_data.get('total_value', 0)},"
                   f"{performance_data.get('available_balance', 0)},"
                   f"{performance_data.get('position_value', 0)},"
                   f"{performance_data.get('unrealized_pnl', 0)},"
                   f"{performance_data.get('realized_pnl', 0)},"
                   f"{performance_data.get('total_pnl', 0)},"
                   f"{performance_data.get('win_rate', 0)},"
                   f"{performance_data.get('max_drawdown', 0)},"
                   f"{performance_data.get('sharpe_ratio', 0)}\n")
        
        # 记录到日志
        self.logger.info(f"性能更新: 总价值={performance_data.get('total_value', 0):.2f}, "
                        f"总盈亏={performance_data.get('total_pnl', 0):.2f}")

# 单例实例
trading_log = TradingLogger()
performance_log = PerformanceLogger()

def get_logger(module_name: str) -> logging.Logger:
    """获取指定模块的日志记录器"""
    logger_map = {
        'trading': trading_logger,
        'data': data_logger,
        'strategy': strategy_logger,
        'performance': performance_logger,
        'system': system_logger
    }
    return logger_map.get(module_name, system_logger)