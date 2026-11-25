"""Online personalized-gift store, adapted to a 16-year-old living on a kibbutz in the periphery.
Differences from online_store_sim.py:
 - Starts 1 Dec 2026 (Hanukkah first) and follows the Israeli calendar: school Sep-Jun, summer Jul-Aug
 - Limited hours: ~8 h/week in school, ~25 h/week in summer -> caps how many custom orders can be handled
 - Learning curve: first 6 months ads are less efficient (higher CPC, lower conversion)
 - Minor: parent/guardian is the legal owner; operating as an exempt dealer (no VAT charged, no VAT reclaimed)
   until turnover passes ~120k NIS; no national insurance under 18 (verify with an accountant)
 - No rent / no home-office cost (kibbutz), cheaper bookkeeping
 - Two strategies compared: FULL (put the ad money in from the start) vs STAGED (small test budget,
   switch product if the conversion rate is bad)
All numbers are assumptions, not market data."""
import random, statistics
from coffee_cart_sim import taxes

BUDGET = 20000
SETUP = 5000                       # store+domain 1,200 | mockups/brand 2,200 | samples 1,300 | registration 300
RESERVE = BUDGET - SETUP
FIXED_MONTH = 150 + 220 + 150 + 100   # platform, apps, bookkeeping (exempt dealer), tools
AOV = 150; PRODUCT_COST = 0.40; SHIP_COST = 18; FEE_PCT, FEE_FIX = 0.029, 1.2; REFUND = 0.045
MONTH_MULT = [0.9, 1.1, 1.2, 0.9, 1.1, 0.8, 0.7, 0.9, 1.3, 1.1, 1.2, 1.6]   # Jan..Dec
EXEMPT_LIMIT = 120000
PIVOT_COST = 900

def draw_cvr(r):
    u = r.random()
    return r.uniform(0.004, 0.009) if u < .35 else r.uniform(0.012, 0.02) if u < .8 else r.uniform(0.025, 0.04)

