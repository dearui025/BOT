"""
主程序入口
统一管理所有模块，提供不同运行模式
"""
import argparse
import asyncio
import signal
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List

from config import *
from data_collector import get_data_collector
from trading_strategy import get_strategy_manager
from trade_executor import get_trade_executor
from performance_analyzer import get_performance_analyzer
from risk_manager import get_risk_manager
from logger_config import get_logger, system_logger
from websocket_server import get_websocket_server

logger = get_logger('system')

class TradingBot:
    """交易机器人主类"""
    
    def __init__(self):
        self.is_running = False
        self.data_collector = get_data_collector()
        self.strategy_manager = get_strategy_manager()
        self.trade_executor = get_trade_executor()
        self.performance_analyzer = get_performance_analyzer()
        self.risk_manager = get_risk_manager()
        self.websocket_server = get_websocket_server()
        
        # 运行模式
        self.mode = 'paper'  # 'paper', 'backtest', 'live'
        self.auto_trading_enabled = False
        
        # 统计数据
        self.start_time = None
        self.last_signal_check = datetime.now()
        self.signal_check_interval = STRATEGY_CHECK_INTERVAL
        
        logger.info("交易机器人初始化完成")
    
    def setup_callbacks(self):
        """设置回调函数"""
        # 价格更新回调
        self.data_collector.add_price_callback(self._on_price_update)
        
        # K线数据回调
        self.data_collector.add_kline_callback(self._on_kline_update)
        
        # 启动WebSocket服务器
        self.websocket_server.start_in_thread()
        
        logger.info("回调函数设置完成")
    
    def _on_price_update(self, symbol: str, price: float, change: float):
        """价格更新回调"""
        # 更新交易执行器的价格
        self.trade_executor.update_price(symbol, price)
        
        # 获取完整市场数据并发送给前端
        market_data = self.data_collector.get_current_market_data(symbol)
        if market_data:
            self.websocket_server.update_market_data(
                symbol=symbol,
                price=price,
                change=change,
                volume=market_data.get('volume', 0),
                high=market_data.get('high', 0),
                low=market_data.get('low', 0)
            )
        
        # 检查风险管理
        self.risk_manager.check_position_risk(symbol, price)
        
        # 如果启用自动交易，检查交易信号
        if (self.auto_trading_enabled and 
            datetime.now() - self.last_signal_check >= timedelta(seconds=self.signal_check_interval)):
            
            self._check_trading_signals(symbol)
            self.last_signal_check = datetime.now()
    
    def _on_kline_update(self, kline_data: Dict):
        """K线数据更新回调"""
        symbol = kline_data['symbol']
        
        # 如果启用自动交易，基于新K线检查信号
        if self.auto_trading_enabled:
            self._check_trading_signals(symbol)
    
    def _check_trading_signals(self, symbol: str):
        """检查交易信号"""
        try:
            # 获取最近的K线数据
            data = self.data_collector.get_recent_klines(symbol, limit=100)
            if data.empty:
                return
            
            # 生成交易信号
            signal = self.strategy_manager.generate_signal(data)
            
            if signal and signal.strength > 0.7:  # 只执行强信号
                # 风险检查
                if self.risk_manager.can_trade(symbol, signal.signal_type):
                    # 执行交易
                    order_id = self.trade_executor.execute_signal(
                        signal=signal,
                        symbol=symbol,
                        position_size_pct=0.1  # 使用10%的资金
                    )
                    
                    if order_id:
                        logger.info(f"自动交易执行: {signal} -> 订单ID: {order_id}")
                    else:
                        logger.warning(f"自动交易执行失败: {signal}")
                else:
                    logger.info(f"风险控制阻止交易: {signal}")
                    
        except Exception as e:
            logger.error(f"检查交易信号失败: {e}")
    
    def start_paper_trading(self, symbols: List[str], auto_trading: bool = False):
        """启动模拟交易模式"""
        logger.info("启动模拟交易模式")
        
        self.mode = 'paper'
        self.auto_trading_enabled = auto_trading
        self.is_running = True
        self.start_time = datetime.now()
        
        # 设置回调函数
        self.setup_callbacks()
        
        # 启动WebSocket数据流
        self.data_collector.start_websocket(symbols, DEFAULT_INTERVAL)
        
        if auto_trading:
            logger.info("自动交易已启用")
        else:
            logger.info("手动交易模式")
        
        # 主循环
        try:
            while self.is_running:
                self._update_performance()
                time.sleep(UPDATE_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("接收到停止信号")
        finally:
            self.stop()
    
    def start_backtest(self, symbols: List[str], start_date: str, end_date: str):
        """启动回测模式"""
        logger.info(f"启动回测模式: {start_date} - {end_date}")
        
        self.mode = 'backtest'
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            for symbol in symbols:
                logger.info(f"回测交易对: {symbol}")
                
                # 获取历史数据
                data = self.data_collector.get_historical_klines(
                    symbol=symbol,
                    interval=DEFAULT_INTERVAL,
                    start_time=start_date,
                    end_time=end_date,
                    limit=10000
                )
                
                if data.empty:
                    logger.error(f"无法获取 {symbol} 的历史数据")
                    continue
                
                # 逐行回测
                self._run_backtest_simulation(symbol, data)
                
            # 生成回测报告
            self._generate_backtest_report()
            
        except Exception as e:
            logger.error(f"回测失败: {e}")
        finally:
            self.stop()
    
    def _run_backtest_simulation(self, symbol: str, data: pd.DataFrame):
        """运行回测模拟"""
        logger.info(f"开始回测模拟: {symbol}, 数据量: {len(data)}")
        
        for i in range(max(50, self.strategy_manager.get_active_strategy().params.get('long_period', 30)), len(data)):
            # 获取当前时间点的数据
            current_data = data.iloc[:i+1]
            current_price = current_data['close'].iloc[-1]
            current_time = current_data['timestamp'].iloc[-1]
            
            # 更新价格
            self.trade_executor.update_price(symbol, current_price)
            
            # 生成交易信号
            signal = self.strategy_manager.generate_signal(current_data)
            
            if signal and signal.strength > 0.6:
                # 执行交易
                order_id = self.trade_executor.execute_signal(
                    signal=signal,
                    symbol=symbol,
                    position_size_pct=0.2
                )
                
                if order_id:
                    logger.debug(f"回测交易: {current_time} - {signal} -> {order_id}")
            
            # 定期更新性能指标
            if i % 100 == 0:
                self._update_performance()
                
                # 显示进度
                progress = (i / len(data)) * 100
                logger.info(f"回测进度: {progress:.1f}% - 当前价格: {current_price:.2f}")
    
    def _generate_backtest_report(self):
        """生成回测报告"""
        logger.info("生成回测报告")
        
        # 获取性能数据
        performance = self.performance_analyzer.get_performance_metrics()
        portfolio = self.trade_executor.get_portfolio_summary()
        
        # 打印报告
        print("\n" + "="*60)
        print("回测报告")
        print("="*60)
        print(f"初始资金: ${portfolio['initial_balance']:,.2f}")
        print(f"最终价值: ${portfolio['total_value']:,.2f}")
        print(f"总收益: ${portfolio['total_pnl']:,.2f} ({portfolio['total_return_pct']:.2f}%)")
        print(f"总交易次数: {portfolio['total_trades']}")
        print(f"胜率: {portfolio['win_rate']:.2f}%")
        print(f"总手续费: ${portfolio['total_commission']:,.2f}")
        
        if performance:
            print(f"最大回撤: {performance.get('max_drawdown', 0):.2f}%")
            print(f"夏普比率: {performance.get('sharpe_ratio', 0):.2f}")
            print(f"年化收益率: {performance.get('annual_return', 0):.2f}%")
        
        print("="*60)
        
        # 生成图表
        self.performance_analyzer.plot_performance_chart()
        self.performance_analyzer.plot_trades_chart()
    
    def _update_performance(self):
        """更新性能指标"""
        try:
            # 获取投资组合数据
            portfolio = self.trade_executor.get_portfolio_summary()
            
            # 更新性能分析器
            self.performance_analyzer.update_metrics(
                total_value=portfolio['total_value'],
                timestamp=datetime.now()
            )
            
            # 定期记录性能日志
            if self.start_time and (datetime.now() - self.start_time).seconds % 300 == 0:  # 每5分钟
                performance = self.performance_analyzer.get_performance_metrics()
                logger.info(f"性能更新 - 总价值: ${portfolio['total_value']:,.2f}, "
                          f"总收益: {portfolio['total_return_pct']:.2f}%, "
                          f"胜率: {portfolio['win_rate']:.2f}%")
                
        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")
    
    def stop(self):
        """停止机器人"""
        logger.info("正在停止交易机器人...")
        
        self.is_running = False
        self.auto_trading_enabled = False
        
        # 停止WebSocket连接
        self.data_collector.stop_websocket()
        
        # 停止WebSocket服务器
        self.websocket_server.stop_server()
        
        # 取消所有挂单
        open_orders = self.trade_executor.get_open_orders()
        for order in open_orders:
            self.trade_executor.cancel_order(order.id)
            
        # 生成最终报告
        self._print_final_summary()
        
        logger.info("交易机器人已停止")
    
    def _print_final_summary(self):
        """打印最终摘要"""
        portfolio = self.trade_executor.get_portfolio_summary()
        positions = self.trade_executor.get_positions()
        
        print("\n" + "="*50)
        print("交易机器人运行摘要")
        print("="*50)
        print(f"运行时间: {datetime.now() - self.start_time if self.start_time else 'N/A'}")
        print(f"运行模式: {self.mode.upper()}")
        print(f"总价值: ${portfolio['total_value']:,.2f}")
        print(f"总收益: ${portfolio['total_pnl']:,.2f} ({portfolio['total_return_pct']:.2f}%)")
        print(f"总交易: {portfolio['total_trades']}")
        print(f"胜率: {portfolio['win_rate']:.2f}%")
        
        if positions:
            print("\n当前持仓:")
            for symbol, position in positions.items():
                print(f"  {symbol}: {position.quantity:.6f} @ ${position.avg_price:.2f}")
        
        print("="*50)

def setup_signal_handlers(bot: TradingBot):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logger.info(f"接收到信号 {signum}，正在优雅退出...")
        bot.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='虚拟加密货币交易机器人')
    parser.add_argument('--mode', choices=['paper', 'backtest', 'auto'], 
                       default='paper', help='运行模式')
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT', 'ETHUSDT'],
                       help='交易对列表')
    parser.add_argument('--strategy', default='dual_ma',
                       help='交易策略')
    parser.add_argument('--start-date', default='2023-01-01',
                       help='回测开始日期')
    parser.add_argument('--end-date', default='2023-12-31',
                       help='回测结束日期')
    parser.add_argument('--auto-trading', action='store_true',
                       help='启用自动交易')
    
    args = parser.parse_args()
    
    # 创建机器人实例
    bot = TradingBot()
    
    # 设置信号处理器
    setup_signal_handlers(bot)
    
    # 设置策略
    if not bot.strategy_manager.set_active_strategy(args.strategy):
        logger.error(f"策略不存在: {args.strategy}")
        return
    
    try:
        if args.mode == 'backtest':
            # 回测模式
            bot.start_backtest(args.symbols, args.start_date, args.end_date)
            
        elif args.mode == 'auto':
            # 自动交易模式
            bot.start_paper_trading(args.symbols, auto_trading=True)
            
        else:
            # 模拟交易模式
            bot.start_paper_trading(args.symbols, auto_trading=args.auto_trading)
            
    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        bot.stop()

if __name__ == "__main__":
    # 确保数据和日志目录存在
    import os
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 启动程序
    main()