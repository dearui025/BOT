"""
交易执行模块
负责模拟交易的执行和管理
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd

from config import *
from logger_config import trading_log, get_logger
from trading_strategy import TradingSignal

logger = get_logger('trading')

class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"      # 市价单
    LIMIT = "LIMIT"        # 限价单
    STOP_LOSS = "STOP_LOSS"      # 止损单
    TAKE_PROFIT = "TAKE_PROFIT"  # 止盈单

class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"      # 待成交
    FILLED = "FILLED"        # 已成交
    CANCELLED = "CANCELLED"  # 已取消
    REJECTED = "REJECTED"    # 已拒绝
    EXPIRED = "EXPIRED"      # 已过期

class OrderSide(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"

class Order:
    """订单类"""
    
    def __init__(self, symbol: str, side: OrderSide, order_type: OrderType,
                 quantity: float, price: float = None, stop_price: float = None):
        self.id = str(uuid.uuid4())
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.filled_quantity = 0.0
        self.remaining_quantity = quantity
        self.avg_fill_price = 0.0
        self.status = OrderStatus.PENDING
        self.created_time = datetime.now()
        self.updated_time = datetime.now()
        self.fills = []
        self.commission = 0.0
        
    def __repr__(self):
        return (f"Order(id={self.id[:8]}, {self.side.value} {self.quantity} "
                f"{self.symbol} @ {self.price}, status={self.status.value})")

class Trade:
    """成交记录类"""
    
    def __init__(self, order_id: str, symbol: str, side: OrderSide,
                 quantity: float, price: float, commission: float = 0.0):
        self.id = str(uuid.uuid4())
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.total = quantity * price
        self.commission = commission
        self.timestamp = datetime.now()
        
    def __repr__(self):
        return (f"Trade(id={self.id[:8]}, {self.side.value} {self.quantity} "
                f"{self.symbol} @ {self.price}, total={self.total:.2f})")

class Position:
    """持仓类"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.quantity = 0.0          # 持仓数量
        self.avg_price = 0.0         # 平均成本
        self.realized_pnl = 0.0      # 已实现盈亏
        self.unrealized_pnl = 0.0    # 未实现盈亏
        self.total_cost = 0.0        # 总成本
        self.total_commission = 0.0  # 总手续费
        self.last_update = datetime.now()
        
    def update_position(self, trade: Trade):
        """更新持仓信息"""
        if trade.side == OrderSide.BUY:
            # 买入
            new_total_cost = self.total_cost + trade.total
            new_quantity = self.quantity + trade.quantity
            
            if new_quantity > 0:
                self.avg_price = new_total_cost / new_quantity
            
            self.quantity = new_quantity
            self.total_cost = new_total_cost
            
        else:
            # 卖出
            if self.quantity > 0:
                # 计算已实现盈亏
                sell_cost = trade.quantity * self.avg_price
                realized_pnl = trade.total - sell_cost
                self.realized_pnl += realized_pnl
                
                # 更新持仓
                self.quantity -= trade.quantity
                if self.quantity <= 0:
                    self.quantity = 0.0
                    self.total_cost = 0.0
                    self.avg_price = 0.0
                else:
                    self.total_cost -= sell_cost
        
        self.total_commission += trade.commission
        self.last_update = datetime.now()
    
    def calculate_unrealized_pnl(self, current_price: float):
        """计算未实现盈亏"""
        if self.quantity > 0 and current_price > 0:
            current_value = self.quantity * current_price
            self.unrealized_pnl = current_value - self.total_cost
        else:
            self.unrealized_pnl = 0.0
    
    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        return self.realized_pnl + self.unrealized_pnl
    
    def __repr__(self):
        return (f"Position({self.symbol}: qty={self.quantity:.6f}, "
                f"avg_price={self.avg_price:.2f}, "
                f"unrealized_pnl={self.unrealized_pnl:.2f})")