def run(seed, strategy):
    r = random.Random(seed)
    cvr = draw_cvr(r)
    cash = RESERVE; ad_daily = 60.0 if strategy == "full" else 25.0
    rev = cogs = ads = fees = fixed = 0.0
    orders_total = 0; repeat_pool = 0.0; cum_gross = 0.0; lost_orders = 0
    capped_days = []; window = []; pivots = 0; pv = po = 0; last_pivot = 0; monthly = []; m_net = 0.0
    for day in range(365):
        cal = (11 + int(day / 30.42)) % 12; seas = MONTH_MULT[cal]
        summer = cal in (6, 7)
        learn = min(1.0, day / 180)
        cpc = 1.2 * (1.3 if cal >= 9 else 1.0) * (1 + ad_daily / 900) ** 0.35 * (1.45 - 0.45 * learn)
        spend_cap = max(0, cash - 500)
        spend = min(ad_daily, spend_cap)
        exempt = cum_gross < EXEMPT_LIMIT
        vat = 1.0 if exempt else 1.17
        ad_cost = spend * (1.17 if exempt else 1.0)     # exempt dealer can't reclaim VAT on ads
        paid = spend / cpc
        organic = (3 + 0.04 * orders_total) * seas * (1.0 if day > 45 else 0.3)
        visitors = paid + organic
        fatigue = 1 - min(0.35, spend * 0.0004 * (day % 60) / 60)
        p = cvr * seas * fatigue * (0.85 + 0.15 * learn)
        n = sum(1 for _ in range(int(visitors)) if r.random() < p) if visitors < 2000 else int(visitors * p)
        n += int(repeat_pool * 0.004 + (r.random() < (repeat_pool * 0.004) % 1))
        # time cap: minutes per order ~3 (proof + customer chat); hours/week by season
        hours = 25 if summer else 8
        cap = int(hours / 7 * 60 / 3)
        capped_days.append(n >= 0.9 * cap); capped_days = capped_days[-14:]
        if n > cap: lost_orders += n - cap; n = cap + int((n - cap) * 0.3)   # some late orders still kept
        gross = n * AOV * r.uniform(0.9, 1.1); cum_gross += gross
        net_rev = gross / vat * (1 - REFUND)
        c = n * (AOV / 1.17 * PRODUCT_COST * (1.17 if exempt else 1.0) + SHIP_COST)
        f = n * FEE_FIX + gross * FEE_PCT
        cash += net_rev - c - f - ad_cost
        rev += net_rev; cogs += c; fees += f; ads += ad_cost
        m_net += net_rev - c - f - ad_cost
        orders_total += n; repeat_pool += n * 0.9
        window.append(net_rev - c - f - ad_cost); window = window[-14:]
        pv += paid + organic; po += sum([0]) + n
        if day % 14 == 13 and spend > 0:
            contrib = sum(window)
            if contrib > 0: ad_daily = ad_daily if sum(capped_days) >= 3 else min(ad_daily * 1.25, 1000)   # no scaling when out of time
            elif contrib < -0.3 * spend * 14: ad_daily = max(15, ad_daily * 0.6)
            else: ad_daily = max(15, ad_daily * 0.9)
        # STAGED: every 30 days after a launch/pivot, judge conversion and swap product if poor
        if strategy == "staged" and (day - last_pivot) % 30 == 29 and day > 0:
            if pv >= 400 and po / pv < 0.009 and pivots < 4 and cash > 4000:
                cash -= PIVOT_COST; fixed += PIVOT_COST
                cvr = draw_cvr(r); pivots += 1; last_pivot = day; ad_daily = 25.0
                orders_total = int(orders_total * 0.5); pv = po = 0
            elif (day - last_pivot) >= 59: pv = po = 0 if pivots >= 4 else pv
        if (day + 1) % 30 == 0:
            fx = FIXED_MONTH + (r.randint(300, 1500) if r.random() < .1 else 0)
            cash -= fx; fixed += fx
            monthly.append((len(monthly) + 1, rev, ads, fx, m_net - fx, cash)); m_net = 0
    op = rev - cogs - fees - ads - fixed
    tax = 0.0
    if op > 0:
        _, tax, _ = taxes(op + 3000 + 5100)       # income tax only; no NI under 18 (verify)
    take = op - tax
    return dict(cvr=cvr, rev=rev, op=op, take=take, net=take - SETUP, cash=cash, orders=orders_total,
                pivots=pivots, lost=lost_orders, broke=cash < 1000, monthly=monthly, ads=ads)

def summarize(strategy, N=1000):
    runs = sorted((run(s, strategy) for s in range(N)), key=lambda x: x["net"])
    nets = [x["net"] for x in runs]
    print(f"\n=== Strategy: {strategy.upper()} ({N} simulated years, net = after tax and the {SETUP:,} setup) ===")
    print(f"median {statistics.median(nets):,.0f} | p10 {nets[N//10]:,.0f} | p90 {nets[9*N//10]:,.0f} | best {nets[-1]:,.0f} | worst {nets[0]:,.0f}")
    print(f"profitable after setup: {sum(x>0 for x in nets)/N:.0%} | cash nearly gone: {sum(x['broke'] for x in runs)/N:.0%}"
          f" | avg product swaps: {statistics.mean(x['pivots'] for x in runs):.1f}"
          f" | avg lost orders (no time): {statistics.mean(x['lost'] for x in runs):.0f}")
    return runs

if __name__ == "__main__":
    print(f"Setup {SETUP:,} | cash for ads/working capital {RESERVE:,}")
    a = summarize("full"); b = summarize("staged")
    med = b[len(b)//2]
    print("\n== Median STAGED year, month by month ==")
    print("month  revenue(cum)  ads(cum)  month-profit   cash")
    for m in med["monthly"]: print(f"{m[0]:>5} {m[1]:>11,.0f} {m[2]:>9,.0f} {m[4]:>12,.0f} {m[5]:>8,.0f}")
    for lab, lo, hi in (("bad product at the start", 0, .01), ("ok", .01, .022), ("great", .022, 1)):
        g = [x["net"] for x in b if lo <= x["cvr"] < hi]
        print(f"  final product {lab:<24} share {len(g)/len(b):.0%} | median net {statistics.median(g):,.0f}")
