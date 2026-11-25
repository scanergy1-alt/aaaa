"""Digital service business: short-form video editing + social content subscriptions for small Israeli businesses.
Owner: 16 y/o, 20,000 NIS, H hours/day. Parent/guardian is the legal owner (minor). Exempt dealer, no NI under 18.
Clients are bots (budget, satisfaction, churn). Leads come from cold outreach (DMs), portfolio-driven inbound and referrals.
Two strategies: SOLO (do all work, stop taking clients when full) vs SCALE (outsource editing to freelancers when full).
Every number is an assumption, not market data."""
import random, math, statistics, sys
from coffee_cart_sim import taxes

BUDGET = 20000
SETUP = {"laptop/PC upgrade": 5500, "mic, light, tripod, stabilizer": 1200, "portfolio site + branding": 1200,
         "courses / first-year tool licenses": 1000, "accountant setup + registration": 300}
SETUP_TOTAL = sum(SETUP.values())
RESERVE = BUDGET - SETUP_TOTAL
TOOLS_MONTH = 400 + 150          # editing/AI/design/CRM subscriptions + bookkeeping
REELS_PER_CLIENT = 8
FREELANCER_REEL = 90
FEE = 0.01                       # bank transfer / Bit / invoicing fees
HOLIDAY_P = 0.035                # unavailable days (holidays, exams, sick)
EXEMPT_LIMIT = 120000
CAL = 1.0      # conversion multiplier: 0.6 pessimistic, 1.0 base, 1.5 optimistic

def binom(r, n, p):
    if n <= 0 or p <= 0: return 0
    if n <= 40: return sum(1 for _ in range(n) if r.random() < p)
    return max(0, min(n, int(r.gauss(n * p, math.sqrt(n * p * (1 - p))) + .5)))

def run(seed, strategy, H=10.0):
    r = random.Random(seed)
    q = r.uniform(0.25, 0.65)            # starting editing/sales quality
    cash = RESERVE; clients = []          # each: price, age, next_bill
    portfolio_h = 0.0; ever = 0; cum_gross = 0.0
    rev = freel = tools = 0.0; monthly = []; m_rev = m_cost = 0.0; overload_days = 0
    ads_unused = RESERVE; ever_msgs = 0; low_until = -1
    for day in range(365):
        month = day // 30
        dow = day % 7
        working = dow != 5 and r.random() > HOLIDAY_P          # Sat off
        trust = 0.70 + 0.30 * min(1.0, ever / 8)               # a 16 y/o must earn trust (portfolio, testimonials)
        edit_h = 2.2 - 1.2 * q                                  # hours per reel
        w_client = REELS_PER_CLIENT * edit_h + 2.0              # hours / client / month
        total_need = len(clients) * w_client
        if H > 6 and day % 30 == 0 and r.random() < 0.10: low_until = day + 21   # burnout / exam crunch
        eff = 0.65 * (0.3 if day < low_until else 1.0)      # focus efficiency, minus burnout
        hours_day = H * eff if working else 0.0
        # outsourcing
        out = 0.0
        if strategy in ("scale", "reinvest") and total_need > 0.7 * H * 0.65 * 26:
            out = min(0.85, 1 - (0.7 * H * 0.65 * 26 - 2 * len(clients)) / max(1, total_need - 2 * len(clients)))
            out = max(out, 0.0)
        own_need_day = (total_need - out * len(clients) * REELS_PER_CLIENT * edit_h + (0.5 * len(clients) if out > 0 else 0)) / 26
        overload = own_need_day > H * 0.65
        if overload and working: overload_days += 1
        used = min(hours_day, own_need_day if working else 0)
        spare = max(0.0, hours_day - used)
        out_h, learn_h, content_h = spare * 0.60, spare * 0.15, spare * 0.25
        portfolio_h += content_h
        q = min(1.0, q + 0.0005 * learn_h * (1 - q) + 0.00008 * used * (1 - q))
        full = own_need_day > 0.9 * H * 0.65 and strategy == "solo"
        # --- lead generation ---
        msgs = int(out_h * 20)
        sat = max(0.15, 1 - ever_msgs / 3500); ever_msgs += msgs
        replies = binom(r, msgs, 0.035 * trust * sat * CAL)
        calls = binom(r, replies, 0.35)
        port = min(1.0, portfolio_h / 300)
        calls += binom(r, 1, min(1, (0.010 + 0.10 * port) * trust * CAL))                    # inbound
        calls += binom(r, 1, min(1, len(clients) * 0.05 / 30 * 3)) if clients else 0  # referrals
        if strategy == "reinvest" and working:      # no living costs -> plow spare cash into paid leads
            ad = min(2500, 0.25 * max(0, cash - 5000)) / 26
            if ad > 0:
                cash -= ad * 1.17; tools += ad * 1.17; m_cost += ad * 1.17      # exempt dealer can't reclaim VAT
                calls += binom(r, 5, min(1, ad / 100 / 5 * CAL))                # ~100 NIS per booked call
        if working and not full:
            for _ in range(calls):
                price = min(4000, max(500, r.lognormvariate(math.log(450 + 700 * q), 0.30)))
                pf = (800 / price) ** 0.6
                if r.random() < min(0.8, 0.25 * (0.4 + 0.6 * q) * trust * pf):
                    clients.append(dict(price=price, nb=day)); ever += 1
        # --- billing & churn ---
        for c in list(clients):
            if day >= c["nb"] and (day - c["nb"]) % 30 == 0:
                gross = c["price"]; cum_gross += gross
                fee = gross * FEE
                free_cost = out * REELS_PER_CLIENT * FREELANCER_REEL
                paid = 0.0 if r.random() < 0.04 else 1.0                # unpaid invoice
                gross *= paid
                cash += gross - fee - free_cost
                rev += gross; freel += free_cost; m_rev += gross; m_cost += fee + free_cost
        if working:
            churn_m = max(0.03, min(0.45, 0.29 - 0.18 * q + (0.12 if overload else 0.0) + (0.02 if trust < 0.85 else 0) + (0.03 if out > 0 else 0)))
            d_p = 1 - (1 - churn_m) ** (1 / 30)
            clients = [c for c in clients if r.random() > d_p]
        if (day + 1) % 30 == 0:
            cash -= TOOLS_MONTH; tools += TOOLS_MONTH; m_cost += TOOLS_MONTH
            monthly.append((len(monthly) + 1, len(clients), m_rev, m_rev - m_cost, cash, q)); m_rev = m_cost = 0
    fixed = tools
    op = rev * (1 - FEE) - freel - fixed
    tax = 0.0
    if op > 0: _, tax, _ = taxes(op + 3000 + 5100)
    take = op - tax
    return dict(rev=rev, op=op, take=take, net=take - SETUP_TOTAL, clients=len(clients), ever=ever, q=q,
                overload=overload_days, monthly=monthly, cash=cash, exempt=cum_gross < EXEMPT_LIMIT)

