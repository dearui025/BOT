"""
数据获取模块
负责从币安API获取真实的实时和历史数据
"""
import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import pandas as pd
import websocket
from binance.client import Client
from binance.exceptions import BinanceAPIException
import numpy as np

from config import *
from logger_config import get_logger

logger = get_logger('data')

class BinanceDataCollector:
    """币安真实数据采集器"""
    
    def __init__(self):
        # 初始化币安客户端
        self.client = Client(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_SECRET_KEY,
            testnet=False  # 使用真实API获取真实数据
        )
        
        # WebSocket连接
        self.ws = None
        self.ws_thread = None
        self.is_running = False
        
        # 数据存储
        self.current_prices = {}
        self.kline_data = {}
        self.order_book = {}
        self.ticker_24hr = {}
        
        # 回调函数
        self.price_callbacks = []
        self.kline_callbacks = []
        
        logger.info("币安真实数据采集器初始化完成")
        
        # 立即获取一次当前价格
        self._fetch_initial_prices()
    
    def _fetch_initial_prices(self):
        """获取初始价格数据"""
        try:
            # 获取所有交易对的24小时统计
            tickers = self.client.get_ticker()
            
            for ticker in tickers:
                symbol = ticker['symbol']
                if symbol in TRADING_PAIRS:
                    self.current_prices[symbol] = {
                        'price': float(ticker['lastPrice']),
                        'change': float(ticker['priceChangePercent']),
                        'volume': float(ticker['volume']),
                        'high': float(ticker['highPrice']),
                        'low': float(ticker['lowPrice']),
                        'timestamp': datetime.now()
                    }
                    
                    # 立即触发价格回调
                    for callback in self.price_callbacks:
                        try:
                            callback(symbol, float(ticker['lastPrice']), float(ticker['priceChangePercent']))
                        except Exception as e:
                            logger.error(f"价格回调函数错误: {e}")
            
            logger.info(f"成功获取 {len(self.current_prices)} 个交易对的初始价格")
            
        except Exception as e:
            logger.error(f"获取初始价格失败: {e}")
    
    def add_price_callback(self, callback: Callable):
        """添加价格更新回调函数"""
        self.price_callbacks.append(callback)
    
    def add_kline_callback(self, callback: Callable):
        """添加K线数据回调函数"""
        self.kline_callbacks.append(callback)
    
    def get_historical_klines(self, symbol: str, interval: str, 
                            start_time: str = None, end_time: str = None,
                            limit: int = 1000) -> pd.DataFrame:
        """获取真实历史K线数据"""
        try:
            logger.info(f"从币安获取真实历史K线数据: {symbol} {interval} {limit}条")
            
            # 计算时间范围
            if not start_time:
                start_time = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if not end_time:
                end_time = datetime.now().strftime('%Y-%m-%d')
            
            # 调用币安真实API
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_time,
                end_str=end_time,
                limit=limit
            )
            
            if not klines:
                logger.warning(f"未获取到 {symbol} 的K线数据")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                'ignore'
            ])
            
            # 数据类型转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = df[col].astype(float)
            
            # 计算技术指标
            df = self._calculate_indicators(df)
            
            logger.info(f"成功获取 {len(df)} 条真实K线数据，时间范围: {df['timestamp'].min()} - {df['timestamp'].max()}")
            return df
            
        except BinanceAPIException as e:
            logger.error(f"币安API获取历史数据失败: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"历史数据处理错误: {e}")
            return pd.DataFrame()
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if len(df) == 0:
            return df
        
        try:
            # 移动平均线
            df['ma_10'] = df['close'].rolling(window=10).mean()
            df['ma_20'] = df['close'].rolling(window=20).mean()
            df['ma_30'] = df['close'].rolling(window=30).mean()
            df['ma_50'] = df['close'].rolling(window=50).mean()
            
            # RSI指标
            df['rsi'] = self._calculate_rsi(df['close'], 14)
            
            # MACD指标
            macd_data = self._calculate_macd(df['close'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']
            
            # 布林带
            bb_data = self._calculate_bollinger_bands(df['close'], 20, 2)
            df['bb_upper'] = bb_data['upper']
            df['bb_middle'] = bb_data['middle']
            df['bb_lower'] = bb_data['lower']
            
            # 成交量移动平均
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            
            logger.debug(f"技术指标计算完成")
            return df
            
        except Exception as e:
            logger.error(f"技术指标计算错误: {e}")
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, 
                       slow: int = 26, signal: int = 9) -> Dict:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        histogram = macd - macd_signal
        
        return {
            'macd': macd,
            'signal': macd_signal,
            'histogram': histogram
        }
    
    def _calculate_bollinger_bands(self, prices: pd.Series, 
                                 period: int = 20, std_dev: int = 2) -> Dict:
        """计算布林带指标"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    def start_websocket(self, symbols: List[str], interval: str = '1m'):
        """启动币安WebSocket实时数据流"""
        if self.is_running:
            logger.warning("WebSocket已在运行")
            return
        
        self.is_running = True
        
        # 构建WebSocket URL
        streams = []
        for symbol in symbols:
            symbol_lower = symbol.lower()
            streams.append(f"{symbol_lower}@ticker")
            streams.append(f"{symbol_lower}@kline_{interval}")
        
        # 使用币安官方WebSocket地址
        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        logger.info(f"启动币安WebSocket连接: {ws_url}")
        logger.info(f"订阅数据流: {streams}")
        
        # 启动WebSocket线程
        self.ws_thread = threading.Thread(target=self._websocket_worker, args=(ws_url,))
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        logger.info("币安WebSocket实时数据流启动完成")
    
    def _websocket_worker(self, url: str):
        """WebSocket工作线程"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self._handle_websocket_message(data)
            except Exception as e:
                logger.error(f"WebSocket消息处理错误: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket错误: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.warning(f"币安WebSocket连接关闭: {close_status_code} - {close_msg}")
            if self.is_running:
                logger.info("尝试重新连接币安WebSocket...")
                time.sleep(WEBSOCKET_RECONNECT_DELAY)
                self._websocket_worker(url)
        
        def on_open(ws):
            logger.info("币安WebSocket连接建立成功")
        
        self.ws = websocket.WebSocketApp(
            url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        self.ws.run_forever()
    
    def _handle_websocket_message(self, data: Dict):
        """处理币安WebSocket消息"""
        try:
            if 'stream' not in data or 'data' not in data:
                return
            
            stream = data['stream']
            message_data = data['data']
            
            # 处理价格数据
            if '@ticker' in stream:
                self._handle_ticker_data(message_data)
            
            # 处理K线数据
            elif '@kline' in stream:
                self._handle_kline_data(message_data)
                
        except Exception as e:
            logger.error(f"WebSocket消息处理错误: {e}")
    
    def _handle_ticker_data(self, data: Dict):
        """处理币安价格推送数据"""
        symbol = data['s']
        price = float(data['c'])
        change = float(data['P'])
        volume = float(data['v'])
        high = float(data['h'])
        low = float(data['l'])
        
        # 更新当前价格
        self.current_prices[symbol] = {
            'price': price,
            'change': change,
            'volume': volume,
            'high': high,
            'low': low,
            'timestamp': datetime.now()
        }
        
        logger.debug(f"价格更新: {symbol} = ${price:.2f} ({change:+.2f}%)")
        
        # 调用价格回调函数
        for callback in self.price_callbacks:
            try:
                callback(symbol, price, change)
            except Exception as e:
                logger.error(f"价格回调函数错误: {e}")
    
    def _handle_kline_data(self, data: Dict):
        """处理币安K线数据"""
        kline = data['k']
        symbol = kline['s']
        
        # 只处理已完成的K线
        if not kline['x']:  # x表示K线是否已完成
            return
        
        kline_info = {
            'symbol': symbol,
            'timestamp': pd.to_datetime(kline['t'], unit='ms'),
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v'])
        }
        
        logger.debug(f"K线更新: {symbol} {kline_info['timestamp']} OHLC=({kline_info['open']:.2f}, {kline_info['high']:.2f}, {kline_info['low']:.2f}, {kline_info['close']:.2f})")
        
        # 更新K线数据
        if symbol not in self.kline_data:
            self.kline_data[symbol] = []
        
        self.kline_data[symbol].append(kline_info)
        
        # 保持数据长度限制
        if len(self.kline_data[symbol]) > 1000:
            self.kline_data[symbol] = self.kline_data[symbol][-1000:]
        
        # 调用K线回调函数
        for callback in self.kline_callbacks:
            try:
                callback(kline_info)
            except Exception as e:
                logger.error(f"K线回调函数错误: {e}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前真实价格"""
        if symbol in self.current_prices:
            return self.current_prices[symbol]['price']
        
        try:
            # 如果WebSocket未提供数据，使用币安REST API获取
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            logger.info(f"通过REST API获取 {symbol} 价格: ${price:.2f}")
            return price
        except Exception as e:
            logger.error(f"获取 {symbol} 当前价格失败: {e}")
            return None
    
    def get_current_market_data(self, symbol: str) -> Optional[Dict]:
        """获取当前完整市场数据"""
        if symbol in self.current_prices:
            return self.current_prices[symbol]
        
        try:
            # 使用24小时统计API获取完整数据
            ticker = self.client.get_ticker(symbol=symbol)
            market_data = {
                'price': float(ticker['lastPrice']),
                'change': float(ticker['priceChangePercent']),
                'volume': float(ticker['volume']),
                'high': float(ticker['highPrice']),
                'low': float(ticker['lowPrice']),
                'timestamp': datetime.now()
            }
            
            # 缓存数据
            self.current_prices[symbol] = market_data
            logger.info(f"通过REST API获取 {symbol} 完整市场数据")
            return market_data
            
        except Exception as e:
            logger.error(f"获取 {symbol} 市场数据失败: {e}")
            return None
    
    def get_recent_klines(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """获取最近的真实K线数据"""
        if symbol in self.kline_data and len(self.kline_data[symbol]) > 0:
            recent_data = self.kline_data[symbol][-limit:]
            df = pd.DataFrame(recent_data)
            return self._calculate_indicators(df)
        
        # 如果没有WebSocket数据，从币安API获取最新历史数据
        logger.info(f"WebSocket无数据，从API获取 {symbol} 最近K线数据")
        try:
            klines = self.client.get_klines(symbol=symbol, interval=DEFAULT_INTERVAL, limit=limit)
            
            if not klines:
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                'ignore'
            ])
            
            # 数据类型转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = df[col].astype(float)
            
            return self._calculate_indicators(df)
            
        except Exception as e:
            logger.error(f"获取最近K线数据失败: {e}")
            return pd.DataFrame()
    
    def stop_websocket(self):
        """停止WebSocket连接"""
        if self.is_running:
            self.is_running = False
            if self.ws:
                self.ws.close()
            logger.info("币安WebSocket连接已停止")
    
    def get_order_book(self, symbol: str, limit: int = 10) -> Dict:
        """获取真实订单簿数据"""
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)
            return {
                'bids': [[float(price), float(qty)] for price, qty in depth['bids']],
                'asks': [[float(price), float(qty)] for price, qty in depth['asks']],
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"获取 {symbol} 订单簿失败: {e}")
            return {'bids': [], 'asks': [], 'timestamp': datetime.now()}
    
    def test_connection(self) -> bool:
        """测试币安API连接"""
        try:
            # 测试连接
            status = self.client.get_system_status()
            server_time = self.client.get_server_time()
            
            logger.info(f"币安API连接测试成功")
            logger.info(f"系统状态: {status}")
            logger.info(f"服务器时间: {datetime.fromtimestamp(server_time['serverTime']/1000)}")
            
            return True
            
        except Exception as e:
            logger.error(f"币安API连接测试失败: {e}")
            return False

# 单例实例
data_collector = BinanceDataCollector()

def get_data_collector() -> BinanceDataCollector:
    """获取币安数据采集器实例"""
    return data_collector