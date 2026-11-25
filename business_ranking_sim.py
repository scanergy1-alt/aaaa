"""Ranks 27 digital/online business models for ONE profile: 16 y/o, 20,000 NIS, Israel (kibbutz), H hours/day,
no living costs. Monthly Monte-Carlo, 12 months starting Dec 2026.
'Success' = net profit after setup costs and income tax > 0 after 12 months.
ALL PARAMETERS ARE MY ASSUMPTIONS (rough industry-style estimates), not measured data. The ranking is only as good as they are,
so the script also re-ranks under random perturbations of every business's demand to show how stable the Top 5 is."""
import random, math, statistics, sys
from collections import Counter
from coffee_cart_sim import taxes

BUDGET = 20000
MONTH_MULT = [0.9, 1.1, 1.2, 0.9, 1.1, 0.8, 0.7, 0.9, 1.3, 1.1, 1.2, 1.6]

def poisson(r, lam):
    if lam <= 0: return 0
    if lam > 30: return max(0, int(r.gauss(lam, math.sqrt(lam)) + .5))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= r.random()
        if p <= L: return k
        k += 1
def binom(r, n, p):
    if n <= 0 or p <= 0: return 0
    if n <= 60: return sum(1 for _ in range(n) if r.random() < p)
    return max(0, min(n, int(r.gauss(n * p, math.sqrt(n * p * (1 - p))) + .5)))
def lognorm(r, med, sig): return med * math.exp(r.gauss(0, sig))
def hours_month(r, prof):
    Hm = prof["H"] * 26 * prof["eff"]
    if prof["H"] > 6 and r.random() < prof["burn"]: Hm *= 0.3     # burnout / exam crunch month
    return Hm
def apply(cash, profit):
    if cash <= 0: return 0.0, cash                                   # business has stopped
    if cash + profit < 0: profit = -cash
    return profit, cash + profit
def comp_of(P, cumH): return 1 - (1 - P["c0"]) * math.exp(-cumH / P["ramp"])

# ---------------- archetype engines (each returns list of 12 monthly profits) ----------------
def sim_service(r, P, prof, bias):
    umult = lognorm(r, 1, .25) * bias
    cash = BUDGET - P["setup"]; cumH = n = ever = 0; att_cum = prev_load = 0.0; out = []
    for m in range(12):
        Hm = hours_month(r, prof); comp = comp_of(P, cumH)
        trust = P["t0"] + (1 - P["t0"]) * min(1, ever / 8)
        price = P["p0"] + P["p1"] * comp; hpc = max(1.0, P["hc0"] - P["hc1"] * comp)
        sat = max(.15, 1 - att_cum / P["market"])
        if not P["one_off"]:
            capH = min(.9 * Hm, P.get("cap_h", 1e9)); need = n * hpc; spare = max(0, Hm - need); overload = need > capH
            att = spare * .6 * P["aph"] * sat; att_cum += att
            lam = (att * P["conv"] * trust * (.5 + .5 * comp) + P["inb"] * min(1, ever / 8 + .15) * trust) * umult + P["ref"] * n
            new = min(poisson(r, lam), max(0, int((capH - need) / hpc)))
            churn = max(.03, min(.5, P["ch0"] - P["ch1"] * comp + (.12 if overload else 0) + (.02 if trust < .85 else 0)))
            n0 = n; n = n - binom(r, n, churn) + new; ever += new
            rev = (n0 + n) / 2 * price * (1 - P["fee"]) * .96
        else:
            spare = max(0, Hm - prev_load)
            att = spare * .6 * P["aph"] * sat; att_cum += att
            inbound = min(P["inb_cap"], P["inb"] + P["inb_g"] * ever) * trust
            lam = (att * P["conv"] * trust * (.5 + .5 * comp) + inbound) * umult + P["rep"] * ever / 12
            proj = min(poisson(r, lam), int(.9 * Hm / hpc)); prev_load = proj * hpc; ever += proj
            rev = proj * price * (1 - P["fee"]) * .96
        pr, cash = apply(cash, rev - P["tools"]); out.append(pr); cumH += Hm
    return out

