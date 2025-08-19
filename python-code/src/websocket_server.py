"""
WebSocket服务器模块
为前端提供实时市场数据的本地WebSocket服务
"""
import asyncio
import json
import threading
import time
from datetime import datetime
from typing import Dict, Set
import websockets
from websockets.server import WebSocketServerProtocol

from logger_config import get_logger

logger = get_logger('websocket_server')

class MarketDataWebSocketServer:
    """市场数据WebSocket服务器"""
    
    def __init__(self, host: str = 'localhost', port: int = 8000):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.is_running = False
        self.latest_data = {}
        
        logger.info(f"WebSocket服务器初始化: {host}:{port}")
    
    async def register_client(self, websocket: WebSocketServerProtocol):
        """注册新客户端"""
        self.clients.add(websocket)
        logger.info(f"新客户端连接: {websocket.remote_address}")
        
        # 发送最新数据给新连接的客户端
        if self.latest_data:
            try:
                await websocket.send(json.dumps(self.latest_data))
            except Exception as e:
                logger.error(f"发送初始数据失败: {e}")
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """注销客户端"""
        self.clients.discard(websocket)
        logger.info(f"客户端断开连接: {websocket.remote_address}")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """处理客户端连接"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                # 处理客户端消息（如果需要）
                logger.debug(f"收到客户端消息: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("客户端连接正常关闭")
        except Exception as e:
            logger.error(f"客户端连接错误: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def broadcast_data(self, data: Dict):
        """广播数据给所有客户端"""
        if not self.clients:
            return
        
        # 更新最新数据
        self.latest_data = data
        
        # 准备发送的消息
        message = json.dumps(data)
        
        # 广播给所有连接的客户端
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"广播数据失败: {e}")
                disconnected_clients.add(client)
        
        # 移除断开连接的客户端
        for client in disconnected_clients:
            self.clients.discard(client)
    
    def update_market_data(self, symbol: str, price: float, change: float, 
                          volume: float = 0, high: float = 0, low: float = 0):
        """更新市场数据（同步方法，供外部调用）"""
        data = {
            's': symbol,
            'c': str(price),
            'P': str(change),
            'v': str(volume),
            'h': str(high),
            'l': str(low),
            'timestamp': datetime.now().isoformat()
        }
        
        # 在事件循环中广播数据
        if self.is_running and hasattr(self, '_loop'):
            asyncio.run_coroutine_threadsafe(
                self.broadcast_data(data), 
                self._loop
            )
    
    async def start_server(self):
        """启动WebSocket服务器"""
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            self.is_running = True
            self._loop = asyncio.get_event_loop()
            
            logger.info(f"WebSocket服务器启动成功: ws://{self.host}:{self.port}")
            
            # 保持服务器运行
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}")
            self.is_running = False
    
    def start_in_thread(self):
        """在新线程中启动服务器"""
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_server())
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        logger.info("WebSocket服务器线程已启动")
    
    def stop_server(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            self.is_running = False
            logger.info("WebSocket服务器已停止")

# 全局服务器实例
_websocket_server = None

def get_websocket_server() -> MarketDataWebSocketServer:
    """获取WebSocket服务器实例"""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = MarketDataWebSocketServer()
    return _websocket_server