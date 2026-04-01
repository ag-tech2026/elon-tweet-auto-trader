#!/usr/bin/env python3
"""
Research Engine — analyzes trading history to discover patterns.

Tracks performance by:
- Market category (crypto, politics, sports, etc.)
- Entry price bucket (t1: 0-10¢, t2: 10-20¢, t3: 20-30¢, t4: 30-40¢)
- Timeframe (days to resolution)
- Liquidity ranges
- Volume ranges

Outputs recommendations for parameter tuning.
"""
import json, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
JFILE = ROOT / "data" / "journals" / "strategy_journal.json"
RFILE = STATE / "research.json"
(STATE / "research" / "backtests").mkdir(parents=True, exist_ok=True)

PRICE_BUCKETS = {
    "t1": (0.00, 0.10),   # 0-10¢ — highest ROI, highest risk
    "t2": (0.10, 0.20),   # 10-20¢
    "t3": (0.20, 0.30),   # 20-30¢
    "t4": (0.30, 0.45),   # 30-40¢ — lower ROI, safer
}

def load_journal():
    if not JFILE.exists():
        return []
    with open(JFILE) as f:
        return json.load(f)

def load_state():
    sfile = STATE / "state.json"
    if not sfile.exists():
        return {}
    with open(sfile) as f:
        return json.load(f)

def load_research():
    if not RFILE.exists():
        return {}
    with open(RFILE) as f:
        return json.load(f)

def save_research(r):
    r["updated_at"] = datetime.now().isoformat()
    RFILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RFILE, "w") as f:
        json.dump(r, f, indent=2)

def get_price_bucket(price):
    """Convert entry price to bucket."""
    if price <= 0.10: return "t1"
    if price <= 0.20: return "t2"
    if price <= 0.30: return "t3"
    return "t4"

def analyze():
    """Full research analysis — returns research dict with insights."""
    jl = load_journal()
    state = load_state()
    prev = load_research()

    # Closed trades (tp or sl)
    closed = [x for x in jl if x.get("t") in ("tp", "sl")]
    opened = [x for x in jl if x.get("t") == "open"]

    total_trades = len(closed)
    wins = sum(1 for x in closed if x["t"] == "tp")
    losses = sum(1 for x in closed if x["t"] == "sl")
    win_rate = wins / total_trades if total_trades > 0 else 0.0

    # Win by price bucket
    bucket_stats = {b: {"wins": 0, "losses": 0, "trades": 0, "avg_pnl": 0.0} for b in PRICE_BUCKETS}
    # Win by category
    cat_stats = {}
    # Win by outcome (Yes vs No)
    outcome_stats = {"Yes": {"wins": 0, "losses": 0}, "No": {"wins": 0, "losses": 0}}

    for trade in closed:
        pnl = trade.get("p", 0)
        is_win = trade.get("t") == "tp"
        pr = trade.get("pr", "")
        cat = trade.get("cat", "general")

        # Price bucket analysis
        if pr in bucket_stats:
            bucket_stats[pr]["trades"] += 1
            if is_win:
                bucket_stats[pr]["wins"] += 1
            else:
                bucket_stats[pr]["losses"] += 1
            bucket_stats[pr]["avg_pnl"] = (
                (bucket_stats[pr]["avg_pnl"] * (bucket_stats[pr]["trades"] - 1) + pnl)
                / bucket_stats[pr]["trades"]
            )

        # Category analysis
        if cat not in cat_stats:
            cat_stats[cat] = {"wins": 0, "losses": 0, "trades": 0, "avg_pnl": 0.0}
        cat_stats[cat]["trades"] += 1
        if is_win:
            cat_stats[cat]["wins"] += 1
        else:
            cat_stats[cat]["losses"] += 1
        cat_stats[cat]["avg_pnl"] = (
            (cat_stats[cat]["avg_pnl"] * (cat_stats[cat]["trades"] - 1) + pnl)
            / cat_stats[cat]["trades"]
        )

        # Position metadata (from state)
        slug = trade.get("s", "")
        if slug in state.get("pos", {}):
            pos = state["pos"][slug]
        else:
            pos = {}
        
        o = pos.get("o", "Yes")  # outcome
        if o in outcome_stats:
            if is_win:
                outcome_stats[o]["wins"] += 1
            else:
                outcome_stats[o]["losses"] += 1

    # Calculate performance scores
    bucket_scores = {}
    for b, stats in bucket_stats.items():
        trades = stats["trades"]
        if trades >= 3:  # need minimum sample size
            wr = stats["wins"] / trades if trades > 0 else 0.5
            bucket_scores[b] = {
                "win_rate": round(wr, 3),
                "trades": trades,
                "avg_pnl": round(stats["avg_pnl"], 2),
                "recommendation": "boost" if wr > 0.6 else "cut" if wr < 0.4 else "hold"
            }
    
    cat_scores = {}
    for cat, stats in cat_stats.items():
        trades = stats["trades"]
        if trades >= 2:
            wr = stats["wins"] / trades if trades > 0 else 0.5
            cat_scores[cat] = {
                "win_rate": round(wr, 3),
                "trades": trades,
                "avg_pnl": round(stats["avg_pnl"], 2),
                "recommendation": "focus" if wr > 0.65 else "avoid" if wr < 0.35 else "neutral"
            }

    outcome_scores = {}
    for o, stats in outcome_stats.items():
        total = stats["wins"] + stats["losses"]
        if total >= 3:
            wr = stats["wins"] / total
            outcome_scores[o] = {
                "win_rate": round(wr, 3),
                "total": total,
                "wins": stats["wins"],
                "losses": stats["losses"]
            }

    # Generate recommendations
    recommendations = []
    
    # Price bucket recommendations
    for b, sc in bucket_scores.items():
        if sc["recommendation"] == "boost":
            recommendations.append(f"✅ Price bucket {b} ({sc['win_rate']:.0%} WR, {sc['trades']} trades) — performing well")
        elif sc["recommendation"] == "cut":
            recommendations.append(f"⚠️ Price bucket {b} ({sc['win_rate']:.0%} WR, {sc['trades']} trades) — underperforming")
    
    # Category recommendations
    for cat, sc in cat_scores.items():
        if sc["recommendation"] == "focus":
            recommendations.append(f"🎯 Category '{cat}' ({sc['win_rate']:.0%} WR, {sc['trades']} trades) — strong performer")
        elif sc["recommendation"] == "avoid":
            recommendations.append(f"🚫 Category '{cat}' ({sc['win_rate']:.0%} WR, {sc['trades']} trades) — weak performer")

    # Research result
    research = {
        "summary": {
            "total_runs": state.get("runs", 0),
            "closed_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 3),
            "total_pnl": state.get("t_pnl", 0.0),
            "daily_pnl": state.get("d_pnl", 0.0),
            "open_positions": len(state.get("pos", {})),
        },
        "by_price_bucket": bucket_scores,
        "by_category": cat_scores,
        "by_outcome": outcome_scores,
        "recommendations": recommendations,
        "updated_at": datetime.now().isoformat(),
    }

    return research