def draw_cvr(r, dist):
    u, acc = r.random(), 0
    for p, lo, hi in dist:
        acc += p
        if u <= acc: return r.uniform(lo, hi)
    return r.uniform(dist[-1][1], dist[-1][2])

def sim_ecom(r, P, prof, bias):
    umult = bias * lognorm(r, 1, .2); cvr = draw_cvr(r, P["cvr_d"]) * umult
    cash = BUDGET - P["setup"]; S = P["s0"]; orders_total = 0; cumH = 0.0; rpool = 0.0; cum_gross = 0.0
    pivots = 0; vis = ords = 0.0; last_pivot = P["delay"]; out = []
    for m in range(12):
        Hm = hours_month(r, prof); cumH += Hm
        if m < P["delay"]:
            pr, cash = apply(cash, -P["tools"]); out.append(pr); continue
        learn = min(1, cumH / P["ramp"]); cal = (11 + m) % 12; seas = MONTH_MULT[cal] if P["seasonal"] else 1.0
        Se = min(S, max(0, cash - 1000))
        cpc = P["cpc"] * (1.3 if cal >= 9 else 1.0) * (1 + Se / 30 / 900) ** .35 * (1.45 - .45 * learn)
        paid = Se / cpc
        organic = (3 + .04 * orders_total) * 30 * seas * P["org"] * (.3 if m - P["delay"] < 2 else 1.0)
        visitors = paid + organic
        fatigue = 1 - min(.35, Se / 30 * .0004 * 15)
        p = cvr * seas * fatigue * (.85 + .15 * learn)
        n = poisson(r, visitors * p) + poisson(r, rpool * .12)
        n = min(n, int(Hm * .6 * 60 / P["min_order"]))
        exempt = cum_gross < 120000; vat = 1.0 if exempt else 1.17
        gross = n * P["aov"] * r.uniform(.9, 1.1); cum_gross += gross
        net_rev = gross / vat * (1 - P["refund"])
        cogs = n * (P["aov"] / 1.17 * P["cogs"] * (1.17 if exempt else 1.0) + P["ship"])
        fees = n * P["fee_fix"] + gross * P["fee_pct"]
        ad_cost = Se * (1.17 if exempt else 1.0)
        contrib = net_rev - cogs - fees - ad_cost; profit = contrib - P["tools"]
        orders_total += n; rpool += n * .9; vis += visitors; ords += n
        since = m - last_pivot
        if since >= 2 and vis >= 400 and ords / vis < P["pv_thr"] and pivots < 3 and cash > 4000:
            profit -= 900; cvr = draw_cvr(r, P["cvr_d"]) * umult; pivots += 1; last_pivot = m
            vis = ords = 0.0; S = P["s0"]; orders_total = int(orders_total * .5)
        else:
            if since >= 4: vis = ords = 0.0
            if contrib > 0: S = min(S * 1.4, P["s_cap"])
            elif contrib < -.3 * max(ad_cost, 1): S = max(300, S * .6)
            else: S = max(300, S * .9)
        pr, cash = apply(cash, profit); out.append(pr)
    return out

def sim_products(r, P, prof, bias):
    umult = bias * lognorm(r, 1, .25)
    cash = BUDGET - P["setup"]; cat = []; cumH = 0.0; mk_cum = 0.0; out = []
    for m in range(12):
        Hm = hours_month(r, prof); comp = comp_of(P, cumH); mk_cum += Hm * P["mk_share"]
        n_new = int(Hm * (1 - P["mk_share"]) * .9 / (P["hpp"] * (1.5 - .8 * comp)))
        if P.get("unit_cost"): n_new = min(n_new, int(max(0, cash - 3000) / P["unit_cost"]))
        for _ in range(n_new): cat.append([0, lognorm(r, P["med"], P["sig"])])
        mk = 1 + P["mk_boost"] * min(1, mk_cum / 150); boost = min(1.6, .7 + .12 * math.log(1 + len(cat)))
        lam = 0.0
        for it in cat:
            if it[0] >= P["delay"]: lam += it[1] * (.97 ** (it[0] - P["delay"]))
            it[0] += 1
        sales = poisson(r, lam * mk * boost * (.6 + .4 * comp) * umult / (1 + len(cat) / P.get("sat", 150)))
        rev = (sum(lognorm(r, P["price"], P["price_sig"]) for _ in range(sales)) if P.get("price_sig") else sales * P["price"]) * (1 - P["fee"])
        cost = P["tools"] + P.get("upkeep", 0) * len(cat) + n_new * P.get("unit_cost", 0)
        pr, cash = apply(cash, rev - cost); out.append(pr); cumH += Hm
    return out

