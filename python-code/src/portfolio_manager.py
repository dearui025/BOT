"""
投资组合管理模块
负责管理虚拟资金、持仓和交易记录
"""
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from config import INITIAL_BALANCE
from logger_config import get_logger

logger = get_logger('trading')

class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self, initial_balance: float = INITIAL_BALANCE):
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.positions = {}  # {symbol: {'quantity': float, 'avg_price': float}}
        self.trade_history = []
        self.balance_history = []
        
        # 记录初始状态
        self.balance_history.append({
            'timestamp': datetime.now(),
            'total_value': initial_balance,
            'available_balance': initial_balance,
            'position_value': 0.0
        })
        
        logger.info(f"投资组合管理器初始化，初始资金: ${initial_balance:,.2f}")
    
    def get_position(self, symbol: str) -> Dict:
        """获取指定交易对的持仓"""
        return self.positions.get(symbol, {'quantity': 0.0, 'avg_price': 0.0})
    
    def update_position(self, symbol: str, side: str, quantity: float, price: float):
        """更新持仓"""
        if symbol not in self.positions:
            self.positions[symbol] = {'quantity': 0.0, 'avg_price': 0.0}
        
        position = self.positions[symbol]
        
        if side == 'BUY':
            # 买入
            total_cost = position['quantity'] * position['avg_price'] + quantity * price
            total_quantity = position['quantity'] + quantity
            
            if total_quantity > 0:
                position['avg_price'] = total_cost / total_quantity
            position['quantity'] = total_quantity
            
            # 减少可用余额
            self.available_balance -= quantity * price
            
        elif side == 'SELL':
            # 卖出
            if position['quantity'] >= quantity:
                position['quantity'] -= quantity
                # 增加可用余额
                self.available_balance += quantity * price
                
                if position['quantity'] == 0:
                    position['avg_price'] = 0.0
            else:
                logger.error(f"持仓不足，无法卖出 {quantity} {symbol}")
                return False
        
        # 记录交易
        trade_record = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'total': quantity * price
        }
        self.trade_history.append(trade_record)
        
        logger.info(f"持仓更新: {symbol} {side} {quantity} @ ${price:.2f}")
        return True
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """计算总资产价值"""
        position_value = 0.0
        
        for symbol, position in self.positions.items():
            if position['quantity'] > 0 and symbol in current_prices:
                position_value += position['quantity'] * current_prices[symbol]
        
        return self.available_balance + position_value
    
    def get_portfolio_summary(self, current_prices: Dict[str, float]) -> Dict:
        """获取投资组合摘要"""
        total_value = self.get_total_value(current_prices)
        position_value = total_value - self.available_balance
        total_pnl = total_value - self.initial_balance
        
        # 计算胜率
        profitable_trades = sum(1 for trade in self.trade_history 
                              if trade['side'] == 'SELL' and self._calculate_trade_pnl(trade) > 0)
        sell_trades = sum(1 for trade in self.trade_history if trade['side'] == 'SELL')
        win_rate = (profitable_trades / max(sell_trades, 1)) * 100
        
        return {
            'total_value': total_value,
            'available_balance': self.available_balance,
            'position_value': position_value,
            'unrealized_pnl': self._calculate_unrealized_pnl(current_prices),
            'total_pnl': total_pnl,
            'total_return_pct': (total_pnl / self.initial_balance) * 100,
            'win_rate': win_rate,
            'total_trades': len([t for t in self.trade_history if t['side'] == 'SELL'])
        }
    
    def _calculate_trade_pnl(self, trade: Dict) -> float:
        """计算单笔交易盈亏（简化版）"""
        # 这里需要更复杂的逻辑来匹配买卖订单
        return 0.0
    
    def _calculate_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """计算未实现盈亏"""
        unrealized_pnl = 0.0
        
        for symbol, position in self.positions.items():
            if position['quantity'] > 0 and symbol in current_prices:
                current_value = position['quantity'] * current_prices[symbol]
                cost_value = position['quantity'] * position['avg_price']
                unrealized_pnl += current_value - cost_value
        
        return unrealized_pnl
    
    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """获取最近的交易记录"""
        return self.trade_history[-limit:] if self.trade_history else []

# 全局实例
portfolio_manager = PortfolioManager()

def get_portfolio_manager() -> PortfolioManager:
    """获取投资组合管理器实例"""
    return portfolio_manager