class TradeExecutor:
    """交易执行器"""
    
    def __init__(self, initial_balance: float = INITIAL_BALANCE):
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.orders = {}
        self.trades = []
        self.positions = {}
        self.current_prices = {}
        
        # 风险控制参数
        self.max_position_size = MAX_POSITION_SIZE
        self.commission_rate = BACKTEST_COMMISSION
        self.slippage = BACKTEST_SLIPPAGE
        
        # 统计数据
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0.0
        
        logger.info(f"交易执行器初始化完成，初始资金: {initial_balance:.2f}")
    
    def update_price(self, symbol: str, price: float):
        """更新市场价格"""
        self.current_prices[symbol] = price
        
        # 更新持仓的未实现盈亏
        if symbol in self.positions:
            self.positions[symbol].calculate_unrealized_pnl(price)
        
        # 检查触发条件的订单
        self._check_pending_orders(symbol, price)
    
    def place_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                   quantity: float, price: float = None, stop_price: float = None) -> Optional[str]:
        """下单"""
        try:
            # 验证参数
            if quantity <= 0:
                logger.error(f"订单数量必须大于0: {quantity}")
                return None
            
            if symbol not in self.current_prices:
                logger.error(f"未知交易对: {symbol}")
                return None
            
            current_price = self.current_prices[symbol]
            
            # 设置价格
            if order_type == OrderType.MARKET:
                price = current_price
            elif price is None:
                logger.error("限价单必须指定价格")
                return None
            
            # 风险检查
            if not self._risk_check(symbol, side, quantity, price):
                return None
            
            # 创建订单
            order = Order(symbol, side, order_type, quantity, price, stop_price)
            self.orders[order.id] = order
            
            # 市价单立即执行
            if order_type == OrderType.MARKET:
                self._execute_order(order, current_price)
            
            logger.info(f"订单已提交: {order}")
            return order.id
            
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            if order_id in self.orders:
                order = self.orders[order_id]
                if order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.CANCELLED
                    order.updated_time = datetime.now()
                    logger.info(f"订单已取消: {order_id}")
                    return True
                else:
                    logger.warning(f"订单状态不允许取消: {order.status}")
                    return False
            else:
                logger.error(f"订单不存在: {order_id}")
                return False
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
    
    def _risk_check(self, symbol: str, side: OrderSide, quantity: float, price: float) -> bool:
        """风险检查"""
        try:
            # 检查最小交易金额
            order_value = quantity * price
            if order_value < MIN_TRADE_AMOUNT:
                logger.error(f"交易金额过小: {order_value:.2f} < {MIN_TRADE_AMOUNT}")
                return False
            
            # 检查可用余额
            if side == OrderSide.BUY:
                required_balance = order_value * (1 + self.commission_rate)
                if self.available_balance < required_balance:
                    logger.error(f"余额不足: {self.available_balance:.2f} < {required_balance:.2f}")
                    return False
            else:
                # 检查持仓数量
                position = self.positions.get(symbol)
                if not position or position.quantity < quantity:
                    available_qty = position.quantity if position else 0
                    logger.error(f"持仓不足: {available_qty:.6f} < {quantity:.6f}")
                    return False
            
            # 检查最大仓位限制
            if side == OrderSide.BUY:
                total_value = self.get_total_value()
                position_limit = total_value * self.max_position_size
                if order_value > position_limit:
                    logger.error(f"超过最大仓位限制: {order_value:.2f} > {position_limit:.2f}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"风险检查失败: {e}")
            return False
    
    def _execute_order(self, order: Order, execution_price: float):
        """执行订单"""
        try:
            # 应用滑点
            if order.side == OrderSide.BUY:
                execution_price *= (1 + self.slippage)
            else:
                execution_price *= (1 - self.slippage)
            
            # 计算手续费
            trade_value = order.quantity * execution_price
            commission = trade_value * self.commission_rate
            
            # 创建成交记录
            trade = Trade(
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                commission=commission
            )
            
            # 更新订单状态
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.remaining_quantity = 0.0
            order.avg_fill_price = execution_price
            order.commission = commission
            order.updated_time = datetime.now()
            order.fills.append(trade)
            
            # 更新余额和持仓
            self._update_balance_and_position(trade)
            
            # 记录交易
            self.trades.append(trade)
            self.total_trades += 1
            self.total_commission += commission
            
            # 记录交易日志
            self._log_trade(trade)
            
            logger.info(f"订单执行成功: {trade}")
            
        except Exception as e:
            logger.error(f"订单执行失败: {e}")
            order.status = OrderStatus.REJECTED
            order.updated_time = datetime.now()
    
    def _update_balance_and_position(self, trade: Trade):
        """更新余额和持仓"""
        symbol = trade.symbol
        
        # 初始化持仓
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        
        position = self.positions[symbol]
        
        # 更新持仓
        position.update_position(trade)
        
        # 更新余额
        if trade.side == OrderSide.BUY:
            # 买入：减少现金余额
            self.available_balance -= (trade.total + trade.commission)
        else:
            # 卖出：增加现金余额
            self.available_balance += (trade.total - trade.commission)
            
            # 更新统计
            if position.realized_pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
    
    def _check_pending_orders(self, symbol: str, current_price: float):
        """检查待成交订单"""
        pending_orders = [order for order in self.orders.values() 
                         if order.status == OrderStatus.PENDING and order.symbol == symbol]
        
        for order in pending_orders:
            should_execute = False
            execution_price = current_price
            
            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.price:
                    should_execute = True
                    execution_price = order.price
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    should_execute = True
                    execution_price = order.price
                    
            elif order.order_type == OrderType.STOP_LOSS:
                if order.stop_price:
                    if order.side == OrderSide.BUY and current_price >= order.stop_price:
                        should_execute = True
                    elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                        should_execute = True
                        
            elif order.order_type == OrderType.TAKE_PROFIT:
                if order.price:
                    if order.side == OrderSide.BUY and current_price <= order.price:
                        should_execute = True
                        execution_price = order.price
                    elif order.side == OrderSide.SELL and current_price >= order.price:
                        should_execute = True
                        execution_price = order.price
            
            if should_execute:
                self._execute_order(order, execution_price)
    
    def _log_trade(self, trade: Trade):
        """记录交易日志"""
        trade_data = {
            'symbol': trade.symbol,
            'side': trade.side.value,
            'price': trade.price,
            'quantity': trade.quantity,
            'total': trade.total,
            'fee': trade.commission,
            'strategy': 'auto',
            'status': 'EXECUTED',
            'pnl': 0.0  # 会在持仓更新后计算
        }
        
        trading_log.log_trade(trade_data)
    
    def execute_signal(self, signal: TradingSignal, symbol: str, 
                      position_size_pct: float = 0.1) -> Optional[str]:
        """执行交易信号"""
        try:
            if signal.signal_type not in ['BUY', 'SELL']:
                return None
            
            current_price = self.current_prices.get(symbol)
            if not current_price:
                logger.error(f"无法获取 {symbol} 当前价格")
                return None
            
            # 计算交易数量
            if signal.signal_type == 'BUY':
                # 买入：根据可用余额和仓位比例计算
                max_investment = self.available_balance * position_size_pct
                quantity = max_investment / current_price
                
                if quantity * current_price < MIN_TRADE_AMOUNT:
                    logger.warning(f"交易金额过小，跳过信号: {quantity * current_price:.2f}")
                    return None
                
                return self.place_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=quantity
                )
                
            else:  # SELL
                # 卖出：卖出当前持仓的一定比例
                position = self.positions.get(symbol)
                if not position or position.quantity <= 0:
                    logger.warning(f"无持仓可卖出: {symbol}")
                    return None
                
                # 卖出全部持仓（也可以设置为部分卖出）
                quantity = position.quantity
                
                return self.place_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=quantity
                )
                
        except Exception as e:
            logger.error(f"执行交易信号失败: {e}")
            return None
    
    def get_portfolio_summary(self) -> Dict:
        """获取投资组合摘要"""
        total_value = self.get_total_value()
        position_value = self.get_position_value()
        total_pnl = self.get_total_pnl()
        
        return {
            'initial_balance': self.initial_balance,
            'available_balance': self.available_balance,
            'position_value': position_value,
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_return_pct': (total_pnl / self.initial_balance) * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / max(self.total_trades, 1)) * 100,
            'total_commission': self.total_commission
        }
    
    def get_total_value(self) -> float:
        """获取总价值"""
        return self.available_balance + self.get_position_value()
    
    def get_position_value(self) -> float:
        """获取持仓价值"""
        total_value = 0.0
        for symbol, position in self.positions.items():
            if position.quantity > 0 and symbol in self.current_prices:
                current_price = self.current_prices[symbol]
                total_value += position.quantity * current_price
        return total_value
    
    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        return self.get_total_value() - self.initial_balance
    
    def get_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return {k: v for k, v in self.positions.items() if v.quantity > 0}
    
    def get_recent_trades(self, limit: int = 20) -> List[Trade]:
        """获取最近的交易记录"""
        return self.trades[-limit:] if self.trades else []
    
    def get_open_orders(self) -> List[Order]:
        """获取未成交订单"""
        return [order for order in self.orders.values() 
                if order.status == OrderStatus.PENDING]

# 全局交易执行器实例
trade_executor = TradeExecutor()

def get_trade_executor() -> TradeExecutor:
    """获取交易执行器实例"""
    return trade_executor