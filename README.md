# Polymarket Crypto Trader

Autonomous micro-trading bot for Polymarket prediction markets. Uses **only** Bullpen CLI — no external APIs, no sentiment scraping.

## How It Works

```
Bullpen CLI discover → Score opportunities → Safety checks → Micro-trades ($1.00)
```

1. **Discover** — fetches active crypto markets via `bullpen polymarket discover crypto`
2. **Score** — finds mispriced markets (cheap YES ≤40¢ or expensive YES ≥85%)
3. **Safety** — checks balance, daily loss limit, position count
4. **Trade** — places $1 orders ranked by max ROI

## Strategy

| Signal | Action | Example |
|--------|--------|---------|
| YES price 5¢-40¢ | Buy YES | ETH $8k by 2026 @ 5% → 19x ROI |
| YES price ≥85% | Buy NO | BTC >$60k tomorrow @ 97% → short |
| YES 41¢-84% | Skip | Efficient market, no edge |

## Usage

```bash
# Check status (no orders)
python3 polymarket_trader.py --status

# Dry run (finds opportunities, no real orders)
python3 polymarket_trader.py

# LIVE trading (REAL orders — be careful!)
python3 polymarket_trader.py --live
```

## Safety Guards

- **Trade size**: $1.00 per order (configurable)
- **Daily loss limit**: $3.00 — stops after this loss
- **Max trades per run**: 3 (keeps it conservative)
- **Min liquidity**: $200k (ensures orders fill)
- **Balance check**: verifies funds before any trade

## Configuration

Edit these at the top of `polymarket_trader.py`:

```python
TRADE_SIZE_USD      = 1.00       # $1 per trade
MAX_DAILY_LOSS_USD  = 3.00       # stop after $3 loss
MAX_TRADES_PER_RUN  = 3          # max orders per run
MIN_LIQUIDITY       = 200000     # $200k min
MIN_VOLUME_24H      = 100000     # $100k min daily
YES_BUY_MIN         = 0.05       # buy YES ≥ 5¢
YES_BUY_MAX         = 0.40       # buy YES ≤ 40¢
```

## Cron Schedule

```bash
# Every 3 hours — dry run (opportunities only)
0 */3 * * * cd /path/to/polymarket-crypto-trader && python3 polymarket_trader.py >> data/logs/cron.log 2>&1

# Every 3 hours — live trading (uncomment when ready)
# 0 */3 * * * cd /path/to/polymarket-crypto-trader && python3 polymarket_trader.py --live >> data/logs/cron.log 2>&1
```

## Dependencies

- **Bullpen CLI** — authenticated with your Polymarket account
- **Python 3.8+** — stdlib only, zero pip packages

## Files

| File | Purpose |
|------|---------|
| `polymarket_trader.py` | Everything in one script |
| `data/logs/trader_*.log` | Timestamped run logs |
| `data/trade-journal/trades_*.csv` | Every order logged |
