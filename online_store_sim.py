"""Online store simulation: personalized-gift print-on-demand (Hebrew market), 20,000 NIS, 365 days.
Traffic = paid ads (run by a bot media-buyer) + organic/word-of-mouth + email repeat buyers.
Product-market fit is random per run, so many simulated years fail - that is realistic."""
import random, statistics, math
from coffee_cart_sim import taxes

BUDGET = 20000
SETUP = {"store theme/domain/legal/business registration": 2500, "product mockups+photos+brand": 2200,
         "sample orders for quality check": 1300}
RESERVE = BUDGET - sum(SETUP.values())           # cash used for ads + working capital
FIXED_MONTH = 150 + 220 + 250 + 100              # platform, apps, accountant, tools
AOV = 150          # avg order incl. VAT and shipping paid by customer
VAT = 1.17
PRODUCT_COST = 0.40   # print+fulfilment as share of net price
SHIP_COST_NET = 18    # carrier cost per order not covered by customer shipping fee
FEE_PCT, FEE_FIX = 0.029, 1.2
REFUND = 0.045
MONTH_MULT = [0.9, 1.1, 1.2, 0.9, 1.1, 0.8, 0.7, 0.9, 1.3, 1.1, 1.2, 1.6]   # Jan..Dec gifting seasons
CPC_BASE = 1.2

def run(seed):
    r = random.Random(seed)
    u = r.random()
    # product-market fit: bad 35%, ok 45%, great 20%  (conversion rate of a visitor)
    cvr = r.uniform(0.004, 0.009) if u < .35 else r.uniform(0.012, 0.02) if u < .8 else r.uniform(0.025, 0.04)
    cash = RESERVE; ad_daily = 60.0
    rev = cogs = ads = fees = 0.0
    orders_total = 0; repeat_pool = 0.0; organic_boost = 0.0
    window = []; monthly = []; m_net = 0.0; m_fixed_total = 0.0
    for day in range(365):
        month = min(11, int(day / 30.42)); seas = MONTH_MULT[month]
        # competitor/CPM pressure: CPC rises 30% in Q4 (Oct-Dec) and with saturation
        cpc = CPC_BASE * (1.3 if month >= 9 else 1.0) * (1 + ad_daily / 900) ** 0.35
        spend = min(ad_daily, max(0, cash - 500))     # cannot spend money it doesn't have
        paid_visitors = spend / cpc
        organic = (3 + 0.04 * orders_total) * seas * (1.0 if day > 45 else 0.3)
        visitors = paid_visitors + organic
        # each visitor is a bot: buy with prob cvr*season; collapse conversion if ad creative fatigues
        fatigue = 1 - min(0.35, spend * 0.0004 * (day % 60) / 60)
        p = cvr * seas * fatigue
        n_orders = sum(1 for _ in range(int(visitors)) if r.random() < p) if visitors < 2000 else int(visitors * p)
        n_orders += int(repeat_pool * 0.004 + (r.random() < (repeat_pool * 0.004) % 1))   # email repeat buyers
        gross = n_orders * AOV * r.uniform(0.9, 1.1)
        net_rev = gross / VAT * (1 - REFUND)
        c = n_orders * (AOV / VAT * PRODUCT_COST + SHIP_COST_NET)
        f = n_orders * FEE_FIX + gross * FEE_PCT
        cash += net_rev - c - f - spend
        rev += net_rev; cogs += c; fees += f; ads += spend
        m_net += net_rev - c - f - spend
        orders_total += n_orders; repeat_pool += n_orders * 0.9
        window.append(net_rev - c - f - spend); window = window[-14:]
        # bot media buyer: review every 14 days (contribution after ads)
        if day % 14 == 13 and spend > 0:
            contrib = sum(window)
            if contrib > 0: ad_daily = min(ad_daily * 1.25, 1500)
            elif contrib < -0.3 * spend * 14: ad_daily = max(15, ad_daily * 0.6)
            else: ad_daily = max(15, ad_daily * 0.9)
        if (day + 1) % 30 == 0:
            fx = FIXED_MONTH + (r.randint(300, 1500) if r.random() < .1 else 0)
            cash -= fx; m_fixed_total += fx
            monthly.append((len(monthly) + 1, rev, ads, fx, m_net - fx, cash)); m_net = 0
    op = rev - cogs - fees - ads - m_fixed_total
    # accountant (3,000/yr) is already inside FIXED_MONTH, so only income tax + NI are added here
    tax = ni = 0.0
    if op > 0:
        _, tax, ni = taxes(op + 3000 + 5100)   # taxes() re-subtracts accountant + deductions
    take_home = op - tax - ni
    return dict(cvr=cvr, rev=rev, ads=ads, cogs=cogs, fees=fees, fixed=m_fixed_total, op=op,
                take=take_home, cash=cash, orders=orders_total, monthly=monthly,
                broke=cash < 1000)

if __name__ == "__main__":
    print(f"Setup {sum(SETUP.values()):,} | starting cash for ads/working capital {RESERVE:,}")
    # print a median-ish detailed run
    runs = [run(s) for s in range(1000)]
    runs.sort(key=lambda x: x["take"])
    med = runs[len(runs) // 2]
    print("\n== Typical (median) simulated year ==")
    print(f"conversion rate {med['cvr']:.2%} | orders {med['orders']:,}")
    print("month  revenue(cum)  ads(cum)  fixed  month-profit   cash")
    for m in med["monthly"]: print(f"{m[0]:>5} {m[1]:>11,.0f} {m[2]:>9,.0f} {m[3]:>6,.0f} {m[4]:>12,.0f} {m[5]:>8,.0f}")
    print(f"Revenue {med['rev']:,.0f} | product+shipping {med['cogs']:,.0f} | fees {med['fees']:,.0f} | ads {med['ads']:,.0f} | fixed {med['fixed']:,.0f}")
    print(f"Operating profit {med['op']:,.0f} | after tax/NI/accountant {med['take']:,.0f}")
    t = [x["take"] for x in runs]; N = len(runs)
    print(f"\n== Monte Carlo, {N} simulated years ==")
    print(f"After-tax result (setup costs {sum(SETUP.values()):,} already spent, not deducted again): "
          f"median {statistics.median(t):,.0f} | p10 {t[N//10]:,.0f} | p90 {t[9*N//10]:,.0f} | best {t[-1]:,.0f} | worst {t[0]:,.0f}")
    net_after_setup = [x - sum(SETUP.values()) for x in t]
    print(f"Net of setup costs: median {statistics.median(net_after_setup):,.0f}")
    print(f"Years with positive operating profit: {sum(x['op']>0 for x in runs)/N:.0%} | net-positive after setup: {sum(x>0 for x in net_after_setup)/N:.0%}")
    print(f"Years the cash fell below 1,000 NIS (effectively bust): {sum(x['broke'] for x in runs)/N:.0%}")
    for lab, lo, hi in (("bad product-market fit", 0, .01), ("ok", .01, .022), ("great", .022, 1)):
        g = [x["take"] - sum(SETUP.values()) for x in runs if lo <= x["cvr"] < hi]
        print(f"  {lab:<24} share {len(g)/N:.0%} | median net {statistics.median(g):,.0f}")