def print_report(r=None):
    """Print a human-readable research report."""
    if r is None:
        r = analyze()
    
    print("=" * 60)
    print("🔬 POLYMARKET RESEARCH REPORT")
    print("=" * 60)
    
    s = r["summary"]
    print(f"\n📊 SUMMARY")
    print(f"  Runs: {s['total_runs']}")
    print(f"  Closed trades: {s['closed_trades']}")
    print(f"  Win rate: {s['win_rate']:.1%}")
    print(f"  Total P&L: ${s['total_pnl']:+.2f}")
    print(f"  Daily P&L: ${s['daily_pnl']:+.2f}")
    print(f"  Open positions: {s['open_positions']}")

    print(f"\n🎯 BY PRICE BUCKET")
    for b, sc in r.get("by_price_bucket", {}).items():
        print(f"  {b}: {sc['win_rate']:.0%} WR ({sc['trades']} trades, ${sc['avg_pnl']:+.2f} avg) → {sc['recommendation']}")

    print(f"\n📂 BY CATEGORY")
    for cat, sc in r.get("by_category", {}).items():
        print(f"  {cat}: {sc['win_rate']:.0%} WR ({sc['trades']} trades, ${sc['avg_pnl']:+.2f} avg) → {sc['recommendation']}")

    print(f"\n🔄 BY OUTCOME")
    for o, sc in r.get("by_outcome", {}).items():
        print(f"  {o}: {sc['win_rate']:.0%} WR ({sc['total']} trades)")

    print(f"\n💡 RECOMMENDATIONS")
    if r.get("recommendations"):
        for rec in r["recommendations"]:
            print(f"  {rec}")
    else:
        print("  (Need more closed trades for meaningful analysis — target: 5+)")
    
    print("=" * 60)
    return r

if __name__ == "__main__":
    r = analyze()
    save_research(r)
    print_report(r)
