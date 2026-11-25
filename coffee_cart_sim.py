"""Coffee-cart business simulation: 20,000 NIS budget, 365 days, bot customers."""
import random, statistics, sys

BUDGET = 20000
# --- one-time spend (NIS) ---
CAPEX = {"cart+espresso machine (used)": 9500, "grinder+fridge+small gear": 2500,
         "permit+insurance (year 1)": 1800, "branding/menu/signage": 900,
         "opening stock": 1300}
RESERVE = BUDGET - sum(CAPEX.values())          # cash kept as working capital
# --- monthly fixed costs ---
FIXED_MONTH = {"location fee": 600, "marketing": 400, "phone/POS/software": 120, "maintenance": 150}

MENU = {  # name: (price, cost)
    "espresso": (10, 2.2), "cappuccino": (15, 3.6), "iced coffee": (16, 3.8), "pastry": (12, 6.0)}
POP = 700            # office workers within walking distance
CAPACITY_PER_DAY = 160   # customers one person can serve
SPOILAGE = 0.04          # share of pastry/milk stock wasted

class Bot:
    def __init__(s, r):
        s.loyal = r.random() * 0.5             # habit strength
        s.price_sens = r.uniform(0.5, 1.5)
        s.coffee_lover = r.random()
        s.fav = r.choice(["espresso", "cappuccino", "iced coffee"])
        s.pastry_p = r.uniform(0.05, 0.5)
        s.aware = False
        s.visits = 0

def season_temp(day):  # 0..1 hotness, peak ~ day 200 (summer)
    import math
    return 0.5 + 0.5 * math.sin((day - 110) / 365 * 2 * math.pi)

def run(seed, verbose=False):
    r = random.Random(seed)
    bots = [Bot(r) for _ in range(POP)]
    for b in bots[:int(POP * 0.12)]: b.aware = True      # launch awareness
    cash = RESERVE; rev = cogs = 0; fixed_total = 0
    monthly = []; m_rev = m_cogs = 0; m_fixed = 0
    price_mult = 1.0
    competitor = r.random() < 0.6; comp_day = r.randint(120, 300)
    daily_customers = []
    for day in range(365):
        dow = day % 7                                    # 5 = Fri,6 = Sat
        month = day // 30.42
        working = dow not in (4, 5)                      # Israel: Fri/Sat closed (cart too)
        holiday = r.random() < 0.035 and working         # random holiday/strike
        rain = r.random() < (0.22 if season_temp(day) < 0.35 else 0.02)
        temp = season_temp(day)
        sick = r.random() < 0.012                        # owner sick day
        open_today = working and not holiday and not sick
        day_rev = day_cogs = 0; served = 0
        if open_today:
            order = bots[:]; r.shuffle(order)
            for b in order:
                if served >= CAPACITY_PER_DAY: break
                presence = 0.75 * (0.6 if rain else 1.0)  # in office & walking by
                if not b.aware:
                    if r.random() < 0.010 * presence + (0.003 if day % 30 < 3 else 0):  # word of mouth/flyers
                        b.aware = True
                    continue
                p = 0.03 + 0.14 * b.coffee_lover + 0.20 * b.loyal * min(1, b.visits / 15)
                p *= presence / b.price_sens ** (price_mult - 0.0) * 1.0
                if competitor and day > comp_day:
                    p *= 0.78
                if rain: p *= 0.8
                if r.random() > min(p, 0.9): continue
                # choose item
                item = b.fav
                if item == "iced coffee" and temp < 0.45: item = "cappuccino"
                if item in ("espresso", "cappuccino") and temp > 0.8 and r.random() < 0.4: item = "iced coffee"
                price, cost = MENU[item]; price *= price_mult
                tot = price; c = cost
                if r.random() < b.pastry_p:
                    pp, pc = MENU["pastry"]; tot += pp * price_mult; c += pc
                day_rev += tot / 1.17 * (1 - 0.015); day_cogs += c * (1 + SPOILAGE); served += 1; b.visits += 1
                # word of mouth
                if r.random() < 0.01:
                    r.choice(bots).aware = True
        daily_customers.append(served)
        cash += day_rev - day_cogs; rev += day_rev; cogs += day_cogs
        m_rev += day_rev; m_cogs += day_cogs
        if (day + 1) % 30 == 0:                          # month-end
            fx = sum(FIXED_MONTH.values())
            if r.random() < 0.15: fx += r.randint(300, 1500)   # repair / fine / equipment failure
            cash -= fx; fixed_total += fx; m_fixed = fx
            monthly.append((len(monthly) + 1, m_rev, m_cogs, fx, m_rev - m_cogs - fx, cash))
            m_rev = m_cogs = 0
    # leftover days (5) fixed cost prorated ignored; year-1 permit already in CAPEX
    profit = rev - cogs - fixed_total - sum(CAPEX.values() if False else [0])
    # operating profit (after fixed costs, before one-time setup). Net = also minus CAPEX written off as 1-yr cost
    capex_cost = sum(CAPEX.values()) - CAPEX["opening stock"]  # stock is consumed via COGS
    net_after_setup = profit - capex_cost + 0.35 * (CAPEX["cart+espresso machine (used)"] + CAPEX["grinder+fridge+small gear"])  # resale value of kit
    return dict(rev=rev, cogs=cogs, fixed=fixed_total, op_profit=profit, net=net_after_setup,
                cash_end=cash, monthly=monthly, avg_cust=statistics.mean([d for d in daily_customers if d] or [0]),
                min_cash=min(m[5] for m in monthly), regulars=sum(1 for b in bots if b.visits >= 20))