def sim_audience(r, P, prof, bias):
    cash = BUDGET - P["setup"]; f = 0.0; cumH = 0.0; out = []
    for m in range(12):
        Hm = hours_month(r, prof); comp = comp_of(P, cumH)
        posts = min(P["posts_max"], int(Hm * .8 / P["hpp"])); views = new_f = 0.0
        for _ in range(posts):
            v = P["base"] * bias * (1 + f / P["k"]) * (.5 + .9 * comp) * lognorm(r, 1, P["sig"])
            if r.random() < P["phit"] * (.5 + comp): v *= P["hit"]
            views += v; new_f += v * P["conv"]
        f = f * (1 - P["fchurn"]) + new_f
        rev = views * P["rpm"] / 1000 if f >= P["thr"] else 0.0
        if f >= P["sthr"]: rev += P["srate"] * f / 1000 * min(1, posts / P["sposts"])
        pr, cash = apply(cash, rev - P["tools"]); out.append(pr); cumH += Hm
    return out

def sim_software(r, P, prof, bias):
    cash = BUDGET - P["setup"]; cumH = 0.0; progress = 0.0; users = 0.0; built = False; out = []
    u = r.random(); acc = 0; mult = P["pmf"][-1][1]; hit = False
    for pp, mu in P["pmf"]:
        acc += pp
        if u <= acc: mult = mu; hit = (mu == P["pmf"][-1][1] and mu > 1); break
    mult *= bias
    for m in range(12):
        Hm = hours_month(r, prof); comp = comp_of(P, cumH)
        if not built:
            progress += Hm * (.4 + .6 * comp); built = progress >= P["build_h"]
            pr, cash = apply(cash, -P["tools"]); out.append(pr); cumH += Hm; continue
        mk_h = Hm * .5
        users = users * (1 - P["churn"]) + poisson(r, P["upm"] * mk_h * mult * (.6 + .4 * comp))
        if hit: users *= 1 + P["vir"]
        rev = users * P["arpu"] * (1 - P["fee"])
        pr, cash = apply(cash, rev - P["tools"] - users * P["cpu"]); out.append(pr); cumH += Hm
    return out

def sim_resell(r, P, prof, bias):
    bias = bias * lognorm(r, 1, .30)     # some people never find a niche with real margin
    cash = BUDGET - P["setup"]; cumH = 0.0; out = []
    for m in range(12):
        Hm = hours_month(r, prof); comp = comp_of(P, cumH)
        K = min(P["kcap"], max(0, cash - 500)); items = min(int(K / P["avg_cost"]), int(Hm * .7 / P["hpi"])); tot = 0.0
        for _ in range(int(items * .65)):          # ~65% of stock sells within the month, rest stays in inventory
            mi = -P["loss"] if r.random() < P["loss_p"] else r.gauss((P["mar"] + .10 * comp) * bias, P["mar_sd"])
            tot += P["avg_cost"] * (1 + mi) * (1 - P["fee"]) - P["avg_cost"] - P["ship"]
        pr, cash = apply(cash, tot - P["tools"]); out.append(pr); cumH += Hm
    return out

ENG = dict(service=sim_service, ecom=sim_ecom, products=sim_products, audience=sim_audience, software=sim_software, resell=sim_resell)

# ---------------- catalogue (27 business models) ----------------
SV = dict(type="service", fee=0, t0=.7, market=3500, inb_ramp=8, aph=20, ref=.05, rep=.1, inb=.3, inb_g=0, inb_cap=0, one_off=False)
EC = dict(type="ecom", seasonal=True, min_order=3, org=1.0, pv_thr=.009, s_cap=30000, refund=.045, fee_pct=.029, fee_fix=1.2, ship=0)
PR = dict(type="products", mk_share=.25, mk_boost=.5, fee=.13, delay=2, unit_cost=0, upkeep=0)
AU = dict(type="audience", fchurn=.02, tools=150)
SW = dict(type="software", churn=.07, fee=.03, vir=.08)

