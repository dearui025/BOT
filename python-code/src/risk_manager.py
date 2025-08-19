"""
风险管理模块
负责交易风险控制和资金管理
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

from config import *
from logger_config import get_logger

logger = get_logger('trading')

class RiskManager:
    """风险管理器"""
    
    def __init__(self):
        self.daily_trades = {}  # {date: count}
        self.daily_loss = {}    # {date: loss_amount}
        self.position_limits = {}  # {symbol: max_position}
        self.stop_loss_orders = {}  # {symbol: stop_price}
        self.take_profit_orders = {}  # {symbol: target_price}
        
        # 风险参数
        self.max_position_size = MAX_POSITION_SIZE
        self.stop_loss_pct = STOP_LOSS_PCT / 100
        self.take_profit_pct = TAKE_PROFIT_PCT / 100
        self.max_daily_trades = MAX_DAILY_TRADES
        self.max_daily_loss_pct = MAX_DAILY_LOSS_PCT / 100
        
        logger.info("风险管理器初始化完成")
    
    def can_trade(self, symbol: str, side: str, quantity: float = None, 
                  current_price: float = None) -> bool:
        """检查是否可以进行交易"""
        today = datetime.now().date()
        
        # 检查每日交易次数限制
        daily_count = self.daily_trades.get(today, 0)
        if daily_count >= self.max_daily_trades:
            logger.warning(f"已达到每日最大交易次数限制: {daily_count}")
            return False
        
        # 检查每日亏损限制
        daily_loss = self.daily_loss.get(today, 0)
        if daily_loss >= self.max_daily_loss_pct:
            logger.warning(f"已达到每日最大亏损限制: {daily_loss:.2%}")
            return False
        
        # 检查仓位限制
        if side == 'BUY' and quantity and current_price:
            position_value = quantity * current_price
            if not self._check_position_limit(symbol, position_value):
                return False
        
        return True
    
    def _check_position_limit(self, symbol: str, position_value: float) -> bool:
        """检查仓位限制"""
        # 这里需要获取当前总资产价值来计算仓位比例
        # 简化实现，假设总资产为初始资金
        max_position_value = INITIAL_BALANCE * self.max_position_size
        
        if position_value > max_position_value:
            logger.warning(f"超过最大仓位限制: {position_value:.2f} > {max_position_value:.2f}")
            return False
        
        return True
    
    def record_trade(self, symbol: str, side: str, quantity: float, price: float):
        """记录交易"""
        today = datetime.now().date()
        
        # 更新每日交易次数
        self.daily_trades[today] = self.daily_trades.get(today, 0) + 1
        
        # 如果是卖出，可能需要计算盈亏（简化处理）
        if side == 'SELL':
            # 这里应该计算实际盈亏，暂时跳过
            pass
        
        logger.info(f"交易记录: {symbol} {side} {quantity} @ {price}")
    
    def check_position_risk(self, symbol: str, current_price: float):
        """检查持仓风险"""
        # 检查止损
        if symbol in self.stop_loss_orders:
            stop_price = self.stop_loss_orders[symbol]
            if current_price <= stop_price:
                logger.warning(f"{symbol} 触发止损: {current_price} <= {stop_price}")
                # 这里应该触发止损卖出
                self._trigger_stop_loss(symbol, current_price)
        
        # 检查止盈
        if symbol in self.take_profit_orders:
            target_price = self.take_profit_orders[symbol]
            if current_price >= target_price:
                logger.info(f"{symbol} 触发止盈: {current_price} >= {target_price}")
                # 这里应该触发止盈卖出
                self._trigger_take_profit(symbol, current_price)
    
    def set_stop_loss(self, symbol: str, entry_price: float, side: str = 'LONG'):
        """设置止损价格"""
        if side == 'LONG':
            stop_price = entry_price * (1 - self.stop_loss_pct)
        else:  # SHORT
            stop_price = entry_price * (1 + self.stop_loss_pct)
        
        self.stop_loss_orders[symbol] = stop_price
        logger.info(f"设置止损: {symbol} @ {stop_price:.2f}")
    
    def set_take_profit(self, symbol: str, entry_price: float, side: str = 'LONG'):
        """设置止盈价格"""
        if side == 'LONG':
            target_price = entry_price * (1 + self.take_profit_pct)
        else:  # SHORT
            target_price = entry_price * (1 - self.take_profit_pct)
        
        self.take_profit_orders[symbol] = target_price
        logger.info(f"设置止盈: {symbol} @ {target_price:.2f}")
    
    def _trigger_stop_loss(self, symbol: str, current_price: float):
        """触发止损"""
        # 这里应该调用交易执行器进行止损卖出
        logger.warning(f"执行止损: {symbol} @ {current_price}")
        
        # 移除止损订单
        if symbol in self.stop_loss_orders:
            del self.stop_loss_orders[symbol]
    
    def _trigger_take_profit(self, symbol: str, current_price: float):
        """触发止盈"""
        # 这里应该调用交易执行器进行止盈卖出
        logger.info(f"执行止盈: {symbol} @ {current_price}")
        
        # 移除止盈订单
        if symbol in self.take_profit_orders:
            del self.take_profit_orders[symbol]
    
    def get_risk_metrics(self) -> Dict:
        """获取风险指标"""
        today = datetime.now().date()
        
        return {
            'daily_trades': self.daily_trades.get(today, 0),
            'max_daily_trades': self.max_daily_trades,
            'daily_loss': self.daily_loss.get(today, 0),
            'max_daily_loss': self.max_daily_loss_pct,
            'active_stop_losses': len(self.stop_loss_orders),
            'active_take_profits': len(self.take_profit_orders),
            'max_position_size': self.max_position_size
        }
    
    def reset_daily_limits(self):
        """重置每日限制（通常在新的一天开始时调用）"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # 清理旧数据
        if yesterday in self.daily_trades:
            del self.daily_trades[yesterday]
        if yesterday in self.daily_loss:
            del self.daily_loss[yesterday]
        
        logger.info("每日风险限制已重置")

# 全局实例
risk_manager = RiskManager()

def get_risk_manager() -> RiskManager:
    """获取风险管理器实例"""
    return risk_manager