# 虚拟加密货币交易机器人

一个功能完整的虚拟加密货币交易机器人，支持实时数据获取、自动交易执行、策略回测和性能评估。

## 🚀 主要功能

- **实时数据获取**: 通过币安WebSocket API获取实时行情数据
- **自动交易执行**: 基于双均线策略的自动交易系统
- **模拟交易环境**: 安全的虚拟资金交易，无真实资金风险
- **性能评估**: 胜率、收益率、最大回撤等关键指标计算
- **风险控制**: 止盈止损、最大仓位限制等风险管理功能
- **可视化界面**: 美观的Web界面展示交易状态和性能数据

## 📁 项目结构

```
crypto-trading-bot/
├── src/
│   ├── data_collector.py      # 数据获取模块
│   ├── trading_strategy.py    # 交易策略模块
│   ├── trade_executor.py      # 交易执行模块
│   ├── portfolio_manager.py   # 投资组合管理
│   ├── performance_analyzer.py # 性能分析模块
│   ├── risk_manager.py        # 风险管理模块
│   ├── logger_config.py       # 日志配置
│   ├── config.py             # 配置文件
│   └── main.py               # 主程序入口
├── data/                     # 数据存储目录
├── logs/                     # 日志文件目录
├── requirements.txt          # Python依赖
└── README.md                # 项目说明
```

## 🛠️ 安装和配置

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 配置币安API密钥

1. 登录币安账户，进入API管理页面
2. 创建新的API密钥，只需要"读取"权限
3. 在 `src/config.py` 中配置您的API密钥：

```python
BINANCE_API_KEY = "your_api_key_here"
BINANCE_SECRET_KEY = "your_secret_key_here"
```

### 3. 运行交易机器人

```bash
# 启动实时模式
python src/main.py --mode live

# 启动自动交易模式
python src/main.py --mode auto

# 启动回测模式
python src/main.py --mode backtest
```

## 📊 交易策略

### 双均线交叉策略

- **买入信号**: 短期均线上穿长期均线
- **卖出信号**: 短期均线下穿长期均线
- **默认参数**: 10周期短期均线，30周期长期均线
- **风险控制**: 2%止损，5%止盈，最大50%仓位

### 自定义策略扩展

您可以在 `trading_strategy.py` 中添加新的策略：

```python
class RSIStrategy(TradingStrategy):
    def generate_signal(self, data):
        # 实现RSI策略逻辑
        pass
```

## 🔧 配置参数

在 `config.py` 中可以调整以下参数：

- `TRADING_PAIRS`: 交易对列表
- `INITIAL_BALANCE`: 初始虚拟资金
- `MAX_POSITION_SIZE`: 最大仓位比例
- `STOP_LOSS_PCT`: 止损百分比
- `TAKE_PROFIT_PCT`: 止盈百分比
- `UPDATE_INTERVAL`: 数据更新间隔

## 📈 性能监控

机器人提供以下性能指标：

- **总收益率**: 投资组合总收益百分比
- **胜率**: 盈利交易占总交易的比例
- **最大回撤**: 资产净值的最大跌幅
- **夏普比率**: 风险调整后收益指标
- **年化收益率**: 换算为年化的收益率

## 🛡️ 风险控制

- **模拟交易**: 所有交易均为虚拟，无真实资金风险
- **位置管理**: 限制单笔交易和总仓位大小
- **止损机制**: 自动止损保护资金
- **API限制**: 遵守币安API调用频率限制

## 📝 日志记录

所有交易活动和系统事件都会记录在日志文件中：

- `logs/trading.log`: 交易记录
- `logs/system.log`: 系统事件
- `logs/error.log`: 错误信息

## ⚠️ 注意事项

1. **仅用于学习**: 此机器人仅供学习和测试使用
2. **虚拟交易**: 不涉及真实资金交易
3. **API安全**: 妥善保管API密钥，不要分享给他人
4. **风险提示**: 加密货币交易存在风险，请谨慎投资

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

MIT License