def summarize(strategy, H=10.0, N=800, show=True):
    runs = sorted((run(s, strategy, H) for s in range(N)), key=lambda x: x["net"])
    nets = [x["net"] for x in runs]
    if show:
        print(f"{strategy.upper():<6} {H:>4.0f}h/day | median net {statistics.median(nets):>8,.0f} | p10 {nets[N//10]:>8,.0f}"
              f" | p90 {nets[9*N//10]:>8,.0f} | profitable {sum(x>0 for x in nets)/N:>4.0%}"
              f" | avg clients at end {statistics.mean(x['clients'] for x in runs):>4.1f}"
              f" | avg revenue {statistics.mean(x['rev'] for x in runs):>8,.0f}")
    return runs

if __name__ == "__main__":
    print(f"Setup {SETUP_TOTAL:,} | cash kept as buffer {RESERVE:,} | (net = after income tax and setup)\n")
    summarize("solo"); summarize("scale"); summarize("reinvest")
    print("\n-- hours sensitivity (SCALE) --")
    for h in (10, 6, 4, 2): summarize("scale", h)
    print("\n-- sensitivity to how well cold outreach converts (SCALE, 10h) --")
    for lab, v in (("pessimistic x0.6", 0.6), ("base x1.0", 1.0), ("optimistic x1.5", 1.5)):
        CAL = v; print(f"{lab:<18}", end=" "); summarize("scale", 10)
    CAL = 1.0
    runs = summarize("scale", 10, show=False); med = runs[len(runs)//2]
    print("\n== Median SCALE year at 10 h/day ==")
    print("month clients  revenue  profit   cash  quality")
    for m in med["monthly"]: print(f"{m[0]:>5} {m[1]:>7} {m[2]:>8,.0f} {m[3]:>7,.0f} {m[4]:>7,.0f}  {m[5]:.2f}")
    print(f"Total revenue {med['rev']:,.0f} | operating profit {med['op']:,.0f} | clients ever {med['ever']}")
    print(f"Equipment still owned (not counted as cash): ~{(5500+1200)*0.5:,.0f} NIS")
