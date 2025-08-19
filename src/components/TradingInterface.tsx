import React, { useState, useEffect } from 'react';
import { Play, Pause, Settings, AlertTriangle, CheckCircle } from 'lucide-react';

interface TradingInterfaceProps {
  isAutoTrading: boolean;
  onToggleAutoTrading: () => void;
  currentPrice: number;
  onManualTrade?: (side: 'BUY' | 'SELL', amount: number) => void;
}

interface Strategy {
  name: string;
  shortMA: number;
  longMA: number;
  stopLoss: number;
  takeProfit: number;
  enabled: boolean;
}

const TradingInterface: React.FC<TradingInterfaceProps> = ({
  isAutoTrading,
  onToggleAutoTrading,
  currentPrice,
  onManualTrade
}) => {
  const [strategy, setStrategy] = useState<Strategy>({
    name: '双均线策略',
    shortMA: 10,
    longMA: 30,
    stopLoss: 2.0,
    takeProfit: 5.0,
    enabled: true
  });

  const [manualTradeAmount, setManualTradeAmount] = useState<number>(0.01);
  const [showSettings, setShowSettings] = useState(false);
  const [lastSignal, setLastSignal] = useState<{type: string, time: Date, strength: number} | null>(null);

  // 模拟策略信号生成
  useEffect(() => {
    if (isAutoTrading && currentPrice > 0) {
      const interval = setInterval(() => {
        // 模拟策略信号（实际应该从Python后端获取）
        const random = Math.random();
        if (random > 0.95) { // 5%概率生成信号
          const signalType = random > 0.975 ? 'BUY' : 'SELL';
          const strength = 0.6 + Math.random() * 0.4; // 0.6-1.0的信号强度
          
          setLastSignal({
            type: signalType,
            time: new Date(),
            strength: strength
          });
        }
      }, 5000); // 每5秒检查一次

      return () => clearInterval(interval);
    }
  }, [isAutoTrading, currentPrice]);

  const handleManualTrade = (side: 'BUY' | 'SELL') => {
    if (onManualTrade && manualTradeAmount > 0) {
      onManualTrade(side, manualTradeAmount);
    }
  };

  const updateStrategy = (field: keyof Strategy, value: any) => {
    setStrategy(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="space-y-6">
      {/* 自动交易控制 */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">自动交易控制</h3>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center justify-center mb-6">
          <button
            onClick={onToggleAutoTrading}
            className={`flex items-center space-x-3 px-8 py-4 rounded-xl font-semibold text-lg transition-all transform hover:scale-105 ${
              isAutoTrading
                ? 'bg-red-600 hover:bg-red-700 text-red-100 shadow-red-500/25'
                : 'bg-green-600 hover:bg-green-700 text-green-100 shadow-green-500/25'
            } shadow-lg`}
          >
            {isAutoTrading ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
            <span>{isAutoTrading ? '停止自动交易' : '启动自动交易'}</span>
          </button>
        </div>

        {/* 策略状态 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <div className={`w-2 h-2 rounded-full ${strategy.enabled ? 'bg-green-400' : 'bg-gray-400'}`}></div>
              <span className="text-sm font-medium">策略状态</span>
            </div>
            <div className="text-xs text-gray-400">{strategy.name}</div>
            <div className={`text-sm font-semibold ${isAutoTrading ? 'text-green-400' : 'text-gray-400'}`}>
              {isAutoTrading ? '运行中' : '已停止'}
            </div>
          </div>

          <div className="bg-gray-700 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-yellow-400" />
              <span className="text-sm font-medium">最新信号</span>
            </div>
            {lastSignal ? (
              <div>
                <div className={`text-sm font-semibold ${
                  lastSignal.type === 'BUY' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {lastSignal.type} ({(lastSignal.strength * 100).toFixed(0)}%)
                </div>
                <div className="text-xs text-gray-400">
                  {lastSignal.time.toLocaleTimeString()}
                </div>
              </div>
            ) : (
              <div className="text-sm text-gray-400">等待信号...</div>
            )}
          </div>
        </div>
      </div>

      {/* 策略设置 */}
      {showSettings && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h4 className="text-lg font-semibold mb-4">策略参数设置</h4>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                短期均线周期
              </label>
              <input
                type="number"
                value={strategy.shortMA}
                onChange={(e) => updateStrategy('shortMA', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="1"
                max="50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                长期均线周期
              </label>
              <input
                type="number"
                value={strategy.longMA}
                onChange={(e) => updateStrategy('longMA', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="10"
                max="200"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                止损百分比 (%)
              </label>
              <input
                type="number"
                value={strategy.stopLoss}
                onChange={(e) => updateStrategy('stopLoss', parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="0.1"
                max="10"
                step="0.1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                止盈百分比 (%)
              </label>
              <input
                type="number"
                value={strategy.takeProfit}
                onChange={(e) => updateStrategy('takeProfit', parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                min="0.1"
                max="20"
                step="0.1"
              />
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
              保存设置
            </button>
          </div>
        </div>
      )}

      {/* 手动交易 */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h4 className="text-lg font-semibold mb-4">手动交易</h4>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              交易数量 (BTC)
            </label>
            <input
              type="number"
              value={manualTradeAmount}
              onChange={(e) => setManualTradeAmount(parseFloat(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="0.001"
              max="10"
              step="0.001"
            />
            <div className="text-xs text-gray-400 mt-1">
              约 ${(manualTradeAmount * currentPrice).toFixed(2)} USDT
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => handleManualTrade('BUY')}
              disabled={isAutoTrading}
              className="flex items-center justify-center space-x-2 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
            >
              <CheckCircle className="h-4 w-4" />
              <span>买入</span>
            </button>

            <button
              onClick={() => handleManualTrade('SELL')}
              disabled={isAutoTrading}
              className="flex items-center justify-center space-x-2 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
            >
              <AlertTriangle className="h-4 w-4" />
              <span>卖出</span>
            </button>
          </div>

          {isAutoTrading && (
            <div className="text-xs text-yellow-400 text-center">
              自动交易模式下手动交易已禁用
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TradingInterface;