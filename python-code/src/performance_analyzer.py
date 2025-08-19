"""
性能分析模块
计算和分析交易策略的各项性能指标
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from config import RISK_FREE_RATE
from logger_config import performance_log, get_logger

logger = get_logger('performance')

class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self):
        self.value_history = []
        self.drawdown_history = []
        self.returns_history = []
        self.benchmark_history = []
        
        logger.info("性能分析器初始化完成")
    
    def update_metrics(self, total_value: float, timestamp: datetime = None):
        """更新性能指标"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # 记录资产价值历史
        self.value_history.append({
            'timestamp': timestamp,
            'total_value': total_value
        })
        
        # 计算收益率
        if len(self.value_history) > 1:
            prev_value = self.value_history[-2]['total_value']
            current_return = (total_value - prev_value) / prev_value
            self.returns_history.append({
                'timestamp': timestamp,
                'return': current_return
            })
        
        # 计算回撤
        self._calculate_drawdown()
        
        # 记录性能日志
        if len(self.value_history) % 100 == 0:  # 每100次更新记录一次
            performance_data = self.get_performance_metrics()
            performance_log.log_performance(performance_data)
    
    def _calculate_drawdown(self):
        """计算回撤"""
        if len(self.value_history) < 2:
            return
        
        values = [item['total_value'] for item in self.value_history]
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        
        current_drawdown = drawdown[-1]
        self.drawdown_history.append({
            'timestamp': self.value_history[-1]['timestamp'],
            'drawdown': current_drawdown
        })
    
    def get_performance_metrics(self) -> Dict:
        """获取性能指标"""
        if len(self.value_history) < 2:
            return {}
        
        try:
            # 基础数据
            values = [item['total_value'] for item in self.value_history]
            returns = [item['return'] for item in self.returns_history]
            
            # 总收益率
            total_return = (values[-1] - values[0]) / values[0]
            
            # 年化收益率
            days = (self.value_history[-1]['timestamp'] - self.value_history[0]['timestamp']).days
            annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
            
            # 波动率
            volatility = np.std(returns) * np.sqrt(252) if returns else 0
            
            # 夏普比率
            excess_return = annual_return - RISK_FREE_RATE
            sharpe_ratio = excess_return / volatility if volatility > 0 else 0
            
            # 最大回撤
            drawdowns = [item['drawdown'] for item in self.drawdown_history]
            max_drawdown = min(drawdowns) if drawdowns else 0
            
            # 胜率（需要交易记录）
            win_rate = self._calculate_win_rate()
            
            # 卡尔玛比率
            calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            return {
                'total_value': values[-1],
                'available_balance': 0,  # 需要从外部传入
                'position_value': 0,     # 需要从外部传入
                'unrealized_pnl': 0,     # 需要从外部传入
                'realized_pnl': values[-1] - values[0],
                'total_pnl': values[-1] - values[0],
                'total_return': total_return * 100,
                'annual_return': annual_return * 100,
                'volatility': volatility * 100,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown * 100,
                'calmar_ratio': calmar_ratio,
                'win_rate': win_rate
            }
            
        except Exception as e:
            logger.error(f"计算性能指标失败: {e}")
            return {}
    
    def _calculate_win_rate(self) -> float:
        """计算胜率（简化版）"""
        # 这里需要实际的交易记录来计算胜率
        # 暂时返回模拟值
        return 65.0
    
    def plot_performance_chart(self, save_path: str = None) -> str:
        """绘制性能图表"""
        if len(self.value_history) < 2:
            logger.warning("数据不足，无法绘制图表")
            return ""
        
        try:
            # 准备数据
            df = pd.DataFrame(self.value_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 创建图表
            fig = go.Figure()
            
            # 添加资产价值曲线
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['total_value'],
                mode='lines',
                name='投资组合价值',
                line=dict(color='#00ff88', width=2)
            ))
            
            # 添加基准线（初始价值）
            initial_value = df['total_value'].iloc[0]
            fig.add_hline(
                y=initial_value,
                line_dash="dash",
                line_color="gray",
                annotation_text="初始价值"
            )
            
            # 设置布局
            fig.update_layout(
                title='投资组合性能表现',
                xaxis_title='时间',
                yaxis_title='价值 (USDT)',
                template='plotly_dark',
                height=500
            )
            
            # 保存图表
            if save_path:
                fig.write_html(save_path)
                logger.info(f"性能图表已保存: {save_path}")
                return save_path
            else:
                return fig.to_html()
                
        except Exception as e:
            logger.error(f"绘制性能图表失败: {e}")
            return ""
    
    def plot_drawdown_chart(self, save_path: str = None) -> str:
        """绘制回撤图表"""
        if len(self.drawdown_history) < 2:
            logger.warning("回撤数据不足，无法绘制图表")
            return ""
        
        try:
            # 准备数据
            df = pd.DataFrame(self.drawdown_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['drawdown_pct'] = df['drawdown'] * 100
            
            # 创建图表
            fig = go.Figure()
            
            # 添加回撤曲线
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['drawdown_pct'],
                mode='lines',
                name='回撤',
                fill='tonexty',
                line=dict(color='#ff4444', width=2)
            ))
            
            # 设置布局
            fig.update_layout(
                title='投资组合回撤分析',
                xaxis_title='时间',
                yaxis_title='回撤 (%)',
                template='plotly_dark',
                height=400
            )
            
            # 保存图表
            if save_path:
                fig.write_html(save_path)
                logger.info(f"回撤图表已保存: {save_path}")
                return save_path
            else:
                return fig.to_html()
                
        except Exception as e:
            logger.error(f"绘制回撤图表失败: {e}")
            return ""
    
    def plot_trades_chart(self, trades_data: List[Dict], save_path: str = None) -> str:
        """绘制交易记录图表"""
        if not trades_data:
            logger.warning("无交易数据，无法绘制图表")
            return ""
        
        try:
            # 准备数据
            df = pd.DataFrame(trades_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 分离买入和卖出
            buy_trades = df[df['side'] == 'BUY']
            sell_trades = df[df['side'] == 'SELL']
            
            # 创建图表
            fig = go.Figure()
            
            # 添加买入点
            if not buy_trades.empty:
                fig.add_trace(go.Scatter(
                    x=buy_trades['timestamp'],
                    y=buy_trades['price'],
                    mode='markers',
                    name='买入',
                    marker=dict(color='#00ff88', size=8, symbol='triangle-up')
                ))
            
            # 添加卖出点
            if not sell_trades.empty:
                fig.add_trace(go.Scatter(
                    x=sell_trades['timestamp'],
                    y=sell_trades['price'],
                    mode='markers',
                    name='卖出',
                    marker=dict(color='#ff4444', size=8, symbol='triangle-down')
                ))
            
            # 设置布局
            fig.update_layout(
                title='交易记录分布',
                xaxis_title='时间',
                yaxis_title='价格 (USDT)',
                template='plotly_dark',
                height=500
            )
            
            # 保存图表
            if save_path:
                fig.write_html(save_path)
                logger.info(f"交易图表已保存: {save_path}")
                return save_path
            else:
                return fig.to_html()
                
        except Exception as e:
            logger.error(f"绘制交易图表失败: {e}")
            return ""
    
    def generate_report(self) -> Dict:
        """生成完整的性能报告"""
        metrics = self.get_performance_metrics()
        
        report = {
            'summary': metrics,
            'charts': {
                'performance': self.plot_performance_chart(),
                'drawdown': self.plot_drawdown_chart()
            },
            'generated_at': datetime.now().isoformat()
        }
        
        return report

# 全局实例
performance_analyzer = PerformanceAnalyzer()

def get_performance_analyzer() -> PerformanceAnalyzer:
    """获取性能分析器实例"""
    return performance_analyzer