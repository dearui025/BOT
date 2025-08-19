"""
交易策略模块
实现各种交易策略和信号生成
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from config import STRATEGY_CONFIG
from logger_config import get_logger

logger = get_logger('strategy')

class TradingSignal:
    """交易信号类"""
    
    def __init__(self, signal_type: str, strength: float, price: float, 
                 timestamp: datetime = None, metadata: Dict = None):
        self.signal_type = signal_type  # 'BUY', 'SELL', 'HOLD'
        self.strength = strength        # 信号强度 0-1
        self.price = price             # 建议价格
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}  # 额外信息
    
    def __repr__(self):
        return (f"TradingSignal(type={self.signal_type}, "
                f"strength={self.strength:.2f}, price={self.price:.2f})")

class TradingStrategy(ABC):
    """交易策略基类"""
    
    def __init__(self, name: str, params: Dict = None):
        self.name = name
        self.params = params or {}
        self.signals_history = []
        self.last_signal = None
        
        logger.info(f"策略初始化: {self.name}")
    
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradingSignal]:
        """生成交易信号 - 需要子类实现"""
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """验证数据有效性"""
        if data is None or len(data) == 0:
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required_columns)
    
    def add_signal(self, signal: TradingSignal):
        """添加信号到历史记录"""
        self.signals_history.append(signal)
        self.last_signal = signal
        
        # 保持历史记录长度限制
        if len(self.signals_history) > 1000:
            self.signals_history = self.signals_history[-1000:]
        
        logger.info(f"策略 {self.name} 生成信号: {signal}")

class DualMAStrategy(TradingStrategy):
    """双均线交叉策略"""
    
    def __init__(self, short_period: int = 10, long_period: int = 30, 
                 signal_threshold: float = 0.1):
        super().__init__("双均线策略", {
            'short_period': short_period,
            'long_period': long_period,
            'signal_threshold': signal_threshold
        })
        
        self.short_period = short_period
        self.long_period = long_period
        self.signal_threshold = signal_threshold
        self.last_ma_cross = None
        
        logger.info(f"双均线策略参数: 短期={short_period}, 长期={long_period}")
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradingSignal]:
        """生成双均线交叉信号"""
        if not self.validate_data(data) or len(data) < max(self.short_period, self.long_period):
            return None
        
        try:
            # 计算移动平均线
            short_ma = data['close'].rolling(window=self.short_period).mean()
            long_ma = data['close'].rolling(window=self.long_period).mean()
            
            # 获取最近的数据
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            prev_short = short_ma.iloc[-2] if len(short_ma) > 1 else current_short
            prev_long = long_ma.iloc[-2] if len(long_ma) > 1 else current_long
            
            current_price = data['close'].iloc[-1]
            signal = None
            
            # 检测金叉（买入信号）
            if (prev_short <= prev_long and current_short > current_long and 
                abs(current_short - current_long) / current_long > self.signal_threshold / 100):
                
                # 计算信号强度
                strength = min(abs(current_short - current_long) / current_long * 10, 1.0)
                
                signal = TradingSignal(
                    signal_type='BUY',
                    strength=strength,
                    price=current_price,
                    metadata={
                        'short_ma': current_short,
                        'long_ma': current_long,
                        'cross_type': 'golden_cross'
                    }
                )
                self.last_ma_cross = 'golden'
            
            # 检测死叉（卖出信号）
            elif (prev_short >= prev_long and current_short < current_long and 
                  abs(current_short - current_long) / current_long > self.signal_threshold / 100):
                
                # 计算信号强度
                strength = min(abs(current_short - current_long) / current_long * 10, 1.0)
                
                signal = TradingSignal(
                    signal_type='SELL',
                    strength=strength,
                    price=current_price,
                    metadata={
                        'short_ma': current_short,
                        'long_ma': current_long,
                        'cross_type': 'death_cross'
                    }
                )
                self.last_ma_cross = 'death'
            
            if signal:
                self.add_signal(signal)
                return signal
                
        except Exception as e:
            logger.error(f"双均线策略计算错误: {e}")
            
        return None

class RSIStrategy(TradingStrategy):
    """RSI超买超卖策略"""
    
    def __init__(self, period: int = 14, overbought: float = 70, 
                 oversold: float = 30):
        super().__init__("RSI策略", {
            'period': period,
            'overbought': overbought,
            'oversold': oversold
        })
        
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradingSignal]:
        """生成RSI信号"""
        if not self.validate_data(data) or len(data) < self.period + 1:
            return None
        
        try:
            # 计算RSI
            if 'rsi' not in data.columns:
                data['rsi'] = self._calculate_rsi(data['close'], self.period)
            
            current_rsi = data['rsi'].iloc[-1]
            prev_rsi = data['rsi'].iloc[-2] if len(data) > 1 else current_rsi
            current_price = data['close'].iloc[-1]
            
            signal = None
            
            # 超卖区域买入信号
            if prev_rsi >= self.oversold and current_rsi < self.oversold:
                strength = (self.oversold - current_rsi) / self.oversold
                signal = TradingSignal(
                    signal_type='BUY',
                    strength=min(strength, 1.0),
                    price=current_price,
                    metadata={'rsi': current_rsi, 'condition': 'oversold'}
                )
            
            # 超买区域卖出信号
            elif prev_rsi <= self.overbought and current_rsi > self.overbought:
                strength = (current_rsi - self.overbought) / (100 - self.overbought)
                signal = TradingSignal(
                    signal_type='SELL',
                    strength=min(strength, 1.0),
                    price=current_price,
                    metadata={'rsi': current_rsi, 'condition': 'overbought'}
                )
            
            if signal:
                self.add_signal(signal)
                return signal
                
        except Exception as e:
            logger.error(f"RSI策略计算错误: {e}")
        
        return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

class MACDStrategy(TradingStrategy):
    """MACD策略"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, 
                 signal_period: int = 9):
        super().__init__("MACD策略", {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period
        })
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradingSignal]:
        """生成MACD信号"""
        min_periods = max(self.slow_period, self.signal_period) + 1
        if not self.validate_data(data) or len(data) < min_periods:
            return None
        
        try:
            # 计算MACD
            if 'macd' not in data.columns:
                macd_data = self._calculate_macd(data['close'])
                data['macd'] = macd_data['macd']
                data['macd_signal'] = macd_data['signal']
                data['macd_histogram'] = macd_data['histogram']
            
            current_macd = data['macd'].iloc[-1]
            current_signal = data['macd_signal'].iloc[-1]
            current_histogram = data['macd_histogram'].iloc[-1]
            prev_histogram = data['macd_histogram'].iloc[-2] if len(data) > 1 else current_histogram
            
            current_price = data['close'].iloc[-1]
            signal = None
            
            # MACD线上穿信号线（买入）
            if prev_histogram <= 0 and current_histogram > 0:
                strength = min(abs(current_histogram) / abs(current_signal) * 2, 1.0)
                signal = TradingSignal(
                    signal_type='BUY',
                    strength=strength,
                    price=current_price,
                    metadata={
                        'macd': current_macd,
                        'signal': current_signal,
                        'histogram': current_histogram,
                        'cross_type': 'bullish'
                    }
                )
            
            # MACD线下穿信号线（卖出）
            elif prev_histogram >= 0 and current_histogram < 0:
                strength = min(abs(current_histogram) / abs(current_signal) * 2, 1.0)
                signal = TradingSignal(
                    signal_type='SELL',
                    strength=strength,
                    price=current_price,
                    metadata={
                        'macd': current_macd,
                        'signal': current_signal,
                        'histogram': current_histogram,
                        'cross_type': 'bearish'
                    }
                )
            
            if signal:
                self.add_signal(signal)
                return signal
                
        except Exception as e:
            logger.error(f"MACD策略计算错误: {e}")
        
        return None
    
    def _calculate_macd(self, prices: pd.Series) -> Dict:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=self.fast_period).mean()
        ema_slow = prices.ewm(span=self.slow_period).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=self.signal_period).mean()
        histogram = macd - macd_signal
        
        return {
            'macd': macd,
            'signal': macd_signal,
            'histogram': histogram
        }