B = {
 "Video editing for local businesses (retainer)": {**SV, "setup": 6000, "tools": 550, "c0": .35, "ramp": 2500, "p0": 450, "p1": 700, "hc0": 19.6, "hc1": 9.6, "ch0": .29, "ch1": .18, "conv": .0031, "inb": .3},
 "Social-media management for local businesses": {**SV, "setup": 2500, "tools": 400, "c0": .45, "ramp": 2000, "p0": 600, "p1": 600, "hc0": 16, "hc1": 5, "ch0": .26, "ch1": .15, "conv": .0030, "t0": .72},
 "Online tutoring (school subjects / programming)": {**SV, "setup": 1200, "tools": 150, "c0": .65, "ramp": 1500, "p0": 220, "p1": 100, "hc0": 6.5, "hc1": 1, "ch0": .14, "ch1": .05, "aph": 8, "conv": .007, "inb": .3, "ref": .12, "t0": .8, "market": 400, "cap_h": 70},
 "Virtual assistant / customer-support outsourcing": {**SV, "setup": 800, "tools": 250, "c0": .5, "ramp": 1200, "p0": 700, "p1": 500, "hc0": 22, "hc1": 4, "ch0": .18, "ch1": .08, "aph": 25, "conv": .0016, "inb": .1, "ref": .03, "t0": .6},
 "Web design (Wix/WordPress) for local businesses": {**SV, "one_off": True, "setup": 1500, "tools": 350, "c0": .3, "ramp": 2500, "p0": 900, "p1": 3000, "hc0": 32, "hc1": 14, "conv": .0022, "inb": .2, "rep": .06},
 "AI automation / chatbots for small businesses": {**SV, "one_off": True, "setup": 1500, "tools": 600, "c0": .2, "ramp": 3000, "p0": 1200, "p1": 4500, "hc0": 35, "hc1": 15, "aph": 18, "conv": .0012, "inb": .1, "rep": .15, "t0": .65},
 "Freelance gigs on Fiverr/Upwork (design/editing)": {**SV, "one_off": True, "setup": 800, "tools": 150, "c0": .4, "ramp": 2000, "p0": 110, "p1": 250, "hc0": 4.5, "hc1": 2, "aph": 0, "conv": 0, "inb": .8, "inb_g": .25, "inb_cap": 15, "fee": .20, "t0": .6},
 "Translation / transcription gigs": {**SV, "one_off": True, "setup": 300, "tools": 80, "c0": .6, "ramp": 1000, "p0": 60, "p1": 100, "hc0": 2.2, "hc1": .7, "aph": 0, "conv": 0, "inb": 1.5, "inb_g": .2, "inb_cap": 15, "fee": .15},
 "UGC video content for brands": {**SV, "one_off": True, "setup": 1500, "tools": 200, "c0": .35, "ramp": 1800, "p0": 250, "p1": 600, "hc0": 6, "hc1": 2.5, "aph": 15, "conv": .004, "inb": .1, "rep": .25},
 "Print-on-demand personalized gifts (ads)": {**EC, "setup": 5000, "tools": 620, "aov": 150, "cogs": .40, "ship": 18, "cpc": 1.2, "ramp": 1200, "delay": 1, "s0": 750,
     "cvr_d": [(.35, .004, .009), (.45, .012, .02), (.2, .025, .04)]},
 "Dropshipping store (ads)": {**EC, "setup": 3500, "tools": 900, "aov": 130, "cogs": .50, "refund": .09, "cpc": 1.2, "ramp": 1200, "delay": 1, "s0": 750, "org": .5,
     "cvr_d": [(.5, .003, .007), (.35, .009, .015), (.15, .02, .03)]},
 "Own online course / info product (Hebrew, ads)": {**EC, "setup": 3500, "tools": 400, "aov": 300, "cogs": .03, "refund": .08, "fee_pct": .03, "cpc": 1.5, "ramp": 1500, "delay": 2, "s0": 1200,
     "min_order": 1, "org": 1.5, "seasonal": False, "pv_thr": .003, "cvr_d": [(.4, .001, .003), (.4, .004, .009), (.2, .012, .02)]},
 "Amazon FBA private label": {**EC, "setup": 5750, "tools": 700, "aov": 180, "cogs": .38, "ship": 22, "fee_pct": .15, "cpc": 1.4, "ramp": 1500, "delay": 2, "s0": 1000, "seasonal": False,
     "pv_thr": .02, "cvr_d": [(.5, .01, .03), (.35, .04, .07), (.15, .08, .12)]},
 "Etsy printables / planners": {**PR, "setup": 800, "tools": 150, "hpp": 3, "med": .06, "sig": 1.5, "price": 28, "c0": .35, "ramp": 1500},
 "Digital templates (Notion/Canva/Excel)": {**PR, "setup": 600, "tools": 200, "hpp": 9, "med": .08, "sig": 1.6, "price": 55, "fee": .10, "mk_boost": .6, "c0": .4, "ramp": 1800},
 "Self-published kids / low-content books (KDP)": {**PR, "setup": 1200, "tools": 100, "hpp": 12, "med": .15, "sig": 1.4, "delay": 3, "price": 9, "fee": 0, "mk_boost": .3, "c0": .3, "ramp": 1800},
 "Stock photos / footage": {**PR, "setup": 3000, "tools": 80, "hpp": .6, "med": .15, "sig": 1.5, "delay": 3, "price": 2.2, "fee": .35, "mk_boost": .1, "c0": .4, "ramp": 1500},
 "Hebrew niche affiliate / SEO blog": {**PR, "setup": 800, "tools": 300, "hpp": 4.5, "med": 12, "sig": 1.3, "delay": 5, "price": .35, "fee": 0, "mk_boost": .8, "c0": .3, "ramp": 1800},
 "Domain flipping": {**PR, "setup": 600, "tools": 80, "hpp": .25, "med": .001, "sig": 1.2, "delay": 0, "price": 1500, "price_sig": .9, "fee": .10, "mk_share": 0, "mk_boost": 0,
     "unit_cost": 40, "upkeep": 3.5, "c0": .2, "ramp": 1500},
 "YouTube channel (long-form, Hebrew)": {**AU, "setup": 3000, "tools": 100, "hpp": 14, "posts_max": 8, "base": 120, "k": 2500, "sig": 1.0, "phit": .03, "hit": 15, "conv": .008, "thr": 1000, "rpm": 9, "sthr": 8000, "srate": 70, "sposts": 4, "c0": .35, "ramp": 2500},
 "Shorts / TikTok / Reels channel": {**AU, "setup": 1500, "hpp": 1.6, "posts_max": 60, "base": 200, "k": 4000, "sig": 1.3, "phit": .04, "hit": 30, "conv": .004, "fchurn": .03, "thr": 3000, "rpm": .5, "sthr": 8000, "srate": 90, "sposts": 20, "c0": .45, "ramp": 1500},
 "Niche newsletter (Hebrew)": {**AU, "setup": 500, "tools": 120, "hpp": 7, "posts_max": 8, "base": 10, "k": 1500, "sig": .8, "phit": .03, "hit": 6, "conv": 1, "fchurn": .015, "thr": 1e9, "rpm": 0, "sthr": 500, "srate": 160, "sposts": 4, "c0": .45, "ramp": 1500},
 "Instagram theme page + brand deals": {**AU, "setup": 500, "tools": 100, "hpp": 1.0, "posts_max": 60, "base": 350, "k": 6000, "sig": 1.2, "phit": .04, "hit": 20, "conv": .006, "fchurn": .03, "thr": 1e9, "rpm": 0, "sthr": 5000, "srate": 220, "sposts": 20, "c0": .5, "ramp": 1200},
 "Micro-SaaS for Israeli small businesses": {**SW, "setup": 1800, "tools": 300, "build_h": 300, "c0": .3, "ramp": 2500, "upm": .05, "arpu": 90, "cpu": 4, "pmf": [(.6, .05), (.3, 1), (.1, 5)]},
 "Mobile app / casual game": {**SW, "setup": 1500, "tools": 200, "build_h": 450, "c0": .25, "ramp": 3000, "upm": 12, "arpu": 1.1, "churn": .22, "cpu": .03, "fee": .15, "vir": .10, "pmf": [(.8, .05), (.15, 1), (.05, 12)]},
 "Chrome extension / Discord bot / plugin": {**SW, "setup": 600, "tools": 120, "build_h": 120, "c0": .35, "ramp": 1500, "upm": .12, "arpu": 18, "churn": .08, "cpu": .5, "fee": .05, "pmf": [(.7, .05), (.25, 1), (.05, 6)]},
 "Online reselling (eBay / Marketplace / Vinted-style)": dict(type="resell", setup=700, tools=120, kcap=9000, avg_cost=250, mar=.38, mar_sd=.40, loss_p=.15, loss=.40, ship=25, fee=.12, hpi=.8, c0=.3, ramp=1000),
}