if __name__ == "__main__":
    print(f"Setup spend: {sum(CAPEX.values()):,} | working-capital reserve: {RESERVE:,}")
    one = run(42)
    print("\n== Single detailed run (seed 42) ==")
    print("month  revenue   COGS  fixed  profit   cash")
    for m in one["monthly"]: print(f"{m[0]:>5} {m[1]:>8,.0f} {m[2]:>6,.0f} {m[3]:>6,.0f} {m[4]:>7,.0f} {m[5]:>7,.0f}")
    print(f"Revenue {one['rev']:,.0f} | COGS {one['cogs']:,.0f} | fixed {one['fixed']:,.0f}")
    print(f"Operating profit (before setup costs): {one['op_profit']:,.0f}")
    print(f"Avg customers/open day: {one['avg_cust']:.0f} | regulars(20+ visits): {one['regulars']}")
    N = 500
    res = [run(s) for s in range(N)]
    nets = sorted(x["net"] for x in res); ops = sorted(x["op_profit"] for x in res)
    print(f"\n== Monte Carlo, {N} simulated years ==")
    print(f"Operating profit: median {statistics.median(ops):,.0f} | p10 {ops[N//10]:,.0f} | p90 {ops[9*N//10]:,.0f}")
    print(f"Net after setup costs (kit resold at 35%): median {statistics.median(nets):,.0f} | p10 {nets[N//10]:,.0f} | p90 {nets[9*N//10]:,.0f}")
    print(f"Years profitable (net>0): {sum(n>0 for n in nets)/N:.0%} | ran out of cash: {sum(x['min_cash']<0 for x in res)/N:.0%}")


# ---- Israeli self-employed taxes (APPROXIMATE, verify with an accountant) ----
def taxes(op_profit):
    accountant = 3000                      # bookkeeping / annual reports
    deductible = 2700 + 0.20 * 12000       # permit+branding + 20% depreciation on kit
    taxable = max(0, op_profit - accountant - deductible)
    brackets = [(84120, .10), (120720, .14), (193800, .20), (269280, .31), (560280, .35), (1e12, .47)]
    tax, prev = 0, 0
    for top, rate in brackets:
        if taxable > prev: tax += (min(taxable, top) - prev) * rate
        prev = top
    tax = max(0, tax - 2.25 * 2904)        # tax credit points
    ni = min(taxable, 99000) * 0.0597 + max(0, min(taxable, 560000) - 99000) * 0.1783  # NI + health
    return accountant, tax, ni

if __name__ == "__main__":
    res = [run(s) for s in range(500)]
    out = []
    for x in res:
        acc, tax, ni = taxes(x["op_profit"])
        out.append(x["op_profit"] - acc - tax - ni)
    out.sort()
    a, t, n = taxes(statistics.median(x["op_profit"] for x in res))
    print(f"\n== After accountant+income tax+national insurance ==")
    print(f"At median profit: accountant {a:,.0f} | income tax {t:,.0f} | NI+health {n:,.0f}")
    print(f"Take-home profit (before any owner salary draw is 'cost'): median {statistics.median(out):,.0f} | p10 {out[50]:,.0f} | p90 {out[450]:,.0f}")
    print(f"Per month: {statistics.median(out)/12:,.0f}")