class CombinedStrategy(TradingStrategy):
    """组合策略 - 结合多个策略的信号"""
    
    def __init__(self, strategies: List[TradingStrategy], weights: List[float] = None):
        super().__init__("组合策略")
        self.strategies = strategies
        self.weights = weights or [1.0] * len(strategies)
        
        if len(self.weights) != len(self.strategies):
            raise ValueError("策略权重数量必须与策略数量一致")
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradingSignal]:
        """生成组合信号"""
        if not self.validate_data(data):
            return None
        
        try:
            signals = []
            weights = []
            
            # 收集所有策略的信号
            for i, strategy in enumerate(self.strategies):
                signal = strategy.generate_signal(data)
                if signal:
                    signals.append(signal)
                    weights.append(self.weights[i])
            
            if not signals:
                return None
            
            # 计算加权信号
            buy_strength = 0
            sell_strength = 0
            total_weight = sum(weights)
            
            current_price = data['close'].iloc[-1]
            
            for signal, weight in zip(signals, weights):
                normalized_weight = weight / total_weight
                
                if signal.signal_type == 'BUY':
                    buy_strength += signal.strength * normalized_weight
                elif signal.signal_type == 'SELL':
                    sell_strength += signal.strength * normalized_weight
            
            # 生成最终信号
            if buy_strength > sell_strength and buy_strength > 0.5:
                final_signal = TradingSignal(
                    signal_type='BUY',
                    strength=buy_strength,
                    price=current_price,
                    metadata={
                        'buy_strength': buy_strength,
                        'sell_strength': sell_strength,
                        'component_signals': len(signals)
                    }
                )
            elif sell_strength > buy_strength and sell_strength > 0.5:
                final_signal = TradingSignal(
                    signal_type='SELL',
                    strength=sell_strength,
                    price=current_price,
                    metadata={
                        'buy_strength': buy_strength,
                        'sell_strength': sell_strength,
                        'component_signals': len(signals)
                    }
                )
            else:
                return None
            
            self.add_signal(final_signal)
            return final_signal
            
        except Exception as e:
            logger.error(f"组合策略计算错误: {e}")
            
        return None

