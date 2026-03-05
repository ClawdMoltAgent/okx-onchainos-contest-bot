# OKX OnchainOS Contest Bot (Base)

可直接运行的 Base 链交易机器人（默认 dry-run，支持 live 模式）。

## 功能
- 链：**Base(8453)**
- 接口：OKX OnchainOS DEX market + quote + swap
- 策略：短均线/长均线动量 + 阈值过滤
- 自动选币：候选池实时评分并自动切换交易代币
- 风控：单笔限额、总仓位限额、日亏损限额
- 运行：循环轮询、状态落盘到 `data/runtime_state.json`

## 快速开始
```bash
cd okx-onchainos-contest-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## 配置 `.env`
必填：
- `OKX_API_KEY`
- `OKX_SECRET_KEY`
- `OKX_PASSPHRASE`
- `EVM_ADDRESS`

可选：
- `OKX_PROJECT_ID`（如果你的账户要求）
- `EVM_PRIVATE_KEY`（后续如果要本地签名广播）

## 运行
### 1) 模拟模式（推荐先跑）
```bash
okx-contest-bot --dry-run
```

### 2) 实盘模式
```bash
okx-contest-bot --live
```

### 3) 刷新 Base 自动代币池（OKX可交易数据）
```bash
okx-contest-bot --refresh-universe
```

### 4) 盈利验证报告
```bash
okx-contest-bot --report
```
报告读取 `data/trades.jsonl`，输出：总交易事件、平仓次数、胜率、已实现PnL、单次平均PnL、最大回撤、Sharpe（按交易）、Profit Factor、按日PnL。

可选保存 JSON：
```bash
okx-contest-bot --report --report-json ./data/report.json
```

## 参数建议（初始）
- `PER_TRADE_USD=20`
- `RISK_MAX_POSITION_USD=40`
- `RISK_MAX_DAILY_LOSS_USD=20`
- `POLL_INTERVAL_SEC=30`

## 目录
- `src/okx_contest_bot/engine.py`：主循环 + 下单流程
- `src/okx_contest_bot/okx_client.py`：OKX API 封装 + 签名
- `src/okx_contest_bot/strategy.py`：策略逻辑
- `src/okx_contest_bot/risk.py`：风控
- `docs/STRATEGY.md`：策略规范（GitHub可审阅版）
- `docs/FLOW.md`：执行流程与失败处理

## GitHub 标准化
- CI: `.github/workflows/ci.yml`（push/PR 自动跑 pytest）
- PR 模板: `.github/pull_request_template.md`
- Issue 模板: `.github/ISSUE_TEMPLATE/*`

## 说明
- live 模式当前实现为“构建交易并提交 swap 请求”流程；若你的 API 版本字段不同，按 OKX 最新文档调整 `okx_client.py` 对应 path/字段即可。
- 建议先用 `MAX_CYCLES=20` 做小样本验证，再改成 0 持续运行。
- 执行层已加入 preflight 模拟、gas buffer、以及失败后的高滑点重试，降低链上回滚概率。
