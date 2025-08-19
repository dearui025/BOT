import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, Wifi, WifiOff } from 'lucide-react';

interface MarketData {
  symbol: string;
  price: string;
  priceChange: string;
  priceChangePercent: string;
  volume: string;
  high: string;
  low: string;
  timestamp: number;
}

const RealTimeData: React.FC = () => {
  const [data, setData] = useState<MarketData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    const fetchData = async () => {
      try {
        const apiUrl = window.location.hostname === 'localhost' 
          ? 'http://localhost:8001/api/ticker'
          : `http://${window.location.hostname}:8001/api/ticker`;
        
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data) {
          setData(result.data);
          setIsConnected(true);
          setError(null);
        } else {
          throw new Error('Invalid response format');
        }
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
        setIsConnected(false);
      }
    };

    // Initial fetch
    fetchData();
    
    // Set up polling every 2 seconds
    intervalId = setInterval(fetchData, 2000);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, []);

  const formatNumber = (numStr: string, decimals: number = 2) => {
    const num = parseFloat(numStr);
    return num.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  };

  const formatPercentage = (percentStr: string) => {
    const num = parseFloat(percentStr);
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
  };

  const getChangeColor = (changeStr: string) => {
    const change = parseFloat(changeStr);
    if (change > 0) return 'text-green-500';
    if (change < 0) return 'text-red-500';
    return 'text-gray-500';
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">实时行情</h2>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span className="text-sm text-red-600">连接失败</span>
          </div>
        </div>
        <div className="text-center py-8">
          <p className="text-red-500 mb-2">获取数据失败</p>
          <p className="text-sm text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">实时行情</h2>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <span className="text-sm text-yellow-600">加载中...</span>
          </div>
        </div>
        <div className="text-center py-8">
          <p className="text-gray-500">正在获取实时数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">实时行情</h2>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`}></div>
          <span className={`text-sm ${
            isConnected ? 'text-green-600' : 'text-red-600'
          }`}>
            {isConnected ? '已连接' : '连接中...'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-1">交易对</p>
          <p className="text-lg font-semibold text-gray-800">{data.symbol}</p>
        </div>
        
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-1">当前价格</p>
          <p className="text-lg font-semibold text-gray-800">
            ${formatNumber(data.price)}
          </p>
        </div>
        
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-1">24h涨跌</p>
          <p className={`text-lg font-semibold ${getChangeColor(data.priceChangePercent)}`}>
            {formatPercentage(data.priceChangePercent)}
          </p>
        </div>
        
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-1">24h成交量</p>
          <p className="text-lg font-semibold text-gray-800">
            {formatNumber(data.volume, 0)}
          </p>
        </div>
        
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-1">24h最高</p>
          <p className="text-lg font-semibold text-gray-800">
            ${formatNumber(data.high)}
          </p>
        </div>
        
        <div className="text-center">
          <p className="text-sm text-gray-500 mb-1">24h最低</p>
          <p className="text-lg font-semibold text-gray-800">
            ${formatNumber(data.low)}
          </p>
        </div>
        
        <div className="text-center md:col-span-2">
          <p className="text-sm text-gray-500 mb-1">更新时间</p>
          <p className="text-sm text-gray-600">
            {new Date(data.timestamp).toLocaleTimeString()}
          </p>
        </div>
      </div>
    </div>
  );
};

export default RealTimeData;