class StrategyManager:
    """策略管理器"""
    
    def __init__(self):
        self.strategies = {}
        self.active_strategy = None
        
        # 初始化默认策略
        self._init_default_strategies()
        logger.info("策略管理器初始化完成")
    
    def _init_default_strategies(self):
        """初始化默认策略"""
        # 双均线策略
        dual_ma_config = STRATEGY_CONFIG.get('dual_ma', {})
        dual_ma = DualMAStrategy(
            short_period=dual_ma_config.get('short_period', 10),
            long_period=dual_ma_config.get('long_period', 30),
            signal_threshold=dual_ma_config.get('signal_threshold', 0.1)
        )
        self.add_strategy('dual_ma', dual_ma)
        
        # RSI策略
        rsi_config = STRATEGY_CONFIG.get('rsi', {})
        rsi_strategy = RSIStrategy(
            period=rsi_config.get('period', 14),
            overbought=rsi_config.get('overbought', 70),
            oversold=rsi_config.get('oversold', 30)
        )
        self.add_strategy('rsi', rsi_strategy)
        
        # MACD策略
        macd_config = STRATEGY_CONFIG.get('macd', {})
        macd_strategy = MACDStrategy(
            fast_period=macd_config.get('fast_period', 12),
            slow_period=macd_config.get('slow_period', 26),
            signal_period=macd_config.get('signal_period', 9)
        )
        self.add_strategy('macd', macd_strategy)
        
        # 组合策略
        combined_strategy = CombinedStrategy(
            strategies=[dual_ma, rsi_strategy, macd_strategy],
            weights=[0.5, 0.3, 0.2]
        )
        self.add_strategy('combined', combined_strategy)
        
        # 设置默认活跃策略
        self.set_active_strategy('dual_ma')
    
    def add_strategy(self, name: str, strategy: TradingStrategy):
        """添加策略"""
        self.strategies[name] = strategy
        logger.info(f"策略已添加: {name}")
    
    def remove_strategy(self, name: str):
        """移除策略"""
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"策略已移除: {name}")
    
    def set_active_strategy(self, name: str):
        """设置活跃策略"""
        if name in self.strategies:
            self.active_strategy = self.strategies[name]
            logger.info(f"活跃策略设置为: {name}")
            return True
        else:
            logger.error(f"策略不存在: {name}")
            return False
    
    def get_active_strategy(self) -> Optional[TradingStrategy]:
        """获取活跃策略"""
        return self.active_strategy
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradingSignal]:
        """使用活跃策略生成信号"""
        if self.active_strategy:
            return self.active_strategy.generate_signal(data)
        return None
    
    def get_all_signals(self, data: pd.DataFrame) -> Dict[str, Optional[TradingSignal]]:
        """获取所有策略的信号"""
        signals = {}
        for name, strategy in self.strategies.items():
            try:
                signals[name] = strategy.generate_signal(data)
            except Exception as e:
                logger.error(f"策略 {name} 生成信号失败: {e}")
                signals[name] = None
        return signals
    
    def get_strategy_performance(self) -> Dict[str, Dict]:
        """获取策略性能统计"""
        performance = {}
        
        for name, strategy in self.strategies.items():
            signals = strategy.signals_history
            
            if not signals:
                performance[name] = {
                    'total_signals': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'avg_strength': 0.0
                }
                continue
            
            buy_signals = [s for s in signals if s.signal_type == 'BUY']
            sell_signals = [s for s in signals if s.signal_type == 'SELL']
            avg_strength = sum(s.strength for s in signals) / len(signals)
            
            performance[name] = {
                'total_signals': len(signals),
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals),
                'avg_strength': avg_strength,
                'last_signal': signals[-1] if signals else None
            }
        
        return performance

# 全局策略管理器实例
strategy_manager = StrategyManager()

def get_strategy_manager() -> StrategyManager:
    """获取策略管理器实例"""
    return strategy_manager