def one_year(name, seed, prof, bias=1.0):
    P = B[name]; r = random.Random(seed)
    profits = ENG[P["type"]](r, P, prof, bias)
    cum = 0.0                                   # stop-loss: a rational owner quits a clearly failing business
    for i in range(12):
        cum += profits[i]
        if i >= 5 and cum < -3000 and sum(profits[i - 2:i + 1]) <= 0:
            profits = profits[:i + 1] + [0.0] * (11 - i); break
    op = sum(profits); tax = 0.0
    if op > 0: _, tax, _ = taxes(op + 3000 + 5100)
    return op - tax - P["setup"], sum(profits[-3:]) / 3

def evaluate(name, prof, N=300, bias_sig=0.0, seed0=0):
    r = random.Random(hash(name) % 99991 + seed0)
    bias = lognorm(r, 1, bias_sig) if bias_sig else 1.0
    res = [one_year(name, seed0 * 100003 + s, prof, bias) for s in range(N)]
    nets = sorted(x[0] for x in res)
    return dict(p=sum(n > 0 for n in nets) / N, med=statistics.median(nets), p10=nets[N // 10], p90=nets[9 * N // 10],
                p5k=sum(n > 5000 for n in nets) / N, mom=statistics.median(x[1] for x in res))

if __name__ == "__main__":
    prof = dict(H=10, eff=.65, burn=.10)
    rows = sorted(((n, evaluate(n, prof, 300)) for n in B), key=lambda x: (-round(x[1]["p"], 2), -x[1]["p5k"], -x[1]["med"]))
    print(f"{'#':>2} {'business':<52} {'P(profit)':>9} {'P(>5k)':>7} {'median':>8} {'p10':>8} {'p90':>8} {'exit/mo':>8}")
    for i, (n, e) in enumerate(rows, 1):
        print(f"{i:>2} {n:<52} {e['p']:>9.0%} {e['p5k']:>7.0%} {e['med']:>8,.0f} {e['p10']:>8,.0f} {e['p90']:>8,.0f} {e['mom']:>8,.0f}")
    top5 = [n for n, _ in rows[:5]]
    print("\nTOP 5 (10 h/day):", top5)
    # robustness 1: fewer hours
    for H in (5, 3):
        rr = sorted(((n, evaluate(n, dict(H=H, eff=.65, burn=.10), 200)) for n in B), key=lambda x: (-round(x[1]["p"], 2), -x[1]["p5k"], -x[1]["med"]))
        print(f"\nTop 5 at {H} h/day:", [(n[:34], f"{e['p']:.0%}") for n, e in rr[:5]])
    # robustness 2: random demand perturbation per business (my parameters could be off by ~35%)
    cnt = Counter(); M = 20
    for it in range(M):
        rr = sorted(((n, evaluate(n, prof, 120, bias_sig=.35, seed0=it + 1)) for n in B), key=lambda x: (-round(x[1]["p"], 2), -x[1]["p5k"], -x[1]["med"]))
        for n, _ in rr[:5]: cnt[n] += 1
    print(f"\nStability: how often each business lands in the Top 5 when my demand assumptions are randomly wrong by ~35% ({M} re-rankings):")
    for n, c in cnt.most_common(10): print(f"  {c/M:>4.0%}  {n}")
