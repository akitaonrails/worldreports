"""The brasil stories: what each panel says, for a reader who has never read
a chart like it.

One function per chapter, each returning `{slot key: ctx.story(...)}`;
chapters.py hands them to the card. Same rule as the chapters: every number
is read from this country's CSVs at build time, never typed.
"""
from __future__ import annotations


def economy_stories(ctx) -> dict:
    """Insights for the four panels of the economy plate (Brazil).

    Each card is three or four sacadas that the drawing implies but nobody
    computes at a glance: a chained total, a ratio between two labelled
    points, a ruler that moved, two surveys that are not one series. Every
    number is a placeholder filled from the CSVs the plate draws; derived
    ones (chained growth, ratios, gaps) are defined in the sentence that
    uses them. Where a sentence is true only while the data keep a shape,
    `need` fails the build so the copy is rewritten, not left to go wrong.
    """
    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        """A derived number as a fact, carried by `year` (default: last full)."""
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil economy stories: {why}; rewrite the "
                             f"copy that depends on it")

    at = lambda y: val(0, "count", year=y)      # a year, as a fact

    growth = dict(ctx.col("macro/gdp.csv", "real_growth"))
    per_person = dict(ctx.col("international/world.csv", "gdp_per_person_usd"))
    dollar = dict(ctx.col("macro/dollar.csv", "avg"))
    ipca = dict(ctx.col("macro/ipca.csv", "value"))
    target = dict(ctx.col("macro/inflation_target.csv", "target"))
    band = dict(ctx.col("macro/inflation_target.csv", "tolerance"))
    pnad = dict(ctx.col("macro/unemployment.csv", "value"))
    pme = dict(ctx.col("macro/unemployment.csv", "pme"))

    first = ctx.c.years[0]

    # ---- growth: bars chained into a level, 2014 = 1
    span = [y for y in sorted(growth) if y <= full]
    pre = 2014
    need(any(lo == pre for lo, hi, _ in ctx.c.recessions),
         "the first shaded band no longer starts in 2014")
    level = {pre: 1.0}
    for y in span:
        if y > pre:
            level[y] = level[y - 1] * (1 + growth[y] / 100)
    r1, r2, cov = 2015, 2016, 2020
    need(growth[r1] < 0 and growth[r2] < 0 and growth[cov] < 0,
         "2015, 2016 or 2020 is no longer a falling year")
    loss = 100 * (1 - (1 + growth[r1] / 100) * (1 + growth[r2] / 100))
    need(1.8 <= loss / abs(growth[cov]) <= 2.2,
         "the 2015-16 loss is no longer about twice the 2020 one")
    up = cov + 1
    need(level[up] > level[cov - 1],
         "2021 no longer passes the 2019 level")
    back = min(y for y in span if y > pre and level[y] >= 1)
    need(all(growth[y] > 0 for y in (2017, 2018, 2019)),
         "2017-2019 are no longer all rising years")
    need(level[2019] < 1, "2019 is already above the 2014 level")
    need(back > 2019, "the 2014 level was regained before 2020")
    ge = [y for y in span if growth[y] >= 4]
    need(len(ge) >= 2 and ge[-1] == 2021 and max(ge[:-1]) < 2012
         and len(ge[:-1]) == 5, "the 4%-or-more years changed shape")

    # ---- income per person
    peak = max((y for y in per_person if y <= full), key=per_person.get)
    trough = min((y for y in per_person if peak < y <= full),
                 key=per_person.get)
    need(per_person[full] < per_person[peak],
         "income per person is back at its peak")
    jumps = {y: per_person[y] / per_person[y - 1] - 1
             for y in per_person if first < y <= full}
    big = min(jumps, key=jumps.get)
    need(big == 2015 and growth[big] < 0, "the biggest yearly fall moved")
    need(dollar[big] > dollar[big - 1], "the dollar did not rise that year")
    need(abs(jumps[big] * 100) > 3 * abs(growth[big]),
         "the dollar fall is no longer much larger than real GDP's")

    # ---- inflation
    ys = [y for y in sorted(ipca) if y <= full]
    ceiling = lambda y: target[y] + band[y]
    floor = lambda y: target[y] - band[y]
    over = [y for y in ys if ipca[y] > ceiling(y)]
    under = [y for y in ys if ipca[y] < floor(y)]
    inside = len(ys) - len(over) - len(under)
    need(first == 2006 and ys[0] == first, "the IPCA no longer starts in 2006")
    need(len(over) == 4 and len(under) == 1, "not 4 years over, 1 under")
    excess = {y: ipca[y] - ceiling(y) for y in over}
    ranked = sorted(over, key=excess.get, reverse=True)
    b1, b2, s1, s2 = ranked[0], ranked[1], ranked[2], ranked[3]
    need(excess[b2] > 3 and excess[s1] < 1, "big and small overshoots blurred")
    b1, b2 = sorted((b1, b2))
    s1, s2 = sorted((s1, s2))
    old, new = 2010, over[-1]
    need(old in ys and old not in over and old not in under
         and ipca[old] > ceiling(new) and ipca[new] < ipca[old],
         "the 2010-versus-latest-overshoot contrast no longer holds")
    need(min(ipca[y] for y in ys) > 0, "an IPCA year is negative")
    cum = 1.0
    for y in ys:
        cum *= 1 + ipca[y] / 100
    need(ipca[full] <= ceiling(full), "the latest year is over the ceiling")

    # ---- unemployment
    top = max(pnad, key=pnad.get)
    last = max(y for y in pnad if y <= full)
    start = min(pnad)
    need(pnad[last] == min(pnad.values()), "the latest rate is not the low")
    need(top == 2021, "the unemployment peak is no longer 2021")
    hi = [y for y in sorted(pnad) if pnad[y] > 11]
    need(hi == list(range(hi[0], hi[-1] + 1)) and len(hi) == 6
         and hi[-1] == top, "the run above 11% changed shape")
    rise_to = max((y for y in pnad if pre <= y <= 2018), key=pnad.get)
    climb = pnad[rise_to] - pnad[pre]
    covid_up = pnad[top] - pnad[2019]
    need(climb > covid_up > 0, "the 2014-17 climb is no longer the larger one")
    ov = max(pme)
    need(ov in pnad and ov == start, "the two surveys no longer overlap in one year")
    need(pnad[ov] - pme[ov] > 1, "the surveys now agree in the overlap")
    need(abs(pnad[last] - pme[ov]) < 0.5,
         "the latest rate is no longer close to the old survey's last")
    need(pnad[last] < pnad[pre], "unemployment is not below its 2014 level")

    return {
        "economy.growth": ctx.story(
            title=ctx.text(
                en="GDP only passed its {pre_year} level again in {back_year}",
                pt="O PIB só passou o nível de {pre_year} em {back_year}"),
            beats=[
                (ctx.text(en="Two falls add up to twice COVID",
                          pt="Duas quedas somam o dobro da covid"),
                 ctx.text(
                    en="Chained, {r1_year} and {r2_year} take {loss} off GDP; "
                       "{cov_year} took {cov}, and by {up_year} output was "
                       "already above its 2019 level.",
                    pt="Encadeadas, {r1_year} e {r2_year} tiram {loss} do PIB; "
                       "{cov_year} tirou {cov}, e em {up_year} a produção já "
                       "estava acima do nível de 2019.")),
                (ctx.text(en="A green bar is not a return",
                          pt="Barra verde não é volta ao nível"),
                 ctx.text(
                    en="GDP grew every year from {a_year} to {c_year}, yet "
                       "with the bars chained it ended {c_year} still {short} "
                       "below {pre_year}.",
                    pt="O PIB cresceu todo ano de {a_year} a {c_year}, mas, "
                       "com as barras encadeadas, fechou {c_year} ainda "
                       "{short} abaixo de {pre_year}.")),
                (ctx.text(en="Growing {thr}% or more became rare",
                          pt="Crescer {thr}% ou mais virou raridade"),
                 ctx.text(
                    en="{n_early} years reached {thr}% or more between "
                       "{first_year} and {e_year}. Since then, one: "
                       "{late_year}, right after the {cov_year} fall.",
                    pt="{n_early} anos chegaram a {thr}% ou mais entre "
                       "{first_year} e {e_year}. Desde então, um só: "
                       "{late_year}, logo depois da queda de {cov_year}.")),
            ],
            facts={"pre": at(pre), "back": at(back),
                   "r1": at(r1), "r2": at(r2), "cov": val(abs(growth[cov]), "pct", year=cov),
                   "loss": val(loss, "pct"), "up": at(up),
                   "a": at(2017), "c": at(2019),
                   "short": val(100 * (1 - level[2019]), "pct", year=2019),
                   "thr": val(4, "count"), "n_early": val(len(ge) - 1, "count"),
                   "first": at(first), "e": at(max(ge[:-1])),
                   "late": at(ge[-1])}),
        "economy.gdp_per_person": ctx.story(
            title=ctx.text(
                en="In dollars, GDP per person is still {gap}% below its "
                   "{peak_year} peak",
                pt="Em dólar, o PIB por pessoa segue {gap}% abaixo do pico "
                   "de {peak_year}"),
            beats=[
                (ctx.text(en="More than doubled, then fell back",
                          pt="Dobrou, depois voltou perto do início"),
                 ctx.text(
                    en="GDP per person in {peak_year} was {up} times that of "
                       "{first_year}; in {low_year}, only {low} times. The "
                       "axis counts proportions: equal steps are equal "
                       "percentage changes.",
                    pt="O PIB por pessoa de {peak_year} foi {up} vezes o de "
                       "{first_year}; o de {low_year}, só {low} vez. O eixo "
                       "conta proporções: degraus iguais são variações "
                       "percentuais iguais.")),
                (ctx.text(en="The biggest fall came in one year",
                          pt="A maior queda veio num só ano"),
                 ctx.text(
                    en="From {prev_year} to {d_year} it fell {drop} in "
                       "dollars while real GDP fell only {g}: the dollar "
                       "went from R$ {fx0} to R$ {fx1}. In dollars, income "
                       "and exchange rate mix.",
                    pt="De {prev_year} a {d_year} caiu {drop} em dólar, "
                       "enquanto o PIB real caiu só {g}: o dólar foi de "
                       "R$ {fx0} a R$ {fx1}. Em dólar, renda e "
                       "câmbio se misturam.")),
                (ctx.text(en="Back up, but not to the top",
                          pt="Voltou a subir, sem chegar ao topo"),
                 ctx.text(
                    en="{last_year}: US${last}, {vs_first} times {first_year} "
                       "and {gap}% under the peak. These are current "
                       "dollars: US price rises are not removed.",
                    pt="{last_year}: US$ {last}, {vs_first} vezes {first_year} "
                       "e {gap}% abaixo do pico. São dólares correntes: a "
                       "alta de preços nos EUA não é descontada.")),
            ],
            facts={"peak": at(peak), "first": at(first), "low": val(
                       per_person[trough] / per_person[first], "dec1",
                       year=trough),
                   "up": val(per_person[peak] / per_person[first], "dec1",
                             year=peak),
                   "prev": at(big - 1), "d": at(big),
                   "drop": val(abs(jumps[big]) * 100, "pct", year=big),
                   "g": val(abs(growth[big]), "pct", year=big),
                   "fx0": val(dollar[big - 1], "dec2", year=big - 1),
                   "fx1": val(dollar[big], "dec2", year=big),
                   "last": val(per_person[full], "count"),
                   "vs_first": val(per_person[full] / per_person[first],
                                   "dec1"),
                   "gap": val(round(100 * (1 - per_person[full]
                                           / per_person[peak])), "count")}),
        "economy.inflation": ctx.story(
            title=ctx.text(
                en="Inflation within target in {inside} of {n} years; "
                   "the target fell",
                pt="Inflação dentro da meta em {inside} de {n} anos; a meta "
                   "baixou"),
            beats=[
                (ctx.text(en="The ruler moved down",
                          pt="A régua desceu"),
                 ctx.text(
                    en="In {old_year}, {old} was inside the range (ceiling "
                       "{old_ceil}). In {new_year}, {new} was above it "
                       "(ceiling {new_ceil}).",
                    pt="Em {old_year}, {old} ficou dentro (teto de "
                       "{old_ceil}). Em {new_year}, {new} ficou acima "
                       "(teto de {new_ceil}).")),
                (ctx.text(en="Two big overshoots, two near misses",
                          pt="Dois estouros grandes, dois por pouco"),
                 ctx.text(
                    en="In {b1_year} and {b2_year} inflation passed the "
                       "ceiling by {b1} and {b2} points; in {s1_year} and "
                       "{s2_year}, by {s1} and {s2}.",
                    pt="Em {b1_year} e {b2_year} a inflação passou do teto "
                       "por {b1} e {b2} pontos; em {s1_year} e {s2_year}, "
                       "por {s1} e {s2}.")),
                (ctx.text(en="Lower inflation is not cheaper prices",
                          pt="Inflação menor não é preço mais barato"),
                 ctx.text(
                    en="Prices did not fall in any of the {n} years. Chained, "
                       "those of December {last_year} are {cum} times those "
                       "of December {prev_year}: even {under_year}, the one "
                       "year below the range, was a rise.",
                    pt="Os preços não caíram em nenhum dos {n} anos. "
                       "Encadeados, os de dezembro de {last_year} são {cum} "
                       "vezes os de dezembro de {prev_year}: até {under_year}, "
                       "o único ano abaixo da faixa, foi de alta.")),
            ],
            facts={"inside": val(inside, "count"), "n": val(len(ys), "count"),
                   "old": val(ipca[old], "pct", year=old),
                   "old_ceil": val(ceiling(old), "pct", year=old),
                   "new": val(ipca[new], "pct", year=new),
                   "new_ceil": val(ceiling(new), "pct", year=new),
                   "b1": val(excess[b1], "dec1", year=b1),
                   "b2": val(excess[b2], "dec1", year=b2),
                   "s1": val(excess[s1], "dec1", year=s1),
                   "s2": val(excess[s2], "dec1", year=s2),
                   "cum": val(cum, "dec1"), "last": at(full),
                   "prev": at(first - 1), "under": at(under[0])}),
        "economy.unemployment": ctx.story(
            title=ctx.text(
                en="Unemployment of {last_rate} is the PNAD-C low, since "
                   "{start_year}",
                pt="Desemprego de {last_rate} é o menor da PNAD-C, de "
                   "{start_year} em diante"),
            beats=[
                (ctx.text(en="{n_hi} years in a row above {thr}%",
                          pt="{n_hi} anos seguidos acima de {thr}%"),
                 ctx.text(
                    en="From {hi0_year} to {hi1_year}. The {pre_year}-"
                       "{rise_year} climb ({climb} points) was bigger than "
                       "the pandemic one, {c0_year}-{c1_year} ({covid}).",
                    pt="De {hi0_year} a {hi1_year}. A subida de {pre_year} a "
                       "{rise_year} ({climb} pontos) foi maior que a da "
                       "pandemia, de {c0_year} a {c1_year} ({covid}).")),
                (ctx.text(en="{last_rate} and {pme} cannot be compared",
                          pt="{last_rate} e {pme} não se comparam"),
                 ctx.text(
                    en="In {ov_year} the old survey said {pme} and the "
                       "national one {pnad}, for the same year. Different "
                       "surveys: that is why the two lines are never joined.",
                    pt="Em {ov_year} a pesquisa antiga deu {pme} e a "
                       "nacional, {pnad}, no mesmo ano. São pesquisas "
                       "diferentes: por isso as linhas nunca se emendam.")),
                (ctx.text(en="Below where the recession began",
                          pt="Abaixo do nível do início da recessão"),
                 ctx.text(
                    en="Since {top_year} it fell {drop} points in {yrs} "
                       "years. It sits {below} points under {pre_year}, "
                       "when the recession band starts.",
                    pt="Desde {top_year} caiu {drop} pontos em {yrs} anos. "
                       "Está {below} ponto abaixo de {pre_year}, quando "
                       "começa a faixa da recessão.")),
            ],
            facts={"last_rate": val(pnad[last], "pct", year=last),
                   "start": at(start), "n_hi": val(len(hi), "count"),
                   "thr": val(11, "count"), "hi0": at(hi[0]),
                   "hi1": at(hi[-1]), "pre": at(pre), "rise": at(rise_to),
                   "climb": val(climb, "dec1", year=rise_to),
                   "c0": at(2019), "c1": at(top),
                   "covid": val(covid_up, "dec1", year=top),
                   "pme": val(pme[ov], "pct", year=ov),
                   "pnad": val(pnad[ov], "pct", year=ov), "ov": at(ov),
                   "top": at(top), "drop": val(pnad[top] - pnad[last], "dec1"),
                   "yrs": val(last - top, "count"),
                   "below": val(pnad[pre] - pnad[last], "dec1")}),
    }


def fiscal_stories(ctx) -> dict:
    """Insights for the four panels of the fiscal plate (brasil).

    Every number is read from the plate's own CSVs; years written as literals
    are none: all go through facts. Where a sentence is only true while the
    data keep a certain shape, `need` fails the build so the copy is rewritten.
    """
    full = ctx.LAST_FULL_YEAR
    partial = ctx.c.years[-1]
    first = ctx.c.years[0]

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def at(y):
        return val(0, "count", year=y)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil fiscal stories: {why}; rewrite the "
                             f"copy that depends on it")

    gg = lambda c: dict(ctx.col("fiscal/general_government.csv", c))
    rev, exp = gg("revenue_pct_gdp"), gg("expenditure_pct_gdp")
    bal, pb = gg("balance_pct_gdp"), gg("primary_balance_pct_gdp")
    imf = gg("gross_debt_pct_gdp")
    prim = dict(ctx.col("fiscal/primary_result.csv", "value"))
    dbgg = dict(ctx.col("fiscal/debt.csv", "gross"))
    dlsp = dict(ctx.col("fiscal/debt.csv", "net"))
    juros = dict(ctx.col("fiscal/nfsp.csv", "interest"))
    tax = ctx.c.table("fiscal/tax_burden.csv")
    meth = dict(zip(tax["year"], tax["methodology"]))
    taxv = dict(ctx.col("fiscal/tax_burden.csv", "value"))
    span = list(range(first, full + 1))
    for name, s in (("revenue", rev), ("expenditure", exp), ("balance", bal),
                    ("primary", pb), ("IMF debt", imf), ("Treasury primary",
                    prim), ("DBGG", dbgg), ("net debt", dlsp),
                    ("interest", juros)):
        need(set(span) <= set(s), f"{name} has a missing year")
    gap = {y: exp[y] - rev[y] for y in span}
    iint = {y: pb[y] - bal[y] for y in span}     # the plate's red interest line
    rec = [(int(lo), int(hi)) for lo, hi, _ in ctx.c.recessions]

    # ============================================================ panel 1
    de, dr = exp[full] - exp[first], rev[full] - rev[first]
    need(all(g > 0 for g in gap.values()), "spending is not above revenue "
         "every year")
    need(dr > 0 and de > 2 * dr, "spending no longer rose more than twice "
         "as much as revenue")
    need(gap[full] > gap[first], "the gap is not larger at the end")
    y15, y19, y20, y21 = rec[0][0] + 1, rec[1][0] - 1, rec[1][0], rec[1][0] + 1
    need(gap[y20] == max(gap.values()), "the widest gap is not in the "
         "COVID-19 band")
    need(gap[y21] < gap[y19] < gap[y20] and gap[y15] > gap[y19] and
         all(gap[y] > gap[y19] for y in range(y15, y19)),
         "the gap no longer falls slowly after the recession and fast after "
         "COVID-19")
    old = sorted(y for y in taxv if meth.get(y) == "old")
    new = sorted(y for y in taxv if meth.get(y) != "old")
    need(old and new and old[-1] + 1 == new[0],
         "the tax burden is not one old segment followed by a new one")
    ob, nb = old[-1], new[0]
    need(taxv[ob] - taxv[nb] > 1 and abs(rev[nb] - rev[ob]) < 0.5,
         "the tax burden drop at the method break is not visible against "
         "a flat revenue line")

    story_rev = ctx.story(
        title=ctx.text(
            en="Spending vs revenue: gap went from {g0} to {g1} GDP points",
            pt="Despesa e receita: espaço de {g0} passou a {g1} pontos "
               "do PIB"),
        beats=[
            (ctx.text(en="Spending rose over twice as much",
                      pt="A despesa subiu mais que o dobro"),
             ctx.text(
                en="From {first_year} to {last_year}, spending rose {de} "
                   "points of GDP and revenue {dr}. The gap between the "
                   "lines went from {g0} to {g1} points.",
                pt="De {first_year} a {last_year}, a despesa subiu {de} "
                   "pontos do PIB e a receita, {dr}. O espaço entre as "
                   "linhas foi de {g0} para {g1} pontos.")),
            (ctx.text(en="Gap closes slowly, or in one year",
                      pt="Espaço fecha devagar ou em um ano"),
             ctx.text(
                en="The gap fell from {g15} ({g15_year}) to {g19} ({g19_year}). "
                   "In {g20_year} it jumped to {g20} and, in {g21_year}, "
                   "was back at {g21}.",
                pt="O espaço caiu de {g15} ({g15_year}) para {g19} "
                   "({g19_year}). Em {g20_year} saltou para {g20} e, em "
                   "{g21_year}, voltou a {g21}.")),
            (ctx.text(en="{new_year} drop is a method change",
                      pt="Queda de {new_year} é troca de método"),
             ctx.text(
                en="The tax burden (another source) goes from {old_v} in "
                   "{old_year} to {new_v} in {new_year}, while IMF revenue "
                   "barely moves: {r0} to {r1}. The plate does not join "
                   "the two parts.",
                pt="A carga tributária (outra fonte) vai de {old_v} em "
                   "{old_year} para {new_v} em {new_year}, enquanto a "
                   "receita do FMI mal se mexe: {r0} para {r1}. O gráfico "
                   "não une os dois trechos.")),
        ],
        facts={"first": at(first), "last": at(full),
               "de": val(de, "dec1"), "dr": val(dr, "dec1"),
               "g0": val(gap[first], "dec1", year=first),
               "g1": val(gap[full], "dec1"),
               "g15": val(gap[y15], "dec1", year=y15),
               "g19": val(gap[y19], "dec1", year=y19),
               "g20": val(gap[y20], "dec1", year=y20),
               "g21": val(gap[y21], "dec1", year=y21),
               "old": at(ob), "new": at(nb),
               "old_v": val(taxv[ob], "pct", year=ob),
               "new_v": val(taxv[nb], "pct", year=nb),
               "r0": val(rev[ob], "pct", year=ob),
               "r1": val(rev[nb], "pct", year=nb)})

    # ============================================================ panel 2
    need(all(bal[y] < 0 for y in span), "an overall balance is not negative")
    npos = [y for y in span if pb[y] > 0]
    need(all(bal[y] < 0 for y in npos), "a positive primary year has a "
         "nominal surplus")
    since = rec[0][0]
    pos_before = [y for y in span if y < since]
    need(all(pb[y] > 0 for y in pos_before) and
         sorted(y for y in span if y >= since and pb[y] > 0)
         == [rec[1][0] + 1, rec[1][0] + 2], "the primary no longer follows: "
         "positive before the recession, only two positive years after it")
    need(pb[full] < 0 and abs(pb[full]) < 0.1 * abs(bal[full]),
         "the primary is not near zero at the end")
    need(abs(pb[y20]) > 0.5 * abs(bal[y20]), "2020 is not mostly primary")
    best = max(span, key=pb.get)
    dif = {y: prim[y] - pb[y] for y in span}
    top2 = sorted(span, key=lambda y: -abs(dif[y]))[:2]
    need(sorted(top2) == [y20, y21] and dif[y20] < 0 and dif[y21] < 0,
         "the central and general primary no longer differ most in "
         "2020 and 2021")

    story_bal = ctx.story(
        title=ctx.text(
            en="None of the {n} years closed in the black after interest",
            pt="Nenhum dos {n} anos fechou no azul depois dos juros"),
        beats=[
            (ctx.text(en="{last_year} deficit is nearly all interest",
                      pt="Rombo de {last_year}: quase tudo é juros"),
             ctx.text(
                en="In {last_year} (% of GDP), the primary result (before "
                   "interest) was {pb25} and the overall, {bal25}: interest "
                   "is the difference, {i25}. In {y20_year}, the primary was "
                   "{pb20} of {bal20}.",
                pt="Em {last_year} (% do PIB), o primário (antes dos juros) "
                   "foi {pb25} e o nominal, {bal25}: a diferença, {i25}, "
                   "são juros. Em {y20_year}, o primário foi {pb20} "
                   "de {bal20}.")),
            (ctx.text(en="A positive primary never sufficed",
                      pt="Primário positivo nunca bastou"),
             ctx.text(
                en="The primary was positive in {npos} of the {n} years, "
                   "and no bar reached zero. The best, {best} in "
                   "{best_year}, still left the overall at {bal_best}.",
                pt="O primário foi positivo em {npos} dos {n} anos, e "
                   "nenhuma barra chegou a zero. O melhor, {best} em "
                   "{best_year}, ainda deixou o nominal em {bal_best}.")),
            (ctx.text(en="Since {since_year}, positive primary only twice",
                      pt="Desde {since_year}, primário positivo só duas vezes"),
             ctx.text(
                en="The general-government primary was positive from "
                   "{first_year} to {pre_year}. Since {since_year}, only "
                   "{c0_year} and {c1_year} left the red.",
                pt="O primário do governo geral foi positivo de "
                   "{first_year} a {pre_year}. Desde {since_year}, só "
                   "{c0_year} e {c1_year} saíram do vermelho.")),
            (ctx.text(en="The yellow line is a smaller set",
                      pt="A linha amarela é um recorte menor"),
             ctx.text(
                en="It covers only the central government. It strays most "
                   "in {y20_year} ({pr20} against {pb20}) and {y21_year} "
                   "({pr21} against {pb21}). The two sets do not swap.",
                pt="Cobre só o governo central. Destoa mais em {y20_year} "
                   "({pr20} contra {pb20}) e {y21_year} ({pr21} contra "
                   "{pb21}). Os dois recortes não se trocam.")),
        ],
        facts={"n": val(len(span), "count"), "npos": val(len(npos), "count"),
               "last": at(full), "first": at(first),
               "pb25": val(pb[full], "pct_s"),
               "bal25": val(bal[full], "pct_s"),
               "i25": val(iint[full], "pct"),
               "y20": at(y20), "y21": at(y21),
               "pb20": val(pb[y20], "pct_s", year=y20),
               "bal20": val(bal[y20], "pct_s", year=y20),
               "best": val(pb[best], "pct_s", year=best),
               "bal_best": val(bal[best], "pct_s", year=best),
               "pre": at(since - 1), "since": at(since),
               "c0": at(y21), "c1": at(rec[1][0] + 2),
               "pr20": val(prim[y20], "pct_s", year=y20),
               "pr21": val(prim[y21], "pct_s", year=y21),
               "pb21": val(pb[y21], "pct_s", year=y21)})

    # ============================================================ panel 3
    need(all(imf[y] > dbgg[y] > dlsp[y] for y in span),
         "the three definitions no longer stack IMF > DBGG > net")
    pk = y20
    need(imf[pk] == max(imf[y] for y in span) and
         dbgg[pk] == max(dbgg[y] for y in span), "the gross debt peak is "
         "no longer in the COVID-19 year")
    need(imf[full] < imf[pk] and dbgg[full] < dbgg[pk] and
         dlsp[full] > dlsp[pk], "net debt is no longer above its peak-year "
         "level while the gross ones are below")
    nlow = min(span, key=dlsp.get)
    need(dlsp[full] > 2 * dlsp[nlow], "net debt no longer more than doubled")
    pre = [y for y in span if y < since]
    post = [y for y in span if y > since]
    need(min(imf[y] for y in post) > max(imf[y] for y in pre) and
         min(dbgg[y] for y in post) > max(dbgg[y] for y in pre),
         "the gross debt came back to its earlier range")
    imin = min(post, key=imf.get)
    need(partial in dbgg and partial in dlsp and partial not in imf,
         "the running year is no longer on the BCB lines only")
    need(dbgg[partial] > dbgg[full] and dlsp[partial] > dlsp[full],
         "the running year is no longer above the last full year")
    need((imf[pk] - imf[full]) < (dbgg[pk] - dbgg[full]),
         "the IMF line no longer falls less than DBGG after the peak")

    story_debt = ctx.story(
        title=ctx.text(
            en="{last_year} debt: from {net} to {imf} of GDP, by the "
               "measure",
            pt="Dívida de {last_year}: de {net} a {imf} do PIB, conforme "
               "a medida"),
        beats=[
            (ctx.text(en="The measure changes how much it fell",
                      pt="A régua muda o tamanho do recuo"),
             ctx.text(
                en="From {pk_year} to {last_year}, IMF gross debt fell {d_imf} "
                   "points of GDP; DBGG, {d_dbgg}. The distance between "
                   "them went from {s0} to {s1}.",
                pt="De {pk_year} a {last_year}, a bruta do FMI recuou "
                   "{d_imf} pontos do PIB; a DBGG, {d_dbgg}. A distância "
                   "entre elas foi de {s0} para {s1}.")),
            (ctx.text(en="Net debt more than doubled",
                      pt="A líquida mais que dobrou"),
             ctx.text(
                en="From {nlow_year} to {last_year}, net debt went from "
                   "{nlow} to {net}, above its {net_pk} of {pk_year}. Both "
                   "gross lines are still below their {pk_year} peaks.",
                pt="De {nlow_year} a {last_year}, a líquida foi de {nlow} "
                   "para {net}, acima dos {net_pk} de {pk_year}. As duas "
                   "brutas seguem abaixo dos picos de {pk_year}.")),
            (ctx.text(en="Debt never returned to the earlier range",
                      pt="A dívida não voltou ao patamar anterior"),
             ctx.text(
                en="Through {pre_year}, IMF gross debt never passed "
                   "{pre_max}; since {post_year}, it has not been under "
                   "{post_min}. DBGG: {d_post_min} against {d_pre_max}.",
                pt="Até {pre_year}, a bruta do FMI não passou de "
                   "{pre_max}; desde {post_year}, não ficou abaixo de "
                   "{post_min}. DBGG: {d_post_min} contra {d_pre_max}.")),
            (ctx.text(en="{partial_year} is a partial point",
                      pt="{partial_year} é um ponto parcial"),
             ctx.text(
                en="The dashed {partial_year} point is August, BCB only: "
                   "DBGG {d26}, net {n26}, both above {last_year}. The IMF "
                   "line stops in {last_year}.",
                pt="O ponto tracejado de {partial_year} é agosto, só do "
                   "BCB: DBGG {d26}, líquida {n26}, ambas acima de "
                   "{last_year}. A linha do FMI para em {last_year}.")),
        ],
        facts={"last": at(full), "partial": at(partial),
               "net": val(dlsp[full], "pct"), "imf": val(imf[full], "pct"),
               "pk": at(pk),
               "d_imf": val(imf[pk] - imf[full], "dec1"),
               "d_dbgg": val(dbgg[pk] - dbgg[full], "dec1"),
               "s0": val(imf[pk] - dbgg[pk], "dec1", year=pk),
               "s1": val(imf[full] - dbgg[full], "dec1"),
               "nlow": val(dlsp[nlow], "pct", year=nlow),
               "net_pk": val(dlsp[pk], "pct", year=pk),
               "pre": at(since - 1),
               "pre_max": val(max(imf[y] for y in pre), "pct",
                              year=max(pre, key=imf.get)),
               "d_pre_max": val(max(dbgg[y] for y in pre), "pct",
                                year=max(pre, key=dbgg.get)),
               "post": at(min(post)),
               "post_min": val(imf[imin], "pct", year=imin),
               "d_post_min": val(min(dbgg[y] for y in post), "pct",
                                 year=min(post, key=dbgg.get)),
               "d26": val(dbgg[partial], "pct", year=partial),
               "n26": val(dlsp[partial], "pct", year=partial)})

    # ============================================================ panel 4
    need(full - y20 == 5, "the trough is no longer five years back")
    lo = min(span, key=juros.get)
    hi = max(span, key=juros.get)
    need(lo == min(span, key=iint.get) == y20 and
         hi == max(span, key=iint.get) == rec[0][0] + 1,
         "the two interest measures no longer share trough (COVID-19 year) "
         "and peak (recession)")
    need(all(iint[y] < iint[y + 1] for y in range(y20, full)),
         "the IMF interest line no longer rises every year since the trough")
    need(juros[full] > 1.8 * juros[y20] and juros[full] < juros[hi],
         "the BCB interest no longer nearly doubled below its peak")
    need(juros[hi] - juros[hi - 1] > 2 and juros[hi] - juros[hi + 1] > 1.5,
         "the peak is no longer a one-year jump")
    wid = max(span, key=lambda y: abs(iint[y] - juros[y]))
    need(wid == full - 1 and abs(iint[wid] - juros[wid]) > 1.5 and
         sorted(span, key=lambda y: -abs(iint[y] - juros[y]))[1] != full,
         "the widest gap between the two interest measures moved")

    story_int = ctx.story(
        title=ctx.text(
            en="Interest paid: {min} of GDP in {min_year}, {last} in "
               "{last_year} (BCB)",
            pt="Juros pagos: {min} do PIB em {min_year} e {last} em "
               "{last_year} (BCB)"),
        beats=[
            (ctx.text(en="Interest nearly doubled in five years",
                      pt="Juros quase dobraram em cinco anos"),
             ctx.text(
                en="The trough, {min} in {min_year}, is the lowest of both "
                   "measures. In {last_year} the BCB measure reached {last} "
                   "and the IMF one {last_imf}; the {hi_year} peak was "
                   "{hi}.",
                pt="O fundo, {min} em {min_year}, é o menor das duas "
                   "medidas. Em {last_year} a do BCB chegou a {last} e a do "
                   "FMI, a {last_imf}; o pico de {hi_year} foi {hi}.")),
            (ctx.text(en="{hi_year} jump; steady climb since {min_year}",
                      pt="Salto em {hi_year}; subida contínua desde {min_year}"),
             ctx.text(
                en="By the BCB measure, interest jumped {jump} points in "
                   "{hi_year} and fell {drop} the next year. Since "
                   "{min_year}, the IMF measure rose every year.",
                pt="Pela medida do BCB, os juros saltaram {jump} pontos em "
                   "{hi_year} e caíram {drop} no ano seguinte. Desde "
                   "{min_year}, a medida do FMI subiu todos os anos.")),
            (ctx.text(en="Same turns, different levels",
                      pt="Mesmas viradas, níveis diferentes"),
             ctx.text(
                en="Both peak in {hi_year} and bottom in {min_year}, but in "
                   "{wid_year} one reads {w_imf} and the other {w_bcb}: "
                   "different sets, not interchangeable.",
                pt="Ambas têm pico em {hi_year} e fundo em {min_year}, mas "
                   "em {wid_year} uma marca {w_imf} e a outra {w_bcb}: "
                   "recortes diferentes, não intercambiáveis.")),
        ],
        facts={"min": val(juros[lo], "pct", year=lo),
               "last": val(juros[full], "pct"),
               "last_imf": val(iint[full], "pct"),
               "hi": val(juros[hi], "pct", year=hi),
               "jump": val(juros[hi] - juros[hi - 1], "dec1", year=hi),
               "drop": val(juros[hi] - juros[hi + 1], "dec1", year=hi),
               "wid": at(wid),
               "w_imf": val(iint[wid], "pct", year=wid),
               "w_bcb": val(juros[wid], "pct", year=wid)})

    return {"fiscal.revenue_expenditure": story_rev,
            "fiscal.balance": story_bal,
            "fiscal.debt": story_debt,
            "fiscal.interest": story_int}


def spending_stories(ctx) -> dict:
    """The four panels of the spending plate as insights, read from the CSVs
    each panel draws (cofog.csv, investment.csv, public_investment.csv).

    Panel 1 stacks seven COFOG functions (general government, from 2010);
    panel 2 splits the same total into social protection and everything
    else; panel 3 is the whole-economy investment rate (IBGE); panel 4 draws
    two different measures of public investment, the OECD one ending in 2020.
    Every number is a fact read from the CSVs; where a sentence holds only
    while the data keep a shape, `need` fails the build instead.
    """
    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil spending stories: {why}; rewrite the "
                             f"copy that depends on it")

    at = lambda y: val(0, "count", year=y)      # a year, as a fact
    bands = ctx.c.recessions
    in_band = lambda y: any(lo <= y <= hi for lo, hi, _ in bands)

    groups = ("social_protection", "health", "education", "general_public",
              "economic_affairs", "defence_order", "other")
    g = {k: dict(ctx.col("fiscal/cofog.csv", k)) for k in groups}
    yrs = sorted(g["social_protection"])
    first, last = yrs[0], yrs[-1]
    tot = {y: sum(g[k].get(y, 0.0) for k in groups) for y in yrs}
    sp, gp, hl, ed = (g["social_protection"], g["general_public"],
                      g["health"], g["education"])
    rest = {y: tot[y] - sp[y] for y in yrs}
    inv = dict(ctx.col("fiscal/investment.csv", "fbcf_pib"))
    fed = dict(ctx.col("fiscal/investment.csv", "federal_rtn_gnd45_pib"))
    pub = {y: v for y, v in ctx.col("fiscal/public_investment.csv",
                                    "gov_gfcf_pct_gdp") if y >= ctx.c.years[0]}

    # ---- panel 1: stacked functions
    need(last <= full, "the stack runs past the last full year")
    need(tot[last] > tot[first], "the total is not above its first year")
    rise = tot[last] - tot[first]
    need(rise > 0 and sp[last] - sp[first] > rise / 2,
         "social protection is no longer more than half of the rise")
    need(all(g[k][last] - g[k][first] < hl[last] - hl[first]
             for k in groups if k not in ("social_protection", "health")),
         "health is no longer the second-largest contributor to the rise")
    need(gp[2015] - gp[2014] > 0.8 * (tot[2015] - tot[2014])
         and sp[2015] - sp[2014] < 1.0,
         "general public services no longer carry most of the 2015 jump")
    need(in_band(2015) and in_band(2014), "2015 is no longer inside a band")
    need(abs(tot[2015] - tot[2020]) < 0.1 and gp[2015] > gp[2020]
         and sp[2020] > sp[2015],
         "2015 and 2020 are no longer same-height with swapped layers")
    need(ed[first] > hl[first] and abs(ed[last] - hl[last]) < 0.2,
         "health no longer almost meets education")

    # ---- panel 2: social protection against the rest
    need(max(sp, key=sp.get) == 2020 and max(rest, key=rest.get) == 2015,
         "the two peaks moved")
    need(in_band(2020) and in_band(2015), "a peak left its band")
    need(sp[2021] < sp[2019] and abs(sp[last] - sp[2019]) < 0.1,
         "2024 is no longer level with 2019 for social protection")
    need(rest[2020] < rest[2019] and rest[2015] - rest[2014] > 3
         and sp[2015] - sp[2014] < 1.0,
         "the lines no longer peak in different crises")
    share = lambda y: 100 * sp[y] / tot[y]
    need(share(2020) > 45 and share(2020) > share(first) + 10
         and share(2020) > share(last) + 5, "the 2020 share is no longer an outlier")

    # ---- panel 3: investment rate
    hi, lo = max(inv), min(inv)
    hi, lo = max(inv, key=inv.get), min(inv, key=inv.get)
    inv_last = max(inv)
    need(inv_last <= full and lo > hi, "the investment peak/low order moved")
    need(lo == int(bands[0][1]) + 1, "the low is no longer the year after the band")
    falls = [y for y in range(hi + 1, lo + 1) if inv[y] < inv[y - 1]]
    need(len(falls) == lo - hi, "the fall is no longer unbroken")
    need(inv[lo] < inv[inv_last] < inv[hi], "latest rate left the low-peak span")
    ifirst = min(inv)
    need(all(inv[y] > inv[inv_last] for y in range(ifirst, 2016)),
         "the latest rate is no longer below every year up to 2015")
    need(inv[2020] > inv[2019] and in_band(2020) and in_band(2016),
         "the rate no longer rises in 2020")
    recovered = 100 * (inv[inv_last] - inv[lo]) / (inv[hi] - inv[lo])
    need(recovered < 50, "the rate recovered more than half of the fall")

    # ---- panel 4: public investment, two measures
    p_end, f_end = max(pub), max(fed)
    p_top = max(pub, key=pub.get)
    p_low = min(pub, key=pub.get)
    need(p_end == 2020 and p_top == first and p_low > p_top,
         "the OECD series changed shape")
    need(p_end < f_end and f_end == max(inv), "the federal series moved")
    need(max(fed, key=fed.get) == 2020 and fed[2021] < fed[2019]
         and 2021 in fed, "the federal peak moved")
    need(all(fed[f_end] < fed[y] for y in fed if y <= 2020),
         "the latest federal reading is no longer below every year to 2020")
    need(p_top in inv and p_low in inv, "no investment rate to compare with")
    gshare = lambda y: 100 * pub[y] / inv[y]
    need(gshare(p_low) < gshare(p_top), "the government share did not fall")
    need(2014 in pub and 2017 in pub and p_low >= 2017 and in_band(2014)
         and (pub[2014] - pub[2017]) > 0.7 * (pub[p_top] - pub[p_low]),
         "most of the public-investment fall is no longer in 2014-2017")

    return {
        "spending.by_function": ctx.story(
            title=ctx.text(
                en="Social protection explains most of the rise in spending",
                pt="Proteção social explica mais da metade da alta do gasto"),
            beats=[
                (ctx.text(en="Bottom layer: {sp_share} of the rise",
                          pt="A base responde por {sp_share} da alta"),
                 ctx.text(
                    en="From {first_year} to {last_year} spending rose "
                       "{rise} points of GDP. Social protection, the bottom "
                       "layer, added {sp_rise}; health, the runner-up, "
                       "added {h_rise}.",
                    pt="De {first_year} a {last_year}, o gasto subiu {rise} "
                       "pontos do PIB. A proteção social, camada de baixo, "
                       "somou {sp_rise}; a saúde, segunda maior, {h_rise}.")),
                (ctx.text(en="One layer explains the {gp15_year} jump",
                          pt="Uma camada explica o salto de {gp15_year}"),
                 ctx.text(
                    en="Spending rose {t_jump} points of GDP between "
                       "{gp14_year} and {gp15_year}; {gp_share} of it is the "
                       "red layer, general public services (interest "
                       "included). The chart does not say why.",
                    pt="O gasto subiu {t_jump} pontos do PIB de {gp14_year} "
                       "para {gp15_year}; {gp_share} veio da camada "
                       "vermelha, serviços públicos gerais (inclui juros). "
                       "O gráfico não diz o motivo.")),
                (ctx.text(en="{gp15_year} and {sp20_year}: same total, swapped "
                             "layers",
                          pt="{gp15_year} e {sp20_year}: mesmo total, "
                             "camadas trocadas"),
                 ctx.text(
                    en="Total spending was {t15} of GDP in {gp15_year} and "
                       "{t20} in {sp20_year}. Red went from {gp15} to "
                       "{gp20}; social protection went from {sp15} to "
                       "{sp20}.",
                    pt="O gasto total foi {t15} do PIB em {gp15_year} e "
                       "{t20} em {sp20_year}. O vermelho foi de {gp15} para "
                       "{gp20}; a proteção social, de {sp15} para {sp20}.")),
                (ctx.text(en="Health nearly caught up with education",
                          pt="Saúde quase alcançou a educação"),
                 ctx.text(
                    en="In {first_year}, education spent {ed_first} of GDP "
                       "and health {h_first}. In {last_year}: {ed_last} and "
                       "{h_last}, a gap of {gap} points.",
                    pt="Em {first_year}, a educação gastava {ed_first} do "
                       "PIB e a saúde, {h_first}. Em {last_year}: "
                       "{ed_last} e {h_last}, diferença de {gap} pontos.")),
            ],
            facts={
                "first": at(first), "last": at(last),
                "sp_share": val(100 * (sp[last] - sp[first]) / rise, "pct",
                                year=last),
                "rise": val(rise, "dec1", year=last),
                "sp_rise": val(sp[last] - sp[first], "dec1", year=last),
                "h_rise": val(hl[last] - hl[first], "dec1", year=last),
                "t_jump": val(tot[2015] - tot[2014], "dec1", year=2015),
                "gp14": at(2014), "gp15": val(gp[2015], "pct", year=2015),
                "gp_share": val(100 * (gp[2015] - gp[2014])
                                / (tot[2015] - tot[2014]), "pct", year=2015),
                "sp20": val(sp[2020], "pct", year=2020),
                "sp15": val(sp[2015], "pct", year=2015),
                "gp20": val(gp[2020], "pct", year=2020),
                "t15": val(tot[2015], "pct", year=2015),
                "t20": val(tot[2020], "pct", year=2020),
                "ed_first": val(ed[first], "pct", year=first),
                "h_first": val(hl[first], "pct", year=first),
                "ed_last": val(ed[last], "pct", year=last),
                "h_last": val(hl[last], "pct", year=last),
                "gap": val(ed[last] - hl[last], "dec2", year=last)}),
        "spending.social_protection": ctx.story(
            title=ctx.text(
                en="In {s20_year}, social protection was {s20} of all "
                   "spending",
                pt="Em {s20_year}, a proteção social foi {s20} de todo o "
                   "gasto"),
            beats=[
                (ctx.text(en="From a third to nearly half",
                          pt="De um terço a quase metade"),
                 ctx.text(
                    en="Social protection's share of total spending: "
                       "{s10} in {s10_year}, {s20} in {s20_year}, {s24} in "
                       "{s24_year}. The blue line is a slice, the grey one "
                       "the other {n_rest} functions.",
                    pt="A fatia da proteção social no gasto total: {s10} em "
                       "{s10_year}, {s20} em {s20_year}, {s24} em "
                       "{s24_year}. A linha azul é uma fatia; a cinza soma "
                       "as outras {n_rest} funções.")),
                (ctx.text(en="The {s20_year} peak was not a new floor",
                          pt="O pico de {s20_year} não virou novo piso"),
                 ctx.text(
                    en="After {sp20} in {s20_year}, the line fell to {sp21} "
                       "in {sp21_year}, below the {sp19} of {sp19_year}, and "
                       "ended at {sp24} in {s24_year}: where it was before.",
                    pt="Depois de {sp20} em {s20_year}, a linha caiu a "
                       "{sp21} em {sp21_year}, abaixo dos {sp19} de "
                       "{sp19_year}, e terminou em {sp24} em {s24_year}: "
                       "onde estava antes.")),
                (ctx.text(en="Each line peaks in a different crisis",
                          pt="Cada linha tem seu pico numa crise"),
                 ctx.text(
                    en="Grey peaks at {r15} in {r15_year}, in the recession "
                       "band, while blue barely moves. In {s20_year} it "
                       "flips: blue rises, grey falls from {r19} to {r20}.",
                    pt="A cinza chega a {r15} em {r15_year}, na faixa de "
                       "recessão, e a azul quase não se mexe. Em {s20_year} "
                       "inverte: a azul sobe, a cinza cai de {r19} para "
                       "{r20}.")),
            ],
            facts={
                "n_rest": val(len(groups) - 1, "count"),
                "s10": val(share(first), "pct", year=first),
                "s20": val(share(2020), "pct", year=2020),
                "s24": val(share(last), "pct", year=last),
                "sp20": val(sp[2020], "pct", year=2020),
                "sp21": val(sp[2021], "pct", year=2021),
                "sp19": val(sp[2019], "pct", year=2019),
                "sp24": val(sp[last], "pct", year=last),
                "r15": val(rest[2015], "pct", year=2015),
                "r19": val(rest[2019], "pct", year=2019),
                "r20": val(rest[2020], "pct", year=2020)}),
        "spending.investment": ctx.story(
            title=ctx.text(
                en="The investment rate regained only {rec} of its fall",
                pt="A taxa de investimento recuperou só {rec} da queda"),
            beats=[
                (ctx.text(en="{n_fall} straight falls, then the floor",
                          pt="{n_fall} quedas seguidas até o fundo"),
                 ctx.text(
                    en="The share of GDP put into machines, buildings and "
                       "works fell every year from {hi} in {hi_year} to "
                       "{lo} in {lo_year}, a year after the recession band "
                       "ends.",
                    pt="A parcela do PIB aplicada em máquinas, prédios e "
                       "obras caiu todo ano, de {hi} em {hi_year} a {lo} em "
                       "{lo_year}, um ano depois do fim da faixa de "
                       "recessão.")),
                (ctx.text(en="Regained {up} of {drop} points lost",
                          pt="Voltou {up} dos {drop} pontos perdidos"),
                 ctx.text(
                    en="From the {lo_year} low of {lo}, the rate climbed to "
                       "{latest} in {latest_year}: still {to_peak} points "
                       "under the {hi} of {hi_year}.",
                    pt="Do fundo de {lo_year}, {lo}, a taxa subiu a "
                       "{latest} em {latest_year}: ainda {to_peak} pontos "
                       "abaixo dos {hi} de {hi_year}.")),
                (ctx.text(en="Below every year through {y15_year}",
                          pt="Abaixo de qualquer ano até {y15_year}"),
                 ctx.text(
                    en="The {latest_year} rate of {latest} is lower than "
                       "any year from {first_year} ({f_first}) through "
                       "{y15_year} ({f15}), so the line starts higher "
                       "than it ends.",
                    pt="A taxa de {latest_year}, {latest}, é menor que a de "
                       "qualquer ano de {first_year} ({f_first}) a "
                       "{y15_year} ({f15}): a linha termina abaixo de onde "
                       "começa.")),
                (ctx.text(en="In the COVID band the rate rose",
                          pt="Na faixa da covid a taxa subiu"),
                 ctx.text(
                    en="From {i19} in {i19_year} to {i20} in {i20_year}, the "
                       "opposite of the 2014–16 band, when it fell from "
                       "{hi} to {i16}.",
                    pt="De {i19} em {i19_year} para {i20} em {i20_year}, o "
                       "oposto da faixa de 2014–16, quando caiu de {hi} "
                       "para {i16}.")),
            ],
            facts={
                "n_fall": val(len(falls), "count"),
                "hi": val(inv[hi], "pct", year=hi),
                "lo": val(inv[lo], "pct", year=lo),
                "latest": val(inv[inv_last], "pct", year=inv_last),
                "rec": val(recovered, "pct", year=inv_last),
                "drop": val(inv[hi] - inv[lo], "dec1", year=lo),
                "up": val(inv[inv_last] - inv[lo], "dec1", year=inv_last),
                "to_peak": val(inv[hi] - inv[inv_last], "dec1",
                               year=inv_last),
                "first": at(ifirst),
                "f_first": val(inv[ifirst], "pct", year=ifirst),
                "y15": at(2015),
                "f15": val(inv[2015], "pct", year=2015),
                "i19": val(inv[2019], "pct", year=2019),
                "i20": val(inv[2020], "pct", year=2020),
                "i16": val(inv[2016], "pct", year=2016)}),
        "spending.public_investment": ctx.story(
            title=ctx.text(
                en="In {low_year}, government invested {ratio} of its "
                   "{top_year} level",
                pt="Em {low_year}, o governo investia {ratio} do que em "
                   "{top_year}"),
            beats=[
                (ctx.text(en="{q_share} of the fall: {p14_year} to {p17_year}",
                          pt="{q_share} da queda: {p14_year} a {p17_year}"),
                 ctx.text(
                    en="The line was still at {p14} of GDP in {p14_year} "
                       "and reached {p17} in {p17_year}: that stretch holds "
                       "{q_share} of the whole fall, {top} ({top_year}) to "
                       "{low} ({low_year}).",
                    pt="A linha ainda estava em {p14} do PIB em {p14_year} "
                       "e chegou a {p17} em {p17_year}: esse trecho é "
                       "{q_share} da queda toda, de {top} ({top_year}) a "
                       "{low} ({low_year}).")),
                (ctx.text(en="Government's slice of all investment shrank",
                          pt="A fatia do governo no investimento encolheu"),
                 ctx.text(
                    en="The green line over the whole-economy rate (side "
                       "panel): {gs_top} in {top_year}, {gs_low} in "
                       "{low_year}. Two sources, so read it as an order of "
                       "magnitude.",
                    pt="A linha verde dividida pela taxa da economia toda "
                       "(painel ao lado): {gs_top} em {top_year}, {gs_low} "
                       "em {low_year}. São duas fontes: vale como ordem de "
                       "grandeza.")),
                (ctx.text(en="The federal {f20_year} peak lasted a year",
                          pt="O pico federal de {f20_year} durou um ano"),
                 ctx.text(
                    en="The yellow line went from {f19} to {f20} in "
                       "{f20_year} and back to {f21} in {f21_year}. In "
                       "{f25_year}, {f25} is below every year through "
                       "{f20_year}.",
                    pt="A amarela foi de {f19} a {f20} em {f20_year} e "
                       "voltou a {f21} em {f21_year}. Em {f25_year}, {f25} "
                       "fica abaixo de todos os anos até {f20_year}.")),
                (ctx.text(en="After {end_year}, only a different measure",
                          pt="Depois de {end_year}, só outra medida"),
                 ctx.text(
                    en="The green line stops in {end_year}. From "
                       "{f21_year} on only the yellow one remains: federal "
                       "money paid, not all governments. What general "
                       "government invested later is not here.",
                    pt="A verde para em {end_year}. De {f21_year} em diante "
                       "só resta a amarela: dinheiro federal pago, não todos "
                       "os governos. O que o governo geral investiu depois "
                       "não está aqui.")),
            ],
            facts={
                "top": val(pub[p_top], "pct2", year=p_top),
                "low": val(pub[p_low], "pct2", year=p_low),
                "ratio": val(100 * pub[p_low] / pub[p_top], "pct",
                             year=p_low),
                "end": at(p_end),
                "p14": val(pub[2014], "pct2", year=2014),
                "p17": val(pub[2017], "pct2", year=2017),
                "q_share": val(100 * (pub[2014] - pub[2017])
                               / (pub[p_top] - pub[p_low]), "pct",
                               year=2017),
                "gs_top": val(gshare(p_top), "pct", year=p_top),
                "gs_low": val(gshare(p_low), "pct", year=p_low),
                "f19": val(fed[2019], "pct2", year=2019),
                "f20": val(fed[2020], "pct2", year=2020),
                "f21": val(fed[2021], "pct2", year=2021),
                "f25": val(fed[f_end], "pct2", year=f_end)}),
    }


def trade_stories(ctx) -> dict:
    """The four panels of the trade plate, as insights read from its CSVs.

    Panel 1 draws exports and imports of goods and services as a share of GDP
    (World Bank); the note beside it is a different measure (goods only,
    US$ bn, SECEX). Panel 2 is their difference, in bars. Panel 3 is the
    share of goods exports by destination in snapshot years joined by lines.
    Panel 4 is the top export groups in snapshot years, 'others' left out.

    Where a sentence is only true while the data keep a certain shape, the
    build fails when they stop, so the copy is rewritten instead of quietly
    going wrong.
    """
    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil trade stories: {why}; rewrite the "
                             f"copy that depends on it")

    at = lambda y: val(0, "count", year=y)      # a year, as a fact

    first = ctx.c.years[0]
    partial = ctx.c.years[-1]
    in_band = lambda y: any(lo <= y <= hi for lo, hi, _ in ctx.c.recessions)

    # ---- panels 1 and 2: the national-accounts lines and their difference
    xs = {y: v for y, v in ctx.col("trade/national_accounts.csv",
                                   "exports_pct_gdp") if first <= y <= full}
    ms = {y: v for y, v in ctx.col("trade/national_accounts.csv",
                                   "imports_pct_gdp") if first <= y <= full}
    span = sorted(y for y in xs if y in ms)
    need(span == list(range(first, full + 1)), "the lines have a gap")
    need(partial not in xs, "the running year now has a point")
    bal = {y: xs[y] - ms[y] for y in span}

    hi_x = max(span, key=xs.get)
    hi_m = max(span, key=ms.get)
    need(hi_x == hi_m == 2022, "the two highest points are no longer 2022")
    hi_y = hi_x
    hi = max(xs[hi_y], ms[hi_y])
    need(hi < 20, "the highest point is no longer under a fifth of GDP")
    need(in_band(2020) and not in_band(2022), "the COVID band moved")

    pre = [v for y in span if y < 2020 for v in (xs[y], ms[y])]
    post = [v for y in span if y >= 2020 for v in (xs[y], ms[y])]
    need(min(post) > max(pre), "the post-2020 floor is not above the old "
                               "ceiling")
    pre_max, post_min = max(pre), min(post)

    dx = xs[hi_y] - xs[hi_y + 1]
    dm = ms[hi_y] - ms[hi_y + 1]
    need(dx > 0 and dm > 2 * dx, "imports no longer fall more than twice "
                                  "as much as exports after the peak")
    y_next = hi_y + 1
    need(bal[y_next] == max(bal[y] for y in span if y > 2006),
         "the year after the peak is no longer the tallest bar after 2006")

    gx = dict(ctx.col("trade/trade.csv", "exports"))
    gm = dict(ctx.col("trade/trade.csv", "imports"))
    gb = dict(ctx.col("trade/trade.csv", "balance"))
    need(gb[full] > 0, "the goods balance is no longer a surplus")
    need(0 < bal[full] < 1, "the latest bar is no longer thin")

    bound = max(abs(v) for v in bal.values())
    need(bound < 3, "the bars are no longer within three points of zero")
    worst = min(span, key=bal.get)
    best = max(span, key=bal.get)
    need(worst == 2014 and best == first, "the extreme bars moved")
    run_start = min(y for y in span if bal[y] < 0)
    run_end = 2015
    run = list(range(run_start, run_end + 1))
    need(run_start == 2008 and all(bal[y] < 0 for y in run),
         "the red run is no longer 2008-2015 without a hole")
    need(all(bal[y] > 0 for y in range(first, run_start) ),
         "the bars before the red run are no longer green")
    need(bal[run_end + 1] > 0, "the year after the run is not green")
    need(worst - first == 8 and bal[worst + 2] > 0 and bal[worst + 1] < 0,
         "the eight-down, two-up pattern is gone")
    red_sum = sum(bal[y] for y in run)
    green_years = [y for y in span if y > run_end]
    green_sum = sum(bal[y] for y in green_years)
    need(red_sum < 0 < green_sum < -red_sum,
         "the later bars no longer add up to less than the red run")
    need(bal[y_next] > 0.2 * green_sum, "the peak year is no longer a big "
                                        "part of the later bars")
    need(max(bal[y] for y in green_years if y != y_next) < 1,
         "another later bar is now above one point")

    # ---- panel 3: destinations
    d = ctx.c.table("trade/destinations.csv")
    share = {}
    for y, n, v in zip(d["year"], d["destiny"], d["share_pct"]):
        if v == v:
            share.setdefault(n, {})[int(y)] = float(v)
    snaps = sorted(share["China"])
    need(partial in snaps, "the running year has no destination snapshot")
    snaps_full = [y for y in snaps if y <= full]
    cn, us, eu, ar = (share[k] for k in ("China", "United States",
                                         "European Union", "Argentina"))
    need(cn[first] < min(us[first], eu[first], ar[first]),
         "China is no longer the smallest of the four lines in the first year")
    y15, y20, y24 = 2015, 2020, 2024
    need(all(y in snaps for y in (y15, y20, y24)), "a snapshot year is gone")
    need(all(cn[y] > max(us[y], eu[y], ar[y])
             for y in snaps_full if y >= y15),
         "China is no longer first in every snapshot from 2015")
    need(not any(y15 > y > first and cn[y] > max(us[y], eu[y], ar[y])
                 for y in snaps), "China already led before 2015")
    for y in snaps_full:
        if y >= y20:
            need(cn[y] > us[y] + eu[y],
                 "China no longer beats the US and the EU together")
    need(max(snaps_full, key=cn.get) == y20 and in_band(y20),
         "the China peak left 2020")
    for s in (us, eu, ar):
        need(s[full] < s[first], "a destination no longer ends below start")
    need(gx[full] > gx[first], "goods exports no longer grew")

    # ---- panel 4: the lens
    p = ctx.c.table("trade/exports_products.csv")
    usbi = {(int(y), g): float(v) for y, g, v
            in zip(p["year"], p["product"], p["usbi"])}
    pick = [y for y in (2006, 2010, 2015, 2020, 2025)
            if any(k[0] == y for k in usbi)]
    need(pick[-1] == full and len(pick) == 5, "the lens years changed")
    groups = ["oil", "soy", "iron", "meat", "sugar", "coffee", "corn",
              "pulp", "steel", "autos", "aircraft"]
    g = lambda y, k: usbi[(y, k)]
    y06, y10, y15p = pick[0], pick[1], pick[2]
    for y in pick:
        need(abs(sum(g(y, k) for k in groups) + usbi[(y, "others")] - gx[y])
             < 0.1, "the groups no longer add up to the goods exports")
    leaders = [max(groups, key=lambda k: g(y, k)) for y in pick]
    need(leaders == ["oil", "iron", "soy", "soy", "oil"],
         "the leading group per snapshot changed")
    need(len(set(leaders)) == 3, "the number of leaders changed")
    need(g(y10, "iron") > 1.9 * g(y15p, "iron") and
         g(y15p, "soy") > g(y10, "soy"),
         "iron no longer halves while soy keeps rising")
    two = lambda y: g(y, "oil") + g(y, "soy")
    s06, s25 = two(y06) / gx[y06] * 100, two(full) / gx[full] * 100
    need(s25 > 2 * s06, "the oil and soy share no longer more than doubles")
    need(abs(g(full, "oil") - g(full, "soy")) < 0.05 * g(full, "oil"),
         "oil and soy no longer almost tie in the last year")
    others = usbi[(full, "others")]
    others_pct = others / gx[full] * 100
    need(others > max(g(full, k) for k in groups),
         "the residual is no longer larger than every bar")
    need(30 < others_pct < 37, "the residual is no longer about a third")
    small = [g(y, k) for y in pick for k in ("steel", "autos", "aircraft")]
    need(max(small) < 7 and g(full, "oil") > 5 * g(y06, "oil"),
         "steel, autos and aircraft no longer stay small beside oil")

    return {
        "trade.exports_imports": ctx.story(
            title=ctx.text(
                en="Neither exports nor imports top {hi} of GDP",
                pt="Vendas e compras externas nunca passam de {hi} do PIB"),
            beats=[
                (ctx.text(en="Since 2020, a higher floor",
                          pt="Desde 2020, outro patamar"),
                 ctx.text(
                    en="Until 2019 no line went above {pre_max} of GDP; "
                       "since 2020 none has gone below {post_min}. It is a "
                       "share of GDP: it can rise on bigger trade or on a "
                       "smaller GDP.",
                    pt="Até 2019 nenhuma linha passou de {pre_max} do PIB; "
                       "desde 2020 nenhuma desce de {post_min}. É fatia do "
                       "PIB: sobe com comércio maior ou com PIB menor.")),
                (ctx.text(en="Both records fall in the same year",
                          pt="Os dois recordes no mesmo ano"),
                 ctx.text(
                    en="Exports ({x22}) and imports ({m22}) hit their "
                       "highest in {hi_year}. Even then, neither side "
                       "reached a fifth of GDP.",
                    pt="Exportações ({x22}) e importações ({m22}) chegam ao "
                       "máximo em {hi_year}. Mesmo aí, nenhuma das duas chega a "
                       "um quinto do PIB.")),
                (ctx.text(en="{next_year}: imports fell over twice as much",
                          pt="{next_year}: importações caem mais que o dobro"),
                 ctx.text(
                    en="From {hi_year} to {next_year} imports lost {dm} "
                       "points of GDP and exports {dx}. That gap is what "
                       "draws the tall bar of {next_year} in the next panel.",
                    pt="De {hi_year} a {next_year} as importações perdem {dm} "
                       "pontos do PIB e as exportações {dx}. Essa "
                       "diferença desenha a barra alta de {next_year} no "
                       "painel ao lado.")),
            ],
            facts={"hi": val(hi, "pct", year=hi_y),
                   "pre_max": val(pre_max, "pct", year=2019),
                   "post_min": val(post_min, "pct"),
                   "x22": val(xs[hi_y], "pct", year=hi_y),
                   "m22": val(ms[hi_y], "pct", year=hi_y),
                   "dm": val(dm, "dec1"), "dx": val(dx, "dec1"),
                   "next": at(y_next)}),
        "trade.balance": ctx.story(
            title=ctx.text(
                en="The balance always stayed within ±{bound} of GDP",
                pt="O saldo ficou sempre dentro de ±{bound} do PIB"),
            beats=[
                (ctx.text(en="Later green bars add up to half the red",
                          pt="Verde recente soma metade do vermelho"),
                 ctx.text(
                    en="Adding the bars: {run_start_year}–{run_end_year} "
                       "gives {red_sum} points of GDP; "
                       "{late_year}–{last_year} gives {green_sum}, of which "
                       "{b23} is {peak_year} alone.",
                    pt="Somando as barras, {run_start_year}–{run_end_year} "
                       "dá {red_sum} pontos do PIB; "
                       "{late_year}–{last_year} dá {green_sum}, dos quais "
                       "{b23} são só de {peak_year}.")),
                (ctx.text(en="Eight years down, two years back",
                          pt="Oito anos para baixo, dois para voltar"),
                 ctx.text(
                    en="From {best_year} ({best}) to {worst_year} ({worst}) "
                       "took {down} years. From {worst_year} to "
                       "{b16_year}, {up} years were enough to be green "
                       "again ({b16}).",
                    pt="De {best_year} ({best}) a {worst_year} ({worst}) "
                       "passaram-se {down} anos. De {worst_year} a "
                       "{b16_year}, bastaram {up} para voltar ao verde "
                       "({b16}).")),
                (ctx.text(en="A surplus in goods, a bar near zero",
                          pt="Superávit em bens, barra quase zero"),
                 ctx.text(
                    en="In {last_year} goods alone sold US${gb} bn more "
                       "than they bought; with services, {b25}. The note "
                       "says the services deficit takes back most of it.",
                    pt="Em {last_year} só os bens venderam US$ {gb} bi a "
                       "mais do que compraram; com serviços, {b25}. A nota "
                       "diz que o déficit de serviços leva quase tudo de "
                       "volta.")),
            ],
            facts={"bound": val(bound, "pct"),
                   "run_start": at(run_start), "run_end": at(run_end),
                   "late": at(run_end + 1), "last": at(full),
                   "red_sum": val(red_sum, "dec1"),
                   "green_sum": val(green_sum, "dec1"),
                   "b23": val(bal[y_next], "dec1", year=y_next),
                   "peak": at(y_next),
                   "best": val(bal[best], "pct_gdp_s", year=best),
                   "worst": val(bal[worst], "pct_gdp_s", year=worst),
                   "down": val(worst - best, "count"),
                   "up": val(2, "count"),
                   "b16": val(bal[worst + 2], "pct_gdp_s", year=worst + 2),
                   "gb": val(gb[full], "count"),
                   "b25": val(bal[full], "pct_gdp_s")}),
        "trade.destinations": ctx.story(
            title=ctx.text(
                en="Among the four destinations, China went from last to "
                   "first",
                pt="Entre os quatro destinos, a China foi de última a "
                   "primeira"),
            beats=[
                (ctx.text(en="China tops the US and EU combined",
                          pt="China supera EUA e UE somados"),
                 ctx.text(
                    en="In {y20_year} China took {cn20} of goods exports, "
                       "against {ue20} for the US and the EU added "
                       "together. In {last_year}: {cn25} against {ue25}.",
                    pt="Em {y20_year} a China ficou com {cn20} das "
                       "exportações de bens, contra {ue20} de EUA e UE "
                       "somados. Em {last_year}: {cn25} contra {ue25}.")),
                (ctx.text(en="The overtaking fell between {first_year} and "
                             "{y15_year}",
                          pt="A ultrapassagem ocorreu entre {first_year} e "
                             "{y15_year}"),
                 ctx.text(
                    en="China was below the other three in {first_year} "
                       "({cn06}) and above all of them in {y15_year} "
                       "({cn15}). Lines join reference years only, so they "
                       "do not say which year.",
                    pt="A China estava abaixo das outras três em "
                       "{first_year} ({cn06}) e acima de todas em {y15_year} "
                       "({cn15}). As linhas ligam só anos de referência: não "
                       "dizem em que ano.")),
                (ctx.text(en="A smaller share is not smaller sales",
                          pt="Fatia menor não é venda menor"),
                 ctx.text(
                    en="The US, EU and Argentina end {last_year} with a "
                       "smaller share than in {first_year}. But goods "
                       "exports went from US${gx06} bn to US${gx25} bn.",
                    pt="EUA, UE e Argentina terminam {last_year} com fatia "
                       "menor que em {first_year}. Mas as exportações de "
                       "bens foram de US$ {gx06} bi para US$ {gx25} bi.")),
                (ctx.text(en="A 2020 peak, then a plateau",
                          pt="Pico em 2020, depois um platô"),
                 ctx.text(
                    en="China reached {cn20} in 2020, in the COVID-19 band, "
                       "then {cn24} in {y24_year} and {cn25} in "
                       "{last_year}. {partial_year} (Jan–Sep, dashed): "
                       "{cn_part}.",
                    pt="A China chegou a {cn20} em 2020, na faixa da "
                       "COVID-19, depois {cn24} em {y24_year} e {cn25} em "
                       "{last_year}. {partial_year} (jan.–set., tracejado): "
                       "{cn_part}.")),
            ],
            facts={"y20": at(y20), "y15": at(y15), "y24": at(y24),
                   "first": at(first), "last": at(full),
                   "partial": at(partial),
                   "cn20": val(cn[y20], "pct", year=y20),
                   "ue20": val(us[y20] + eu[y20], "pct", year=y20),
                   "cn25": val(cn[full], "pct"),
                   "ue25": val(us[full] + eu[full], "pct"),
                   "cn06": val(cn[first], "pct", year=first),
                   "cn15": val(cn[y15], "pct", year=y15),
                   "cn24": val(cn[y24], "pct", year=y24),
                   "cn_part": val(cn[partial], "pct", year=partial),
                   "gx06": val(gx[first], "count", year=first),
                   "gx25": val(gx[full], "count")}),
        "trade.lens": ctx.story(
            title=ctx.text(
                en="Oil and soy are already {s25} of the goods Brazil sells",
                pt="Petróleo e soja já são {s25} dos bens que o Brasil "
                   "vende"),
            beats=[
                (ctx.text(en="The pair more than doubled its share",
                          pt="A dupla mais que dobrou sua fatia"),
                 ctx.text(
                    en="Oil plus soy was {s06} of goods exports in {y06_year} "
                       "and {s25} in {last_year}. In {last_year} the two "
                       "bars nearly tie: US${oil} bn and US${soy} bn.",
                    pt="Petróleo mais soja eram {s06} das exportações de "
                       "bens em {y06_year} e são {s25} em {last_year}. Em "
                       "{last_year} as duas barras quase empatam: US$ {oil} "
                       "bi e US$ {soy} bi.")),
                (ctx.text(en="Five snapshots, three leaders",
                          pt="Cinco fotos, três líderes"),
                 ctx.text(
                    en="Oil, iron, soy, soy, oil: the leader changes. From "
                       "{y10_year} to {y15_year} iron fell from US${iron10} "
                       "bn to US${iron15} bn, and soy moved ahead.",
                    pt="Petróleo, minério, soja, soja, petróleo: o líder "
                       "muda. De {y10_year} a {y15_year} o minério foi de "
                       "US$ {iron10} bi a US$ {iron15} bi, e a soja passou "
                       "à frente.")),
                (ctx.text(en="{others_pct} of sales is not in the chart",
                          pt="{others_pct} das vendas nem aparece"),
                 ctx.text(
                    en="The 'others' residual, left out of the chart, was "
                       "US${others} bn in {last_year}: bigger than any "
                       "single bar. The 11 groups do not cover the rest.",
                    pt="O resíduo 'outros', fora do gráfico, somou US$ "
                       "{others} bi em {last_year}: mais que qualquer barra. "
                       "Os 11 grupos não cobrem o resto.")),
                (ctx.text(en="Steel, cars and planes barely move",
                          pt="Aço, carros e aviões quase parados"),
                 ctx.text(
                    en="In every snapshot the three stay at US${small_hi} "
                       "bn or less, while oil went from US${oil06} bn in {y06_year} to "
                       "US${oil} bn in {last_year}.",
                    pt="Em todas as fotos os três ficam em até US$ "
                       "{small_hi} bi, enquanto o petróleo foi de US$ "
                       "{oil06} bi em {y06_year} a US$ {oil} bi em {last_year}.")),
            ],
            facts={"s06": val(s06, "pct", year=y06),
                   "s25": val(s25, "pct"),
                   "y06": at(y06), "y10": at(y10), "y15": at(y15p),
                   "last": at(full),
                   "oil": val(g(full, "oil"), "dec1"),
                   "soy": val(g(full, "soy"), "dec1"),
                   "oil06": val(g(y06, "oil"), "dec1", year=y06),
                   "iron10": val(g(y10, "iron"), "dec1", year=y10),
                   "iron15": val(g(y15p, "iron"), "dec1", year=y15p),
                   "others": val(others, "count"),
                   "others_pct": val(others_pct, "pct"),
                   "small_hi": val(max(small), "dec1")}),
    }


def markets_stories(ctx) -> dict:
    """Insights for the markets plate (policy rate, 10-year bond, the real,
    equities). Every number is read from the plate's CSVs at build time."""
    full = ctx.LAST_FULL_YEAR
    join = {"pt": " e ", "en": " and "}

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def years(ys):
        ys = [str(y) for y in ys]
        return {"year": None, "value": {
            loc: ", ".join(ys[:-1]) + join.get(loc, ", ") + ys[-1]
            if len(ys) > 1 else ys[0] for loc in ctx.locales}}

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil markets stories: {why}; rewrite the "
                             f"copy that depends on it")

    def in_band(y):
        return any(lo <= y <= hi for lo, hi, _ in ctx.c.recessions)

    selic = dict(ctx.col("macro/selic.csv", "value"))
    ipca = dict(ctx.col("macro/ipca.csv", "value"))
    avg = dict(ctx.col("macro/dollar.csv", "avg"))
    eop = dict(ctx.col("macro/dollar.csv", "eop"))
    ibov = dict(ctx.col("markets/ibov.csv", "close"))
    sp = dict(ctx.col("markets/sp500.csv", "close"))
    bond = dict(ctx.col("markets/bond_10y.csv", "yield_10y"))

    first = ctx.c.years[0]
    partial = ctx.c.years[-1]
    at = lambda y: val(0, "count", year=y)
    span = list(range(first, full + 1))

    # ---- policy rate vs inflation
    need(all(y in selic and y in ipca for y in span), "a Selic/IPCA year is missing")
    need(partial in selic, "no running-year Selic")
    above = [y for y in span if selic[y] > ipca[y]]
    below = [y for y in span if selic[y] <= ipca[y]]
    need(below == [2020, 2021], "the years with the Selic under IPCA are "
         "no longer exactly 2020 and 2021")
    gap = {y: selic[y] - ipca[y] for y in span}
    g_rank = sorted(span, key=gap.get, reverse=True)
    need(g_rank[0] == full, "the widest Selic-IPCA gap is no longer the "
         "latest full year")
    g2 = g_rank[1]
    step = {y: selic[y] - selic[y - 1] for y in span[1:]}
    by_move = sorted(step, key=lambda y: abs(step[y]), reverse=True)
    up_y, fall_y = max(step, key=step.get), min(step, key=step.get)
    need(set(by_move[:2]) == {up_y, fall_y} and step[up_y] > 0 > step[fall_y]
         and abs(step[by_move[2]]) < min(abs(step[up_y]), abs(step[fall_y])),
         "the two biggest one-year Selic moves are no longer one rise and "
         "one fall that stand clear of the rest")
    need(up_y == 2021 and selic[up_y] <= ipca[up_y],
         "the biggest Selic rise is no longer 2021, still under that "
         "year's IPCA")

    # ---- 10-year bond
    b_years = sorted(y for y in bond if y <= full)
    both = [y for y in b_years if y in ipca]
    bgap = {y: bond[y] - ipca[y] for y in both}
    neg = [y for y in both if bgap[y] <= 0]
    need(neg == [2021], "the years with the bond under IPCA are no longer "
         "exactly 2021")
    gaps = [y for y in range(first, max(bond)) if y not in bond]
    need(gaps == [2006, 2009] or (2009 in gaps and 2008 in bond
                                  and 2010 in bond), "the bond hole at 2009 "
         "is gone")
    need(2006 not in bond or 2006 in gaps, "unexpected 2006 bond point")
    gb = sorted(both, key=bgap.get, reverse=True)
    need(gb[0] == full, "the widest bond-IPCA gap is no longer the latest "
         "full year")
    low = min(b_years, key=bond.get)
    need(low == 2020 and 2020 in selic, "the bond low is no longer 2020")
    need(all(y in selic for y in b_years), "a Selic year for the bond is "
         "missing")
    sgap = {y: bond[y] - selic[y] for y in b_years}
    need(max(sgap, key=sgap.get) == low, "the widest bond-Selic distance is "
         "no longer the bond's low year")
    n_over = len(both) - len(neg)
    min_over = min(bgap[y] for y in both if y not in neg)

    # ---- the real: annual-average PTAX as an index, 2006 = 100
    base = avg[first]
    idx = {y: base / avg[y] * 100 for y in span}
    peak = max(span, key=idx.get)
    steep = min(span[1:], key=lambda y: idx[y] / idx[y - 1])
    need(peak == 2011, "the real's strongest year is no longer 2011")
    need(steep == 2015 and in_band(steep),
         "the steepest one-year fall is no longer 2015 inside the band")
    flat = [idx[y] for y in span if y >= 2020]
    need(max(flat) - min(flat) < 6 and min(flat) == min(idx.values())
         and max(flat) < idx[2014], "the real is no longer flat from 2020 "
         "at its lows")
    lost = 1 - idx[2020] / idx[peak]

    # ---- equities
    ib_usd = {y: ibov[y] / eop[y] for y in span}
    ib_i = {y: ib_usd[y] / ib_usd[first] * 100 for y in span}
    sp_i = {y: sp[y] / sp[first] * 100 for y in span}
    e_peak = max(span, key=ib_i.get)
    since = min(y for y in span
                if all(sp_i[z] > ib_i[z] for z in span if z >= y))
    need(since > first and sp_i[since - 1] <= ib_i[since - 1] and
         since <= full - 3, "the S&P 500 is not above the Ibovespa from a "
         "single year on")
    x_brl = ibov[full] / ibov[first]
    x_usd = ib_usd[full] / ib_usd[first]
    x_fx = eop[full] / eop[first]
    need(abs(x_brl / x_usd - x_fx) < 1e-9, "reais/dollars gap is no longer "
         "the year-end exchange rate")
    need(ib_i[full] < ib_i[e_peak] and partial in ibov and partial in eop,
         "the Ibovespa in dollars is no longer under its peak")
    ib26 = ibov[partial] / eop[partial] / ib_usd[first] * 100
    ch = {y: ib_i[y] / ib_i[y - 1] - 1 for y in span[1:]}
    need(min(ch, key=ch.get) == 2008 and max(ch, key=ch.get) == 2009
         and not in_band(2008) and not in_band(2009),
         "the Ibovespa's biggest fall and rise are no longer 2008 and 2009 "
         "outside the bands")
    need(sp_i[2008] < sp_i[2007], "the S&P 500 did not fall in 2008")

    return {
        "markets.policy_rate": ctx.story(
            title=ctx.text(
                en="The Selic sat above inflation in {n_above} of {n} years",
                pt="A Selic ficou acima da inflação em {n_above} de {n} anos"),
            beats=[
                (ctx.text(en="{full_year} has the widest gap",
                          pt="Em {full_year}, a folga foi a maior"),
                 ctx.text(
                    en="The Selic ({selic_f}) ended {gap_f} percentage points "
                       "above IPCA ({ipca_f}), the widest distance in the "
                       "series. Next comes {gap2_year}: {gap2}.",
                    pt="A Selic ({selic_f}) ficou {gap_f} pontos percentuais "
                       "acima do IPCA ({ipca_f}), a maior distância da série. "
                       "A segunda maior é a de {gap2_year}: {gap2}.")),
                (ctx.text(en="Only {below} flipped the order",
                          pt="Só {below} inverteram a ordem"),
                 ctx.text(
                    en="In {s20_year}: Selic {s20} against IPCA {i20}. In "
                       "{s21_year}: {s21} against {i21}. The Selic is the "
                       "year-end target; IPCA is the whole year.",
                    pt="Em {s20_year}: Selic de {s20} contra IPCA de {i20}. "
                       "Em {s21_year}: {s21} contra {i21}. A Selic é a meta "
                       "de fim de ano; o IPCA, o ano inteiro.")),
                (ctx.text(en="The two biggest jumps: {fall_year} and {up_year}",
                          pt="Os dois maiores saltos: {fall_year} e {up_year}"),
                 ctx.text(
                    en="In {fall_year} the Selic fell {fall} points in one "
                       "year ({sf0} to {sf1}); in {up_year} it rose {up} "
                       "({su0} to {su1}). No other year moves as much.",
                    pt="Em {fall_year} a Selic recuou {fall} pontos em um ano "
                       "({sf0} a {sf1}); em {up_year} subiu {up} ({su0} a "
                       "{su1}). Nenhum outro ano mexe tanto.")),
            ],
            facts={"n": val(len(span), "count"),
                   "n_above": val(len(above), "count"),
                   "full": at(full),
                   "selic_f": val(selic[full], "pct2"),
                   "ipca_f": val(ipca[full], "pct2"),
                   "gap_f": val(gap[full], "dec1"),
                   "gap2": val(gap[g2], "dec1", year=g2),
                   "below": years(below),
                   "s20": val(selic[2020], "pct2", year=2020),
                   "i20": val(ipca[2020], "pct2", year=2020),
                   "s21": val(selic[2021], "pct2", year=2021),
                   "i21": val(ipca[2021], "pct2", year=2021),
                   "fall": val(abs(step[fall_y]), "dec2", year=fall_y),
                   "up": val(step[up_y], "dec2", year=up_y),
                   "sf0": val(selic[fall_y - 1], "pct2", year=fall_y - 1),
                   "sf1": val(selic[fall_y], "pct2", year=fall_y),
                   "su0": val(selic[up_y - 1], "pct2", year=up_y - 1),
                   "su1": val(selic[up_y], "pct2", year=up_y)}),
        "markets.bond_10y": ctx.story(
            title=ctx.text(
                en="The 10-year yield beat IPCA in {n_over} of {n_b} years",
                pt="O juro de 10 anos superou o IPCA em {n_over} de {n_b} "
                   "anos"),
            beats=[
                (ctx.text(en="Only {neg_year} fell below inflation",
                          pt="Só {neg_year} ficou abaixo da inflação"),
                 ctx.text(
                    en="In {neg_year} the bond yielded {b21}, under IPCA of "
                       "{i21}. In every other year with a point, the yield "
                       "was at least {min_over} points above.",
                    pt="Em {neg_year} o título rendeu {b21}, abaixo do IPCA "
                       "de {i21}. Em todos os outros anos com ponto, a taxa "
                       "ficou ao menos {min_over} pontos acima.")),
                (ctx.text(en="{full_year}: the widest cushion yet",
                          pt="Em {full_year}, a maior sobra da série"),
                 ctx.text(
                    en="The yield ({b_f}) sat {gap_b} points above IPCA "
                       "({ipca_f}), the widest among full years; the "
                       "previous record was {prev_year}: {prev_gap}.",
                    pt="A taxa ({b_f}) ficou {gap_b} pontos acima do IPCA "
                       "({ipca_f}), a maior entre anos completos; o recorde "
                       "anterior era o de {prev_year}: {prev_gap}.")),
                (ctx.text(en="Selic at {s20}, bond at {low}",
                          pt="Selic a {s20}, título a {low}"),
                 ctx.text(
                    en="In {low_year} the bond averaged {low} while the "
                       "Selic closed the year at {s20}: the widest distance "
                       "between them, {gap_s} points.",
                    pt="Em {low_year} o título teve média de {low} e a Selic "
                       "fechou o ano em {s20}: a maior distância entre os "
                       "dois, {gap_s} pontos.")),
                (ctx.text(en="What happened in {g09_year} is not drawn",
                          pt="O que houve em {g09_year} não aparece"),
                 ctx.text(
                    en="No bond near ten years in {gaps}, so the line is "
                       "not drawn across them. From {b08_year} to {b10_year} "
                       "it goes {b08} to {b10}; the path in between is "
                       "unknown.",
                    pt="Sem título perto de dez anos em {gaps}, a linha não "
                       "os cruza. De {b08_year} a {b10_year} ela vai de "
                       "{b08} a {b10}; o caminho no meio é desconhecido.")),
            ],
            facts={"n_over": val(n_over, "count"),
                   "n_b": val(len(both), "count"),
                   "neg": at(2021),
                   "b21": val(bond[2021], "pct2", year=2021),
                   "i21": val(ipca[2021], "pct2", year=2021),
                   "min_over": val(min_over, "dec1"),
                   "full": at(full),
                   "b_f": val(bond[full], "pct2"),
                   "ipca_f": val(ipca[full], "pct2"),
                   "gap_b": val(bgap[full], "dec1"),
                   "prev": at(gb[1]),
                   "prev_gap": val(bgap[gb[1]], "dec1", year=gb[1]),
                   "low": val(bond[low], "pct2", year=low),
                   "s20": val(selic[low], "pct2", year=low),
                   "gap_s": val(sgap[low], "dec1", year=low),
                   "g09": at(2009), "gaps": years(gaps),
                   "b08": val(bond[2008], "pct2", year=2008),
                   "b10": val(bond[2010], "pct2", year=2010)}),
        "markets.currency": ctx.story(
            title=ctx.text(
                en="The real fell until 2020 and has moved sideways since",
                pt="O real caiu até 2020 e desde então anda de lado"),
            beats=[
                (ctx.text(en="{peak_year} to {y20_year}: down {lost}",
                          pt="De {peak_year} a {y20_year}, perdeu {lost}"),
                 ctx.text(
                    en="The index went from {peak} at the {peak_year} high "
                       "to {i20} in {y20_year}: each real came to buy {lost} "
                       "fewer dollars.",
                    pt="O índice foi de {peak} no pico de {peak_year} a "
                       "{i20} em {y20_year}: cada real passou a comprar "
                       "{lost} menos dólares.")),
                (ctx.text(en="{y20_year} to {full_year}: sideways",
                          pt="De {y20_year} a {full_year}, de lado"),
                 ctx.text(
                    en="Across the full years from {y20_year} to "
                       "{full_year} the index stayed between {lo} and {hi}: "
                       "the fall stopped, with no recovery.",
                    pt="Nos anos completos de {y20_year} a {full_year} o "
                       "índice ficou entre {lo} e {hi}: a queda parou, sem "
                       "recuperação.")),
                (ctx.text(en="The dollar costs {mult}× more reais",
                          pt="O dólar custa {mult}× mais reais"),
                 ctx.text(
                    en="From {usd0} in {first_year} to {usd1} in "
                       "{full_year}, annual averages. The line measures the "
                       "real against the dollar only: not prices at home, "
                       "not other currencies.",
                    pt="De {usd0} em {first_year} a {usd1} em {full_year}, "
                       "em médias anuais. A linha mede só o real contra o "
                       "dólar: não mede preços no país nem outras moedas.")),
                (ctx.text(en="{steep_year}: the sharpest one-year fall",
                          pt="{steep_year}: a maior queda em um ano"),
                 ctx.text(
                    en="From {prev_year} to {steep_year}, inside the "
                       "2014–16 band, the index fell {drop} ({i_prev} to "
                       "{i_steep}). No other year falls as much.",
                    pt="De {prev_year} a {steep_year}, dentro da faixa "
                       "2014–16, o índice caiu {drop} ({i_prev} a "
                       "{i_steep}). Nenhum outro ano cai tanto.")),
            ],
            facts={"peak": val(idx[peak], "index", year=peak),
                   "i20": val(idx[2020], "index", year=2020),
                   "y20": at(2020), "full": at(full),
                   "lost": val(lost * 100, "pct", year=2020),
                   "lo": val(min(flat), "index"),
                   "hi": val(max(flat), "index"),
                   "mult": val(avg[full] / avg[first], "dec1"),
                   "first": at(first),
                   "usd0": val(avg[first], "money2", year=first),
                   "usd1": val(avg[full], "money2"),
                   "steep": at(steep), "prev": at(steep - 1),
                   "drop": val((1 - idx[steep] / idx[steep - 1]) * 100,
                               "pct", year=steep),
                   "i_prev": val(idx[steep - 1], "index", year=steep - 1),
                   "i_steep": val(idx[steep], "index", year=steep)}),
        "markets.equities": ctx.story(
            title=ctx.text(
                en="In dollars, the S&P 500 has led the Ibovespa since "
                   "{since_year}",
                pt="Em dólares, o S&P 500 lidera o Ibovespa desde "
                   "{since_year}"),
            beats=[
                (ctx.text(en="The exchange rate is the whole gap",
                          pt="O câmbio explica toda a diferença"),
                 ctx.text(
                    en="The Ibovespa grew {x_brl}× in reais and {x_usd}× in "
                       "dollars. Their ratio, {x_fx}, is exactly how much "
                       "the year-end dollar rose: {d0} to {d1}.",
                    pt="O Ibovespa cresceu {x_brl}× em reais e {x_usd}× em "
                       "dólares. A razão entre os dois, {x_fx}, é a alta do "
                       "dólar no fim do ano: de {d0} a {d1}.")),
                (ctx.text(en="In {full_year}, below the {e_peak_year} peak",
                          pt="Em {full_year}, abaixo do pico de {e_peak_year}"),
                 ctx.text(
                    en="The Ibovespa in dollars ended {full_year} at "
                       "{ib_f}; the high was {e_peak} in {e_peak_year}. "
                       "Dashed {partial_year} (to Oct 20) reaches {ib26}.",
                    pt="O Ibovespa em dólares fechou {full_year} em {ib_f}; "
                       "o pico foi {e_peak} em {e_peak_year}. O tracejado de "
                       "{partial_year} (até 20 out.) chega a {ib26}.")),
                (ctx.text(en="{r_sp}× apart at the end",
                          pt="{r_sp}× de distância no fim"),
                 ctx.text(
                    en="The S&P 500 stands at {sp_f}, the Ibovespa in "
                       "dollars at {ib_f} ({first_year} = 100). In "
                       "{pre_year} the Ibovespa still led; in {since_year}, "
                       "no longer.",
                    pt="O S&P 500 está em {sp_f}; o Ibovespa em dólares, em "
                       "{ib_f} ({first_year} = 100). Em {pre_year} o "
                       "Ibovespa ainda liderava; em {since_year}, já não.")),
                (ctx.text(en="The biggest swings sit outside the bands",
                          pt="Os maiores vaivéns estão fora das faixas"),
                 ctx.text(
                    en="The Ibovespa in dollars went {i07} ({i07_year}), "
                       "{i08} ({i08_year}), {i09} ({i09_year}): its biggest "
                       "yearly moves. The S&P 500 also fell in {i08_year}, "
                       "to {s08}.",
                    pt="O Ibovespa em dólares foi de {i07} ({i07_year}) a "
                       "{i08} ({i08_year}) e a {i09} ({i09_year}): suas "
                       "maiores variações. O S&P 500 também caiu em "
                       "{i08_year}, a {s08}.")),
            ],
            facts={"since": at(since), "pre": at(since - 1),
                   "full": at(full), "partial": at(partial),
                   "first": at(first),
                   "x_brl": val(x_brl, "dec1"), "x_usd": val(x_usd, "dec1"),
                   "x_fx": val(x_fx, "dec1"),
                   "d0": val(eop[first], "money2", year=first),
                   "d1": val(eop[full], "money2"),
                   "ib_f": val(ib_i[full], "index"),
                   "e_peak": val(ib_i[e_peak], "index", year=e_peak),
                   "ib26": val(ib26, "index", year=partial),
                   "sp_f": val(sp_i[full], "index"),
                   "r_sp": val(sp_i[full] / ib_i[full], "dec1"),
                   "i07": val(ib_i[2007], "index", year=2007),
                   "i08": val(ib_i[2008], "index", year=2008),
                   "i09": val(ib_i[2009], "index", year=2009),
                   "s08": val(sp_i[2008], "index", year=2008)}),
    }


def credit_stories(ctx) -> dict:
    """Insights for the four panels of the credit plate (Brasil).

    Every number is a fact read from the CSVs at build time; the only years
    written into a sentence are the ones the plate itself marks. `need`
    stops the build when a sentence stops being true.
    """
    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil credit stories: {why}; rewrite the "
                             f"copy that depends on it")

    bis = dict(ctx.col("macro/household_credit.csv", "hh_credit_pct_gdp_q4"))
    allc = dict(ctx.col("macro/credit.csv", "credit_gdp"))
    pf = dict(ctx.col("macro/credit.csv", "rate_pf"))
    selic = dict(ctx.col("macro/selic.csv", "value"))
    npl_pf = dict(ctx.col("macro/credit.csv", "npl_pf"))
    npl = dict(ctx.col("macro/credit.csv", "npl_total"))
    di = dict(ctx.col("macro/household_debt.csv", "debt_income"))
    dx = dict(ctx.col("macro/household_debt.csv", "debt_income_ex_housing"))
    ds = dict(ctx.col("macro/household_debt.csv", "debt_service"))

    first = ctx.c.years[0]
    partial = ctx.c.years[-1]
    at = lambda y: val(0, "count", year=y)

    # ---- household debt, % of GDP
    span = [y for y in sorted(bis) if first <= y <= full]
    drops = [y for y in span[1:] if bis[y] < bis[y - 1]]
    need(span[0] == first and bis[full] > 2 * bis[first],
         "household debt no longer more than doubles over the span")
    need(len(drops) == 1, "household debt did not fall exactly once")
    drop = drops[0]
    pause = (2015, 2016, 2017, 2018)
    need(max(bis[y] for y in pause) - min(bis[y] for y in pause) < 1.0,
         "household debt is no longer nearly flat in 2015-2018")
    need(drop in pause, "the one fall is no longer inside the 2015-2018 pause")
    need(bis[2014] - bis[first] > 3 * (bis[2018] - bis[2014])
         and bis[full] > bis[2018],
         "the pre-2014 climb is no longer much steeper than 2014-2018")
    need(partial not in bis, "the running year now has a Q4 BIS point")
    need(allc[full] > bis[full], "all bank credit is not above household debt")
    p_lo, p_hi = min(pause, key=bis.get), max(pause, key=bis.get)
    pace = (bis[2014] - bis[first]) / (2014 - first)

    # ---- lending rate vs the policy rate
    ry = [y for y in sorted(pf) if y <= full]
    start = min(pf)
    gap = {y: pf[y] - selic[y] for y in ry}
    g_lo, g_hi = min(gap, key=gap.get), max(gap, key=gap.get)
    sy = [y for y in ry]
    s_low = min(sy, key=selic.get)
    s_high = max(sy, key=selic.get)
    need(gap[g_lo] > 15, "the household rate is no longer 15+ points above the Selic")
    need(s_low == 2020 and pf[2020] == min(pf[y] for y in ry),
         "the lows of both rates are no longer in 2020")
    need(pf[2016] == max(pf[y] for y in ry) and selic[2016] < selic[2015],
         "the household-rate peak is no longer 2016")
    need(selic[2016] > selic[2020] > 0 and pf[2016] > pf[2020],
         "both rates no longer fall between 2016 and 2020")
    need((selic[2016] - selic[2020]) / selic[2016]
         > (pf[2016] - pf[2020]) / pf[2016],
         "the Selic no longer falls proportionally more than the household rate")
    need(pf[s_low] / selic[s_low] > 2 * pf[full] / selic[full],
         "the rate-to-Selic multiple at the low is no longer well above today's")
    need(pf[min(ry, key=pf.get)] > selic[s_high],
         "the lowest household rate no longer sits above the highest Selic")

    # ---- arrears
    ny = [y for y in sorted(npl_pf) if y <= full]
    need(min(npl_pf) == start, "arrears no longer start with the household rate")
    n_low = min(ny, key=npl_pf.get)
    need(n_low == 2020, "the arrears low is no longer 2020")
    need(all(npl_pf[y] > npl[y] for y in npl_pf if y in npl),
         "household arrears are not above all-borrower arrears every year")
    need(abs(npl_pf[full] - npl_pf[start]) < 0.3,
         "household arrears are no longer close to where the series starts")
    need(partial in npl_pf and npl_pf[partial] > max(npl_pf[y] for y in ny),
         "the running year is no longer the arrears peak")
    ngap = {y: npl_pf[y] - npl[y] for y in ny}
    n_gmin = min(ngap, key=ngap.get)
    need(ngap[n_gmin] < ngap[start] / 3,
         "the household-vs-all gap no longer shrinks to a third")

    # ---- the lens
    ly = [y for y in sorted(di) if first <= y <= full]
    need(all(dx[y] < di[y] for y in ly), "debt ex housing is not below the total")
    need(di[full] > 2 * di[first], "debt is no longer more than double its start")
    need(1 < ds[full] / ds[first] < di[full] / di[first],
         "debt service no longer rises by a smaller multiple than debt")
    rise = {y: di[y] - di[y - 1] for y in ly[1:]}
    big = max(rise, key=rise.get)
    need(big == 2021, "the biggest yearly step in debt is no longer 2021")
    others = [rise[y] for y in rise if y != big]
    need(rise[big] > 3 * (sum(others) / len(others)),
         "the biggest step is no longer far above the average one")
    after = [di[y] for y in ly if y >= big]
    h = {y: di[y] - dx[y] for y in ly}
    h_share = (h[full] - h[first]) / (di[full] - di[first])
    need(h_share > 0.5, "housing is no longer over half of the rise in debt")
    need(max(after) - min(after) < 3, "debt is no longer steady after the jump")
    a_lo, a_hi = min(after), max(after)


    return {
        "credit.household_debt": ctx.story(
            title=ctx.text(
                en="Household debt went from {d_first} to {d_last} of GDP",
                pt="A dívida das famílias foi de {d_first} a {d_last} do PIB"),
            beats=[
                (ctx.text(en="More than doubled, with one tiny dip",
                          pt="Mais que dobrou, com um recuo mínimo"),
                 ctx.text(
                    en="From {first_year} to {last_year} it grew {ratio} times. "
                       "Of {span} yearly steps, only {drop_year} went down, "
                       "by {drop_pts} percentage point.",
                    pt="De {first_year} a {last_year} cresceu {ratio} vezes. "
                       "De {span} passos anuais, só {drop_year} recuou, em "
                       "{drop_pts} ponto percentual.")),
                (ctx.text(en="A pause, then the climb resumes",
                          pt="Uma pausa, e a subida recomeça"),
                 ctx.text(
                    en="Until {pre_year} it rose {pace} points a year on "
                       "average. From {p_from_year} to {p_to_year} it stayed "
                       "between {p_lo} and {p_hi}, then climbed again.",
                    pt="Até {pre_year} subia {pace} pontos por ano, em média. "
                       "De {p_from_year} a {p_to_year} ficou entre {p_lo} e "
                       "{p_hi}, e depois voltou a subir.")),
                (ctx.text(en="Against GDP, not against income",
                          pt="Contra o PIB, não contra a renda"),
                 ctx.text(
                    en="GDP is what the country produces, not what families "
                       "earn. The last panel measures debt against their "
                       "income, per the central bank: {inc} in {last_year}.",
                    pt="PIB é o que o país produz, não o que as famílias "
                       "ganham. O último painel mede a dívida contra a renda "
                       "delas, pelo Banco Central: {inc} em {last_year}.")),
                (ctx.text(en="Firms are outside this line",
                          pt="As empresas ficam fora desta linha"),
                 ctx.text(
                    en="All bank credit, firms included, is {all_last} of "
                       "GDP in {last_year}. It is a different measure: it is "
                       "not a sum with, or a share of, the line.",
                    pt="Todo o crédito bancário, com empresas, é {all_last} "
                       "do PIB em {last_year}. É outra medida: não se soma à "
                       "linha nem é uma fatia dela.")),
            ],
            facts={"d_first": val(bis[first], "pct", year=first),
                   "d_last": val(bis[full], "pct"),
                   "first": at(first), "last": at(full),
                   "ratio": val(bis[full] / bis[first], "dec1"),
                   "span": val(len(span) - 1, "count"),
                   "drop": at(drop),
                   "drop_pts": val(bis[drop - 1] - bis[drop], "dec1", year=drop),
                   "pre": at(2014),
                   "pace": val(pace, "dec1", year=2014),
                   "p_from": at(pause[0]), "p_to": at(pause[-1]),
                   "p_lo": val(bis[p_lo], "pct", year=p_lo),
                   "p_hi": val(bis[p_hi], "pct", year=p_hi),
                   "inc": val(di[full], "pct"),
                   "all_last": val(allc[full], "pct")}),
        "credit.lending_rate": ctx.story(
            title=ctx.text(
                en="Household loan rates: at least {gap_min} points above "
                   "the Selic",
                pt="Juro às famílias: ao menos {gap_min} pontos acima da "
                   "Selic"),
            beats=[
                (ctx.text(en="The gap barely depends on the Selic",
                          pt="A distância pouco depende da Selic"),
                 ctx.text(
                    en="From {start_year} to {last_year} the gap stays between "
                       "{gap_min} ({gap_min_year}) and {gap_max} ({gap_max_year}) "
                       "points, while the Selic ranges from {selic_low} to "
                       "{selic_high}.",
                    pt="De {start_year} a {last_year} a distância fica entre "
                       "{gap_min} ({gap_min_year}) e {gap_max} ({gap_max_year}) "
                       "pontos, enquanto a Selic vai de {selic_low} a "
                       "{selic_high}.")),
                (ctx.text(en="Selic fell {s_drop}; the loan rate, {p_drop}",
                          pt="A Selic caiu {s_drop}; o juro, {p_drop}"),
                 ctx.text(
                    en="From {peak_year} to {low_year} the Selic went from "
                       "{s_peak} to {s_low}; the household rate, from {p_peak} "
                       "to {p_low}. The lowest household rate still beats "
                       "the Selic's highest.",
                    pt="De {peak_year} a {low_year} a Selic foi de {s_peak} "
                       "a {s_low}; o juro às famílias, de {p_peak} a {p_low}. "
                       "O menor juro às famílias ainda supera o maior da "
                       "Selic.")),
                (ctx.text(en="In {low_year}: {r_low} times the Selic",
                          pt="Em {low_year}: {r_low} vezes a Selic"),
                 ctx.text(
                    en="In {low_year} the household rate was {r_low} times "
                       "the Selic; in {last_year}, {r_last}. In points the "
                       "gap moved little, in multiples a lot.",
                    pt="Em {low_year} o juro às famílias era {r_low} vezes a "
                       "Selic; em {last_year}, {r_last}. Em pontos a "
                       "distância mudou pouco; em múltiplos, muito.")),
                (ctx.text(en="No view before {start_year}",
                          pt="Sem visão antes de {start_year}"),
                 ctx.text(
                    en="The red line begins in {start_year}, when the central "
                       "bank rebuilt the statistic. The chart shows the two "
                       "moving at a distance, not why. {partial_year} runs "
                       "to August.",
                    pt="A vermelha começa em {start_year}, quando o Banco "
                       "Central refez a estatística. O gráfico mostra as "
                       "duas a certa distância, não o motivo. {partial_year} "
                       "vai até agosto.")),
            ],
            facts={"gap_min": val(gap[g_lo], "dec1", year=g_lo),
                   "gap_max": val(gap[g_hi], "dec1", year=g_hi),
                   "start": at(start), "last": at(full),
                   "selic_low": val(selic[s_low], "pct2", year=s_low),
                   "selic_high": val(selic[s_high], "pct2", year=s_high),
                   "peak": at(2016), "low": at(2020),
                   "s_peak": val(selic[2016], "pct2", year=2016),
                   "s_low": val(selic[2020], "pct2", year=2020),
                   "p_peak": val(pf[2016], "pct2", year=2016),
                   "p_low": val(pf[2020], "pct2", year=2020),
                   "s_drop": val(100 * (selic[2016] - selic[2020]) / selic[2016],
                                 "pct", year=2020),
                   "p_drop": val(100 * (pf[2016] - pf[2020]) / pf[2016],
                                 "pct", year=2020),
                   "r_low": val(pf[2020] / selic[2020], "dec1", year=2020),
                   "r_last": val(pf[full] / selic[full], "dec1"),
                   "partial": at(partial)}),
        "credit.npl": ctx.story(
            title=ctx.text(
                en="Household arrears: {low} in {low_year}, {last} in "
                   "{last_year}",
                pt="Atraso das famílias: {low} em {low_year}, {last} em "
                   "{last_year}"),
            beats=[
                (ctx.text(en="Nearly doubled in five years",
                          pt="Quase dobrou em cinco anos"),
                 ctx.text(
                    en="From {low_year} to {last_year} the late share went "
                       "from {low} to {last}: {mult} times. In {first_year} "
                       "it was {first}, close to where it ended.",
                    pt="De {low_year} a {last_year} a fatia atrasada foi de "
                       "{low} a {last}: {mult} vezes. Em {first_year} era "
                       "{first}, perto de onde terminou.")),
                (ctx.text(en="{partial_year}, to August: the series high",
                          pt="{partial_year}, até agosto: máxima da série"),
                 ctx.text(
                    en="The dashed point is {aug}, above every full year, "
                       "including {first} in {first_year}. The year is "
                       "incomplete, so it is a reading, not a final figure.",
                    pt="O ponto tracejado é {aug}, acima de todos os anos "
                       "completos, inclusive {first} em {first_year}. O ano "
                       "está incompleto: é uma leitura, não um número "
                       "final.")),
                (ctx.text(en="Households run late more, but less so",
                          pt="Famílias atrasam mais, mas menos"),
                 ctx.text(
                    en="The red line sits above the grey one every year. The "
                       "gap went from {gap_first} points in {first_year} to "
                       "{gap_min} in {gap_min_year}, and {gap_last} in "
                       "{last_year}.",
                    pt="A vermelha fica acima da cinza todo ano. A diferença "
                       "foi de {gap_first} pontos em {first_year} a "
                       "{gap_min} em {gap_min_year}, e {gap_last} em "
                       "{last_year}.")),
                (ctx.text(en="Counts money, not families",
                          pt="Conta dinheiro, não famílias"),
                 ctx.text(
                    en="In {last_year}, of every 100 reais lent to "
                       "households, {last_r} were more than 90 days late. "
                       "It does not say how many families that is.",
                    pt="Em {last_year}, de cada 100 reais emprestados às "
                       "famílias, {last_r} estavam atrasados há mais de 90 "
                       "dias. Não diz quantas famílias são.")),
            ],
            facts={"low": val(npl_pf[n_low], "pct", year=n_low),
                   "last": val(npl_pf[full], "pct"),
                   "last_r": val(npl_pf[full], "dec1"),
                   "first": val(npl_pf[start], "pct", year=start),
                   "mult": val(npl_pf[full] / npl_pf[n_low], "dec1"),
                   "aug": val(npl_pf[partial], "pct", year=partial),
                   "partial": at(partial),
                   "gap_first": val(ngap[start], "dec1", year=start),
                   "gap_min": val(ngap[n_gmin], "dec1", year=n_gmin),
                   "gap_last": val(ngap[full], "dec1")}),
        "credit.lens": ctx.story(
            title=ctx.text(
                en="Debt more than doubled against income; the burden "
                   "rose less",
                pt="A dívida mais que dobrou frente à renda; o peso, menos"),
            beats=[
                (ctx.text(en="Debt: {months} months of income",
                          pt="Dívida: {months} meses de renda"),
                 ctx.text(
                    en="Debt is measured against 12 months of income. In "
                       "{first_year}: {d_first}, about {m_first} months. In "
                       "{last_year}: {d_last}, about {months}.",
                    pt="A dívida é medida contra 12 meses de renda. Em "
                       "{first_year}: {d_first}, cerca de {m_first} meses. "
                       "Em {last_year}: {d_last}, cerca de {months}.")),
                (ctx.text(en="Debt ×{r_d}; the burden, only ×{r_s}",
                          pt="Dívida ×{r_d}; o peso, só ×{r_s}"),
                 ctx.text(
                    en="Debt went from {d_first} to {d_last} of income. The "
                       "share of income spent servicing it went from "
                       "{s_first} to {s_last}.",
                    pt="A dívida foi de {d_first} a {d_last} da renda. A "
                       "fatia da renda gasta com o serviço dela foi de "
                       "{s_first} a {s_last}.")),
                (ctx.text(en="Housing is over half the rise",
                          pt="O imóvel é mais da metade da alta"),
                 ctx.text(
                    en="The shaded gap (housing credit) grew from {h_first} "
                       "to {h_last} points of income: {h_rise} of the {d_rise} "
                       "points that debt gained.",
                    pt="A faixa sombreada (crédito habitacional) foi de "
                       "{h_first} a {h_last} pontos da renda: {h_rise} dos "
                       "{d_rise} pontos que a dívida ganhou.")),
                (ctx.text(en="One jump in {big_year}",
                          pt="Um salto em {big_year}"),
                 ctx.text(
                    en="In {big_year} debt rose {jump} points in one year; in "
                       "the other years, {avg} on average. Since then it "
                       "has stayed between {a_lo} and {a_hi}.",
                    pt="Em {big_year} a dívida subiu {jump} pontos num ano; "
                       "nos outros, {avg} em média. Desde então ficou entre "
                       "{a_lo} e {a_hi}.")),
            ],
            facts={"d_first": val(di[first], "pct", year=first),
                   "d_last": val(di[full], "pct"),
                   "first": at(first), "last": at(full),
                   "m_first": val(di[first] * 12 / 100, "dec1", year=first),
                   "months": val(di[full] * 12 / 100, "dec1"),
                   "r_d": val(di[full] / di[first], "dec1"),
                   "r_s": val(ds[full] / ds[first], "dec1"),
                   "s_first": val(ds[first], "pct", year=first),
                   "s_last": val(ds[full], "pct"),
                   "h_first": val(h[first], "dec1", year=first),
                   "h_last": val(h[full], "dec1"),
                   "h_rise": val(h[full] - h[first], "dec1"),
                   "d_rise": val(di[full] - di[first], "dec1"),
                   "big": at(big),
                   "jump": val(rise[big], "dec1", year=big),
                   "avg": val(sum(others) / len(others), "dec1"),
                   "a_lo": val(a_lo, "pct"), "a_hi": val(a_hi, "pct")}),
    }


def world_stories(ctx) -> dict:
    """Insights for the four panels of the world plate (GDP in dollars, HDI,
    corruption index, reserves). Numbers are read from the plate's CSVs; the
    only years written into prose are the ones the plate itself marks (the
    2014-16 and 2020 bands, 2007-08 for reserves, the 2011/2012 CPI break).
    Where a sentence holds only while the data keep a shape, `need` fails.
    """
    full = ctx.LAST_FULL_YEAR
    join = {"pt": " e ", "en": " and "}

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil world stories: {why}; rewrite the "
                             f"copy that depends on it")

    gdp = {y: v / 1e9 for y, v in
           ctx.col("international/world.csv", "gdp_usd") if y >= 2006}
    brl = dict(ctx.col("macro/gdp.csv", "nominal_rbi"))
    hdi = dict(ctx.col("social/hdi.csv", "value"))
    cpi = dict(ctx.col("international/cpi.csv", "score"))
    res = dict(ctx.col("macro/reserves.csv", "eop_usbi"))
    partial = ctx.c.years[-1]

    # --- GDP in dollars
    span = [y for y in sorted(gdp) if y <= full]
    peak = max(span, key=gdp.get)
    low = min((y for y in span if y > peak), key=gdp.get)
    need(peak == 2011 and low == 2020, "the GDP peak/low are no longer "
         "2011 and 2020")
    need(gdp[full] < gdp[peak], "GDP in dollars is back at its peak")
    need(all(gdp[y] > gdp[low] for y in span if y > low),
         "GDP after the low is not above it")
    d15 = (1 - gdp[2015] / gdp[2014]) * 100
    d20 = (1 - gdp[2020] / gdp[2019]) * 100
    need(d15 > d20 > 0, "the 2015 fall is no longer larger than 2020's")
    need(all(gdp[y] / gdp[y - 1] > gdp[2015] / gdp[2014]
             for y in span if y > 2006 and y != 2015),
         "2015 is no longer the largest one-year fall in dollars")
    need(brl.get(full), "no GDP in reais for the last full year")
    rate = brl[full] / gdp[full]

    # --- HDI
    h_end, h_start = max(hdi), min(hdi)
    dip = min((y for y in hdi if y > 2019), key=hdi.get)
    need(dip == 2021 and hdi[dip] < hdi[2019], "the pandemic dip is no "
         "longer 2021 below 2019")
    need(hdi[2022] > hdi[2019], "HDI is not above its 2019 level in 2022")
    need(all(v < 0.8 for v in hdi.values()), "HDI reached the 0.800 line")
    need(h_end < full and h_end > dip, "HDI now reaches the last full year")
    flat = hdi[2021] - hdi[2014]
    up = hdi[h_end] - hdi[2021]
    early = hdi[2014] - hdi[h_start]
    late = hdi[h_end] - hdi[2014]
    need(up > 3 * flat > 0, "the late jump is no longer well above 2014-21")
    need(early > late > 0, "the HDI pace after 2014 is no longer slower")
    need(h_start == 2006, "HDI no longer starts in 2006")

    # --- CPI
    new = {y: v for y, v in cpi.items() if y >= 2012}
    old = {y: v for y, v in cpi.items() if y < 2012}
    need(new[2014] == new[2012], "CPI 2014 is no longer equal to 2012")
    need(new[2018] == new[full], "CPI last full year no longer equals 2018")
    loss = new[2014] - new[2018]
    need(loss > 0 and loss == new[2012] - new[full],
         "the CPI loss from 2014 to 2018 is no longer the whole loss")
    after = [new[y] for y in range(2018, full + 1)]
    drops = {y: new[y - 1] - new[y] for y in new if y - 1 in new}
    need(max(drops, key=drops.get) == 2015
         and list(drops.values()).count(drops[2015]) == 1,
         "the biggest CPI fall is no longer the single 2014-to-2015 step")
    need(max(old) == 2011 and min(new) == 2012
         and round(old[2011] * 10) < new[2012],
         "the old and new CPI segments no longer leave a visible step")

    # --- reserves
    need(res[2007] > 1.5 * res[2006], "reserves no longer jump in 2007")
    need(res[2008] > res[2007], "year-end reserves fell in 2008")
    flat_r = [res[y] for y in range(2012, full + 1)]
    r_lo, r_hi = min(flat_r), max(flat_r)
    need(res[2007] - res[2006] > r_hi - r_lo,
         "the 2007 jump is no longer larger than the 2012+ range")
    need(res[2011] / res[full] > 0.95 and res[2011] < r_hi,
         "reserves in 2011 are no longer close to the last full year")
    need(3.9 < res[2011] / res[2006] < 4.3,
         "reserves are no longer about four times 2006 by 2011")
    need(partial in res and partial > full, "no running-year reserve point")

    return {
        "world.gdp": ctx.story(
            title=ctx.text(
                en="In dollars, GDP is still {gap} below its {peak_year} peak",
                pt="Em dólares, o PIB segue {gap} abaixo do pico de "
                   "{peak_year}"),
            beats=[
                (ctx.text(en="The log scale hides a {drop} fall",
                          pt="A escala esconde uma queda de {drop}"),
                 ctx.text(
                    en="From US${peak}bn ({peak_year}) to US${low}bn "
                       "({low_year}): {drop} less. On a scale where each step "
                       "multiplies by ten, that fall looks like a small dip.",
                    pt="De US$ {peak} bi ({peak_year}) a US$ {low} bi "
                       "({low_year}): {drop} a menos. Numa escala em que cada "
                       "degrau multiplica por dez, a queda parece um recuo "
                       "discreto.")),
                (ctx.text(en="2015 fell harder than the pandemic",
                          pt="2015 pesou mais que a pandemia"),
                 ctx.text(
                    en="In 2015 GDP in dollars fell {d15} in one year, from "
                       "US${g14}bn to US${g15}bn. In 2020 the fall was {d20}.",
                    pt="Em 2015 o PIB em dólares caiu {d15} num só ano, de "
                       "US$ {g14} bi para US$ {g15} bi. Em 2020, a queda foi "
                       "de {d20}.")),
                (ctx.text(en="Regained {rise}, but not the peak",
                          pt="Recuperou {rise}, mas não o pico"),
                 ctx.text(
                    en="From {low_year} to {last_year} the line rose {rise}, "
                       "to US${last}bn. The {peak_year} level of US${peak}bn "
                       "has not been reached again.",
                    pt="De {low_year} a {last_year} a linha subiu {rise}, "
                       "para US$ {last} bi. O nível de {peak_year}, US$ "
                       "{peak} bi, não foi alcançado de novo.")),
                (ctx.text(en="Two sizes: R${rate} per dollar",
                          pt="Dois tamanhos: R$ {rate} por dólar"),
                 ctx.text(
                    en="The note gives {last_year} as R${brl}tn or "
                       "US${last}bn: R${rate} per dollar. The dollar line "
                       "carries the exchange rate along with production.",
                    pt="A nota traz {last_year} como R$ {brl} tri ou US$ "
                       "{last} bi: R$ {rate} por dólar. A linha em dólar "
                       "carrega o câmbio junto com a produção.")),
            ],
            facts={"gap": val((1 - gdp[full] / gdp[peak]) * 100, "pct"),
                   "drop": val((1 - gdp[low] / gdp[peak]) * 100, "pct",
                               year=low),
                   "peak": val(gdp[peak], "count", year=peak),
                   "low": val(gdp[low], "count", year=low),
                   "last": val(gdp[full], "count"),
                   "rise": val((gdp[full] / gdp[low] - 1) * 100, "pct"),
                   "d15": val(d15, "pct", year=2015),
                   "d20": val(d20, "pct", year=2020),
                   "g14": val(gdp[2014], "count", year=2014),
                   "g15": val(gdp[2015], "count", year=2015),
                   "brl": val(brl[full] / 1000, "dec1"),
                   "rate": val(rate, "dec2")}),
        "world.hdi": ctx.story(
            title=ctx.text(
                en="HDI is still {gap} short of the 0.800 line",
                pt="O IDH ainda está {gap} abaixo da linha de 0,800"),
            beats=[
                (ctx.text(en="Nearly flat to {dip_year}, then a jump",
                          pt="Quase parado até {dip_year}, depois um salto"),
                 ctx.text(
                    en="From 2014 to {dip_year} the index gained only "
                       "{flat}. From {dip_year} to {end_year} it gained "
                       "{up}.",
                    pt="De 2014 a {dip_year} o índice ganhou só {flat}. De "
                       "{dip_year} a {end_year}, ganhou {up}.")),
                (ctx.text(en="2022 was above the pre-pandemic level",
                          pt="Em 2022, acima do nível pré-pandemia"),
                 ctx.text(
                    en="From {pre} ({pre_year}) the index fell to {dipv} "
                       "({dip_year}); in {back_year} it was already at "
                       "{back}, above {pre_year}.",
                    pt="De {pre} ({pre_year}) o índice caiu a {dipv} "
                       "({dip_year}); em {back_year} já estava em {back}, "
                       "acima de {pre_year}.")),
                (ctx.text(en="The climb slowed after 2014",
                          pt="A subida desacelerou depois de 2014"),
                 ctx.text(
                    en="From {start_year} to 2014 the index gained {early}; "
                       "from 2014 to {end_year}, over a similar span, "
                       "{late}.",
                    pt="De {start_year} a 2014 o índice ganhou {early}; de "
                       "2014 a {end_year}, em tempo parecido, {late}.")),
                (ctx.text(en="The line stops at {end_year}",
                          pt="A linha para em {end_year}"),
                 ctx.text(
                    en="The axis runs to {partial_year}, but the data end "
                       "in {end_year}. The {gap} to 0.800 is the "
                       "{end_year} distance; later years are not shown.",
                    pt="O eixo vai até {partial_year}, mas os dados acabam em "
                       "{end_year}. Os {gap} até 0,800 são a distância de "
                       "{end_year}; os anos seguintes não aparecem.")),
            ],
            facts={"gap": val(0.8 - hdi[h_end], "dec3", year=h_end),
                   "dip": val(hdi[dip], "dec3", year=dip),
                   "dipv": val(hdi[dip], "dec3", year=dip),
                   "flat": val(flat, "dec3", year=dip),
                   "up": val(up, "dec3", year=h_end),
                   "end": val(hdi[h_end], "dec3", year=h_end),
                   "pre": val(hdi[2019], "dec3", year=2019),
                   "back": val(hdi[2022], "dec3", year=2022),
                   "early": val(early, "dec3", year=2014),
                   "late": val(late, "dec3", year=h_end),
                   "start": val(hdi[h_start], "dec3", year=h_start),
                   "partial": val(0, "count", year=partial)}),
        "world.cpi": ctx.story(
            title=ctx.text(
                en="The perception score fell {loss} points, {s14_year} to "
                   "{s18_year}",
                pt="A nota de percepção caiu {loss} pontos de {s14_year} a "
                   "{s18_year}"),
            beats=[
                (ctx.text(en="The points were lost by {s18_year}",
                          pt="Os pontos foram perdidos até {s18_year}"),
                 ctx.text(
                    en="From {s14} in {s14_year} to {s18} in {s18_year}. "
                       "{last_year} is back at {last}: since {s18_year} the "
                       "score stayed between {lo} and {hi}.",
                    pt="De {s14} em {s14_year} a {s18} em {s18_year}. Em "
                       "{last_year} está em {last}: desde {s18_year} a nota "
                       "ficou entre {lo} e {hi}.")),
                (ctx.text(en="{d15} of {loss} points in one year",
                          pt="{d15} dos {loss} pontos num só ano"),
                 ctx.text(
                    en="From {s14_year} to {s15_year} the score went from "
                       "{s14} to {s15}: {d15} points, the largest one-year "
                       "fall since the new method began.",
                    pt="De {s14_year} a {s15_year} a nota foi de {s14} a "
                       "{s15}: {d15} pontos, a maior queda de um ano desde "
                       "o novo método.")),
                (ctx.text(en="The 2011-12 step is not a rise",
                          pt="2011 a 2012: troca de método"),
                 ctx.text(
                    en="The dotted old scale (0-10, times 10) ends at {o11}; "
                       "the new one starts at {s12}. That {step}-point step "
                       "is a change of method, and only 2012 onward "
                       "compares.",
                    pt="A escala antiga (0 a 10, vezes 10) acaba em {o11}; a "
                       "nova começa em {s12}. Os {step} pontos de diferença "
                       "são troca de método: só de 2012 em diante se "
                       "compara.")),
            ],
            facts={"loss": val(loss, "count", year=2018),
                   "s12": val(new[2012], "count", year=2012),
                   "s14": val(new[2014], "count", year=2014),
                   "s15": val(new[2015], "count", year=2015),
                   "s18": val(new[2018], "count", year=2018),
                   "last": val(new[full], "count"),
                   "lo": val(min(after), "count"),
                   "hi": val(max(after), "count"),
                   "d15": val(drops[2015], "count", year=2015),
                   "o11": val(round(old[2011] * 10), "count", year=2011),
                   "step": val(new[2012] - round(old[2011] * 10), "count",
                               year=2012)}),
        "world.reserves": ctx.story(
            title=ctx.text(
                en="Reserves in {r11_year} were already {share} of {last_year}'s",
                pt="As reservas de {r11_year} já eram {share} das de "
                   "{last_year}"),
            beats=[
                (ctx.text(en="Fourfold in five years, then flat",
                          pt="Quadruplicaram em 5 anos e pararam"),
                 ctx.text(
                    en="From US${r06}bn ({r06_year}) to US${r11}bn "
                       "({r11_year}). From 2012 on, no year-end passed "
                       "US${hi}bn, nor went under US${lo}bn.",
                    pt="De US$ {r06} bi ({r06_year}) a US$ {r11} bi "
                       "({r11_year}). De 2012 em diante, nenhum fim de ano "
                       "passou de US$ {hi} bi nem ficou abaixo de US$ {lo} "
                       "bi.")),
                (ctx.text(en="2007 alone outweighs the later range",
                          pt="Só 2007 supera toda a oscilação depois"),
                 ctx.text(
                    en="In 2007 reserves rose US${jump}bn in one year. The "
                       "whole 2012-{last_year} range, highest to lowest, is "
                       "US${width}bn.",
                    pt="Em 2007 as reservas subiram US$ {jump} bi num ano. A "
                       "amplitude de 2012 a {last_year}, do maior ao menor "
                       "valor, é de US$ {width} bi.")),
                (ctx.text(en="Year-end points do not see 2008",
                          pt="O fim de ano não vê 2008"),
                 ctx.text(
                    en="The chart marks 2008 as a year of reserve sales, yet "
                       "year-end (US${r08}bn) is above 2007 (US${r07}bn). "
                       "What moves inside a year does not show.",
                    pt="O gráfico marca 2008 como ano de venda de reservas, "
                       "mas o fim de ano (US$ {r08} bi) supera 2007 (US$ "
                       "{r07} bi). O que oscila dentro do ano some.")),
                (ctx.text(en="The dashed {partial_year} point is one month",
                          pt="O ponto de {partial_year} é um mês"),
                 ctx.text(
                    en="US${rp}bn in {partial_year} is the latest month "
                       "available, not a closed year, so it is not "
                       "year-end like the others.",
                    pt="US$ {rp} bi em {partial_year} é o último mês "
                       "disponível, não um ano fechado: não é saldo de fim "
                       "de ano como os outros.")),
            ],
            facts={"share": val(res[2011] / res[full] * 100, "pct"),
                   "r11": val(res[2011], "count", year=2011),
                   "r06": val(res[2006], "count", year=2006),
                   "last": val(res[full], "count"),
                   "r07": val(res[2007], "count", year=2007),
                   "r08": val(res[2008], "count", year=2008),
                   "hi": val(r_hi, "count"),
                   "lo": val(r_lo, "count"),
                   "jump": val(res[2007] - res[2006], "count", year=2007),
                   "width": val(r_hi - r_lo, "count"),
                   "rp": val(res[partial], "count", year=partial),
                   "partial": val(res[partial], "count", year=partial)}),
    }


def people_stories(ctx) -> dict:
    """Insights for the four panels of the people plate (Brasil)."""
    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil people stories: {why}; rewrite the "
                             f"copy that depends on it")

    at = lambda y: val(0, "count", year=y)      # a year, as a fact
    r1 = lambda x: round(x, 1)

    # ------------------------------------------------------------ gini
    wb = {y: r1(v * 100) for y, v in ctx.col("social/gini.csv", "wb")}
    ib = {y: r1(v * 100) for y, v in ctx.col("social/gini.csv", "ibge")}
    wb0 = min(wb)
    ib0, ib1 = min(ib), max(ib)
    d20 = r1(wb[2019] - wb[2020])
    d06 = r1(wb[wb0] - wb[2019])
    ibd = r1(ib[2019] - ib[2020])
    floor = min(ib[y] for y in range(ib0, 2022))
    ceil = max(ib[y] for y in range(2022, ib1 + 1))
    rise = r1(ib[2018] - ib[2015])
    need(wb0 == 2006 and ib1 == full and ib[ib1] < ib[ib0],
         "the Gini series no longer start in 2006 / end in the last full year")
    need(d20 > d06 > 0 and min(wb, key=wb.get) == 2020,
         "the 2020 World Bank drop no longer exceeds the earlier fall")
    need(ibd < d20 / 2 and ib[2021] == ib[2019] and ib[2020] < ib[2019],
         "the official 2020 dip no longer reads as drawn")
    need(ceil < floor and all(y in ib for y in range(ib0, ib1 + 1)),
         "the official Gini no longer stays below its old floor after 2021")
    need(ib[ib1] > ib[ib1 - 1], "the last official reading no longer rises")
    need(ib[2015] == min(ib[y] for y in range(ib0, 2020)) and
         ib[2018] == max(ib[y] for y in range(ib0, 2020)) and ib[2018] > ib[2015],
         "the official rise from 2015 to 2018 no longer reads as drawn")
    need(all(wb[y] < wb[2019] for y in (2020,)) and wb[2021] > wb[2020],
         "the World Bank 2021 rebound is gone")

    # --------------------------------------------------------- poverty
    pov = dict(ctx.col("social/poverty.csv", "poverty_pct"))
    ext = dict(ctx.col("social/poverty.csv", "extreme_pct"))
    p0, p1 = min(pov), max(pov)
    need(p0 == 2006 and p1 == full - 1 and pov[p1] < pov[p0] / 2,
         "poverty is no longer under half of its start")
    d20p = r1(pov[2019] - pov[2020])
    d21p = r1(pov[2021] - pov[2020])
    need(d21p > d20p > 0 and pov[2021] > pov[2019] and
         pov[2021] > max(pov[y] for y in range(2012, 2021)) and
         pov[2011] > pov[2021],
         "the 2021 rebound is no longer the highest since 2011")
    need(pov[2014] == min(v for y, v in pov.items() if y < 2020) and
         all(pov[y] > pov[2014] for y in (2015, 2016, 2017, 2018, 2019, 2021))
         and pov[2020] < pov[2014] and pov[2022] < pov[2014],
         "poverty no longer stays above the 2014 low until 2022")
    rel_hi = round((1 - pov[p1] / pov[p0]) * 100)
    rel_lo = round((1 - ext[p1] / ext[p0]) * 100)
    need(rel_lo > rel_hi and pov[p0] - pov[p1] > ext[p0] - ext[p1],
         "the lower line no longer falls more in proportion")
    need(all(ext[y] < pov[y] for y in pov), "the red line leaves the teal one")
    need(2010 not in pov, "2010 now has a poverty rate")

    # ----------------------------------------------------- minimum wage
    mw = dict(ctx.col("macro/minimum_wage.csv", "value"))
    fx = dict(ctx.col("macro/dollar.csv", "avg"))
    ipca = dict(ctx.col("macro/ipca.csv", "value"))
    usd = {y: v / fx[y] for y, v in mw.items() if y in fx}
    peak = max((y for y in usd if y <= full), key=usd.get)
    need(peak < full and usd[full] < usd[peak], "the dollar wage is at its peak")
    need(min((y for y in fx if 2006 <= y <= full), key=fx.get) == peak,
         "the peak in dollars is no longer the cheapest dollar")
    need(all(mw[y] < mw[y + 1] for y in mw if y + 1 in mw),
         "the wage in reais no longer rises every year")
    for a, b in ((2014, 2015), (2019, 2020)):
        need(usd[b] < usd[a] and fx[b] > fx[a] and mw[b] > mw[a],
             f"the fall in dollars {a}-{b} no longer comes from the dollar")
    mult_nom = mw[full] / mw[2006]
    mult_fx = fx[full] / fx[2006]
    mult_usd = usd[full] / usd[2006]
    need(mult_nom > mult_fx > 1 and mult_usd > 1, "the wage-dollar contrast moved")
    mw_ratio = mw[full] / mw[peak]
    fx_ratio = fx[full] / fx[peak]
    need(fx_ratio > mw_ratio > 1, "the dollar no longer outgrew the wage since the peak")

    real = {}
    for y, v in mw.items():
        if y > full:
            continue
        factor = 1.0
        for k in range(y + 1, full + 1):
            factor *= 1 + ipca[k] / 100
        real[y] = v * factor
    gain = round((real[full] / real[2006] - 1) * 100)
    g14 = real[2014] - real[2006]
    g_rest = real[full] - real[2014]
    share = round(g14 / (real[full] - real[2006]) * 100)
    falls = [y for y in range(2007, full + 1) if real[y] < real[y - 1]]
    need(falls == [2015, 2018, 2021],
         "the real wage no longer falls in exactly 2015, 2018 and 2021")
    for y in falls:
        need(mw[y] / mw[y - 1] - 1 < ipca[y] / 100 and mw[y] > mw[y - 1],
             f"the {y} raise is no longer below the IPCA")
    need(g14 > g_rest > 0 and 50 < share < 75,
         "the real gain is no longer concentrated up to 2014")
    r15n = r1((mw[2015] / mw[2014] - 1) * 100)
    n21 = r1((mw[2021] / mw[2020] - 1) * 100)

    return {
        "people.gini": ctx.story(
            title=ctx.text(
                en="Official Gini fell {dt} points since {a_year}, in a zigzag",
                pt="Gini oficial caiu {dt} pontos desde {a_year}, em zigue-zague"),
            beats=[
                (ctx.text(en="One year beat the whole earlier fall",
                          pt="Um ano superou toda a queda anterior"),
                 ctx.text(
                    en="On the World Bank line, the Gini drops {d20} points in "
                       "{wb20_year} ({wb19} to {wb20}). From {wb06_year} to "
                       "{wb19_year}, the whole fall was {d06}. By "
                       "{wb21_year} it is {wb21}.",
                    pt="Na linha do Banco Mundial, o Gini cai {d20} pontos em "
                       "{wb20_year} ({wb19} para {wb20}). De {wb06_year} a "
                       "{wb19_year}, a queda toda foi de {d06}. Em "
                       "{wb21_year}, já está em {wb21}.")),
                (ctx.text(en="The dip's size depends on the source",
                          pt="Quem mede muda o tamanho do tombo"),
                 ctx.text(
                    en="The official Gini drops {ibd} in {ib20_year} ({ib19} "
                       "to {ib20}), under half the World Bank's fall. In "
                       "{ib21_year} it is {ib21}, the same as in {ib19_year}.",
                    pt="O Gini oficial cai {ibd} em {ib20_year} ({ib19} para "
                       "{ib20}), menos da metade da queda do Banco Mundial. "
                       "Em {ib21_year}, volta a {ib21}, igual a {ib19_year}.")),
                (ctx.text(en="A new floor only after 2021",
                          pt="Um piso novo só depois de 2021"),
                 ctx.text(
                    en="From {a_year} to {ib21_year}, the official Gini never "
                       "went below {floor}. From {ib22_year} on it never "
                       "went above {ceil}. The last reading, {ib25}, is up "
                       "from {ib24} in {ib24_year}.",
                    pt="De {a_year} a {ib21_year}, o Gini oficial nunca ficou "
                       "abaixo de {floor}. De {ib22_year} em diante, nunca "
                       "passou de {ceil}. A última leitura, {ib25}, subiu "
                       "frente a {ib24} de {ib24_year}.")),
                (ctx.text(en="Up {rise} points after the {ib15_year} low",
                          pt="Sobe {rise} pontos desde {ib15_year}"),
                 ctx.text(
                    en="The official Gini goes from {ib15} in {ib15_year} to "
                       "{ib18} in {ib18_year}. The band marks the 2014–16 "
                       "recession: it shows when, not why.",
                    pt="O Gini oficial vai de {ib15} em {ib15_year} a {ib18} "
                       "em {ib18_year}. A faixa marca a recessão de 2014–16: "
                       "mostra quando, não por quê.")),
            ],
            facts={"dt": val(r1(ib[ib0] - ib[ib1]), "dec1"),
                   "a": at(ib0), "d20": val(d20, "dec1"), "d06": val(d06, "dec1"),
                   "wb06": at(2006), "wb19": val(wb[2019], "dec1", year=2019),
                   "wb20": val(wb[2020], "dec1", year=2020),
                   "wb21": val(wb[2021], "dec1", year=2021),
                   "ibd": val(ibd, "dec1"),
                   "ib19": val(ib[2019], "dec1", year=2019),
                   "ib20": val(ib[2020], "dec1", year=2020),
                   "ib21": val(ib[2021], "dec1", year=2021),
                   "floor": val(floor, "dec1"), "ceil": val(ceil, "dec1"),
                   "ib22": at(2022),
                   "ib24": val(ib[2024], "dec1", year=2024),
                   "ib25": val(ib[ib1], "dec1", year=ib1),
                   "rise": val(rise, "dec1"),
                   "ib15": val(ib[2015], "dec1", year=2015),
                   "ib18": val(ib[2018], "dec1", year=2018)}),
        "people.poverty": ctx.story(
            title=ctx.text(
                en="Poverty (US${hi}/day) in {p1_year}: under half of "
                   "{p0_year}",
                pt="Pobreza (US$ {hi}/dia) em {p1_year}: menos da metade de "
                   "{p0_year}"),
            beats=[
                (ctx.text(en="{p21_year} rose more than {p20_year} fell",
                          pt="{p21_year} subiu mais do que {p20_year} caiu"),
                 ctx.text(
                    en="The line falls {d20} points in {p20_year} ({p19} to "
                       "{p20}) and rises {d21} in {p21_year}, to {p21}: the "
                       "highest since {p11_year}.",
                    pt="A linha cai {d20} pontos em {p20_year} ({p19} para "
                       "{p20}) e sobe {d21} em {p21_year}, até {p21}: o maior "
                       "valor desde {p11_year}.")),
                (ctx.text(en="Only in {p22_year}, back at {p14_year}'s level",
                          pt="Só {p22_year} volta ao nível de {p14_year}"),
                 ctx.text(
                    en="After the low of {p14} in {p14_year}, poverty stayed "
                       "above it every year, except {p20_year}, until "
                       "{p22_year}, when it reached {p22}.",
                    pt="Depois do piso de {p14} em {p14_year}, a pobreza ficou "
                       "acima dele todos os anos, exceto {p20_year}, até "
                       "{p22_year}, quando chegou a {p22}.")),
                (ctx.text(en="The lower line fell more in proportion",
                          pt="A de baixo caiu mais em proporção"),
                 ctx.text(
                    en="From {p0_year} to {p1_year}, the US${hi} rate fell "
                       "{rel_hi}% ({p0} to {p1}); the US${lo} rate fell "
                       "{rel_lo}% ({e0} to {e1}). In points, the top one fell "
                       "more.",
                    pt="De {p0_year} a {p1_year}, a taxa de US$ {hi} caiu "
                       "{rel_hi}% ({p0} para {p1}); a de US$ {lo} caiu "
                       "{rel_lo}% ({e0} para {e1}). Em pontos, a de cima "
                       "caiu mais.")),
                (ctx.text(en="Red sits inside the teal line",
                          pt="A vermelha está dentro da verde"),
                 ctx.text(
                    en="Whoever is below US${lo} is also below US${hi}. In "
                       "{p1_year}, {e1} of the population is inside the {p1}: "
                       "the lines do not add up. Brazil has no official line.",
                    pt="Quem está abaixo de US$ {lo} também está abaixo de "
                       "US$ {hi}. Em {p1_year}, {e1} da população está dentro "
                       "dos {p1}: as linhas não se somam. O Brasil não tem "
                       "linha oficial.")),
            ],
            facts={"hi": val(8.30, "dec2"), "lo": val(3.00, "dec2"),
                   "p0": val(pov[p0], "pct", year=p0),
                   "p1": val(pov[p1], "pct", year=p1),
                   "e0": val(ext[p0], "pct"), "e1": val(ext[p1], "pct", year=p1),
                   "p11": val(pov[2011], "pct", year=2011),
                   "p14": val(pov[2014], "pct", year=2014),
                   "p19": val(pov[2019], "pct", year=2019),
                   "p20": val(pov[2020], "pct", year=2020),
                   "p21": val(pov[2021], "pct", year=2021),
                   "p22": val(pov[2022], "pct", year=2022),
                   "d20": val(d20p, "dec1"), "d21": val(d21p, "dec1"),
                   "rel_hi": val(rel_hi, "count"),
                   "rel_lo": val(rel_lo, "count")}),
        "people.minimum_wage": ctx.story(
            title=ctx.text(
                en="In dollars, the wage also swings with the exchange rate",
                pt="Em dólares, o mínimo também oscila com o câmbio"),
            beats=[
                (ctx.text(en="Reais ×{m_nom}; dollars only ×{m_usd}",
                          pt="Em reais, ×{m_nom}; em dólares, só ×{m_usd}"),
                 ctx.text(
                    en="From {y0_year} to {n1_year}, the wage goes from R$ "
                       "{n0} to R$ {n1}, but the dollar goes from R$ {fx0} to "
                       "R$ {fx1} (×{m_fx}). So US${u0} become US${u1}.",
                    pt="De {y0_year} a {n1_year}, o mínimo vai de R$ {n0} a R$ "
                       "{n1}, mas o dólar vai de R$ {fx0} a R$ {fx1} "
                       "(×{m_fx}). Assim, US$ {u0} viram US$ {u1}.")),
                (ctx.text(en="The {peak_year} peak is the cheapest dollar",
                          pt="Pico de {peak_year}: o dólar mais barato"),
                 ctx.text(
                    en="In {peak_year}, R$ {mw_peak} bought US${u_peak}, with "
                       "the dollar at R$ {fx_peak}, the lowest in the series. "
                       "Since then the wage grew ×{mw_ratio}; the dollar, "
                       "×{fx_ratio}.",
                    pt="Em {peak_year}, R$ {mw_peak} valiam US$ {u_peak}, com "
                       "o dólar a R$ {fx_peak}, o menor da série. Desde "
                       "então, o salário cresceu ×{mw_ratio}; o dólar, "
                       "×{fx_ratio}.")),
                (ctx.text(en="Down in dollars while up in reais",
                          pt="Caiu em dólares enquanto subia em reais"),
                 ctx.text(
                    en="In {y15_year}, R$ {mw14} to {mw15}, yet US${u14} to "
                       "{u15}, as the dollar went from R$ {f14} to {f15}. In "
                       "{y20_year}, the same: US${u19} to {u20}.",
                    pt="Em {y15_year}, de R$ {mw14} a {mw15}, mas de US$ {u14} "
                       "a {u15}, com o dólar de R$ {f14} a {f15}. Em "
                       "{y20_year}, igual: de US$ {u19} a {u20}.")),
            ],
            facts={"m_nom": val(mult_nom, "dec1"), "m_usd": val(mult_usd, "dec1"),
                   "m_fx": val(mult_fx, "dec1"), "y0": at(2006),
                   "n0": val(mw[2006], "count", year=2006),
                   "n1": val(mw[full], "count"),
                   "fx0": val(fx[2006], "dec2", year=2006),
                   "fx1": val(fx[full], "dec2"),
                   "u0": val(usd[2006], "count", year=2006),
                   "u1": val(usd[full], "count"),
                   "peak": at(peak), "mw_peak": val(mw[peak], "count", year=peak),
                   "u_peak": val(usd[peak], "count", year=peak),
                   "fx_peak": val(fx[peak], "dec2", year=peak),
                   "mw_ratio": val(mw_ratio, "dec1"),
                   "fx_ratio": val(fx_ratio, "dec1"),
                   "y15": at(2015), "y20": at(2020),
                   "mw14": val(mw[2014], "count"), "mw15": val(mw[2015], "count"),
                   "u14": val(usd[2014], "count"), "u15": val(usd[2015], "count"),
                   "u19": val(usd[2019], "count"), "u20": val(usd[2020], "count"),
                   "f14": val(fx[2014], "dec2"), "f15": val(fx[2015], "dec2")}),
        "people.lens": ctx.story(
            title=ctx.text(
                en="After inflation, the minimum wage rose {gain}% since "
                   "{y0_year}",
                pt="Descontada a inflação, o mínimo subiu {gain}% desde "
                   "{y0_year}"),
            beats=[
                (ctx.text(en="The lines meet in {n1_year} by construction",
                          pt="Linhas se tocam em {n1_year} por construção"),
                 ctx.text(
                    en="The brown line puts every year in {n1_year} prices: "
                       "R$ {n0} of {y0_year} equal R$ {r0}. Nominally the "
                       "wage is ×{m_nom}; after prices, ×{m_real}.",
                    pt="A marrom põe todos os anos nos preços de {n1_year}: "
                       "R$ {n0} de {y0_year} equivalem a R$ {r0}. No valor "
                       "nominal, o mínimo é ×{m_nom}; descontados os preços, "
                       "×{m_real}.")),
                (ctx.text(en="{share}% of the gain came by {y14_year}",
                          pt="{share}% do ganho veio até {y14_year}"),
                 ctx.text(
                    en="In {n1_year} reais, the wage rose R$ {g14} up to "
                       "{y14_year} and R$ {g_rest} from then to {n1_year}: "
                       "the second stretch is longer and gained less.",
                    pt="Em reais de {n1_year}, o mínimo subiu R$ {g14} até "
                       "{y14_year} e R$ {g_rest} de então até {n1_year}: o "
                       "segundo trecho é mais longo e ganhou menos.")),
                (ctx.text(en="Real dips in {y15_year}, {y18_year} and "
                             "{y21_year}",
                          pt="Recuos reais em {y15_year}, {y18_year} e "
                             "{y21_year}"),
                 ctx.text(
                    en="In {y21_year} the wage rose {n21}, below the "
                       "{ipca21} IPCA: in {n1_year} reais, from R$ {r20} to "
                       "R$ {r21}. The raise also trailed the IPCA in {y15_year} "
                       "and {y18_year}.",
                    pt="Em {y21_year} o mínimo subiu {n21}, abaixo dos "
                       "{ipca21} do IPCA: em reais de {n1_year}, de R$ {r20} "
                       "a R$ {r21}. O reajuste também ficou abaixo do IPCA "
                       "em {y15_year} e {y18_year}.")),
            ],
            facts={"gain": val(gain, "count"), "y0": at(2006),
                   "n1": val(mw[full], "count"),
                   "n0": val(mw[2006], "count", year=2006),
                   "r0": val(real[2006], "count"),
                   "m_nom": val(mult_nom, "dec1"),
                   "m_real": val(real[full] / real[2006], "dec1"),
                   "share": val(share, "count"), "y14": at(2014),
                   "g14": val(g14, "count"), "g_rest": val(g_rest, "count"),
                   "y15": at(2015), "y18": at(2018), "y21": at(2021),
                   "n21": val(n21, "pct"), "ipca21": val(ipca[2021], "pct"),
                   "r20": val(real[2020], "count"),
                   "r21": val(real[2021], "count")}),
    }


def demography_stories(ctx) -> dict:
    """Insights for the four demography panels (IBGE 2024 projection; the UN
    net migration only in the last panel). Numbers are read from the CSVs;
    only the years the plate itself marks are written into a sentence."""
    full = ctx.LAST_FULL_YEAR
    obs = 2024          # fig_demographics dashes everything after this year
    replacement = 2.1   # the dashed replacement line of fig_demographics

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil demography stories: {why}; rewrite the "
                             f"copy that depends on it")

    at = lambda y: val(0, "count", year=y)      # a year, as a fact

    first = ctx.c.years[0]
    last = ctx.c.years[-1]
    need(first < obs < full <= last, "the plate's observed/dashed split moved")

    pop = dict(ctx.col("social/population.csv", "pop_mn"))
    tfr = dict(ctx.col("social/population.csv", "tfr"))
    births = dict(ctx.col("social/population.csv", "births"))
    deaths = dict(ctx.col("social/population.csv", "deaths"))
    wpop = dict(ctx.col("social/demography.csv", "population"))
    mig = dict(ctx.col("social/demography.csv", "net_migration"))
    span = list(range(first, last + 1))
    need(all(y in pop and y in tfr and y in births and y in deaths
             for y in span), "a plotted year is missing from population.csv")

    # ---------------------------------------------------- population
    peak = max(pop, key=pop.get)
    need(peak > last, "the projected peak is now inside the plotted years")
    need(all(pop[y] > pop[y - 1] for y in span[1:]),
         "the population no longer rises every year")
    gain = pop[full] - pop[first]
    to_peak = pop[peak] - pop[full]
    share = gain / (gain + to_peak) * 100
    need(0 < to_peak < gain, "the peak is no longer closer than the start")
    step = {y: pop[y] - pop[y - 1] for y in span[1:]}
    need(2016 in step and 2013 in step and 2020 in step and 2022 in step,
         "a step year is missing")
    need(all(step[y] < 1.0 for y in range(2021, full + 1)),
         "the yearly gain is no longer under 1M from 2021 on")
    need(min(step[y] for y in range(first + 1, 2021)) > 1.0,
         "a yearly gain before 2021 was already under 1M")
    need(min(step[y] for y in range(2021, full + 1)) == step[2022],
         "the smallest yearly gain is no longer 2022")
    need(abs(step[2016] - step[2013]) < 0.2 and step[2020] - step[2022] > 0.4,
         "the 2014-16 band has a step as large as the one after 2020")

    # ---------------------------------------------------- fertility
    need(max(tfr[y] for y in span) < replacement,
         "a plotted year reaches replacement")
    gap0, gap1 = replacement - tfr[first], replacement - tfr[obs]
    need(gap1 > 2 * gap0, "the gap to replacement no longer more than doubles")
    d_early = tfr[first] - tfr[2019]
    d_late = tfr[2019] - tfr[obs]
    need(d_early > 0 and d_late > d_early
         and d_late > (d_early + d_late) / 2,
         "most of the fertility fall is no longer after 2019")
    need(2019 - first > 2 * (obs - 2019), "the two stretches are not 13 vs 5")

    # ---------------------------------------------------- births and deaths
    br = {y: births[y] / (pop[y] * 1e6) * 1e3 for y in span}
    dr = {y: deaths[y] / (pop[y] * 1e6) * 1e3 for y in span}
    need(all(br[y] > dr[y] for y in span), "deaths overtake births on the plate")
    ratio = {y: births[y] / deaths[y] for y in span}
    need(ratio[first] > ratio[obs] > ratio[last], "births per death no longer fall")
    b_fall = br[first] - br[obs]
    d_rise = dr[obs] - dr[first]
    need(b_fall > 0 and d_rise > 0 and b_fall > 3 * d_rise,
         "births no longer drive most of the narrowing")
    dpeak = max(span, key=dr.get)
    need(dpeak == 2021, "the death-rate peak is no longer in 2021")
    need(dr[2019] - dr[first] > 0 and
         dr[2021] - dr[2019] > 3 * (dr[2019] - dr[first]),
         "the 2019-21 jump is no longer several times the earlier rise")
    need(dr[obs] > dr[2019] and dr[obs] < dr[2021],
         "deaths in the last observed year are not between 2019 and 2021")

    # ---------------------------------------------------- natural, migration
    nat = {y: br[y] - dr[y] for y in span}
    nm = {y: mig[y] / wpop[y] * 1e3 for y in mig if y >= first}
    need(all(v < 0 for v in nm.values()), "net migration is no longer negative")
    need(max(nm) < last, "net migration now reaches the last plotted year")
    need(2021 in nm, "no migration value for 2021")
    need(min(nat.values()) > abs(min(nm.values())),
         "migration is no longer smaller than the natural increase")
    cross = next((y for y in sorted(births)
                  if y > obs and deaths[y] > births[y]), None)
    need(cross == peak + 1 and cross > last,
         "the crossing is no longer the year after the peak, outside the frame")
    need(min(nat[y] for y in span if y <= full) == nat[2021]
         and abs(nat[last] - nat[2021]) < 0.1,
         "the projected natural increase no longer meets the 2021 low")
    need(dr[2021] - dr[last] > 1 and br[2021] - br[last] > 1,
         "2021 and the last year no longer differ in composition")
    need(nat[first] > nat[obs] > nat[last], "natural increase no longer shrinks")

    return {
        "demography.population": ctx.story(
            title=ctx.text(
                en="Still growing, ever slower: projected peak in {peak_year}",
                pt="Ainda cresce, cada vez menos: pico projetado em "
                   "{peak_year}"),
            beats=[
                (ctx.text(en="{share} of the way to peak done",
                          pt="Já foram {share} do caminho ao pico"),
                 ctx.text(
                    en="From {first_year} to {full_year} the population "
                       "gained {gain}; to the projected peak in {peak_year}, "
                       "{to_peak} remain. Slower growth is not decline: the "
                       "fall comes only after the peak.",
                    pt="De {first_year} a {full_year} a população ganhou "
                       "{gain}; até o pico projetado, em {peak_year}, "
                       "faltam {to_peak}. Crescer mais devagar não é "
                       "encolher: a queda só vem depois do pico.")),
                (ctx.text(en="Yearly gain drops under one million",
                          pt="Ganho anual cai abaixo de um milhão"),
                 ctx.text(
                    en="It was {s20} in {s20_year}, {s22} in {s22_year}, and "
                       "has stayed under {one} since {s21_year}. In the 2014–16 "
                       "band it barely moved: {s13} to {s16}.",
                    pt="Era {s20} em {s20_year}, {s22} em {s22_year}, e fica "
                       "abaixo de {one} desde {s21_year}. Na faixa de "
                       "2014–16, mal mexeu: de {s13} a {s16}.")),
                (ctx.text(en="The frame ends before the peak",
                          pt="O quadro acaba antes do pico"),
                 ctx.text(
                    en="The line stops in {last_year}, {n_after} years "
                       "before the projected peak. The peak and the fall "
                       "appear only in the note, as IBGE projection.",
                    pt="A linha para em {last_year}, {n_after} anos antes do "
                       "pico projetado. O pico e a queda aparecem só na "
                       "nota, como projeção do IBGE.")),
            ],
            facts={"peak": val(pop[peak], "pop_mn", year=peak),
                   "share": val(share, "pct", year=full),
                   "first": at(first), "last": at(last),
                   "gain": val(gain, "pop_mn"),
                   "to_peak": val(to_peak, "pop_mn", year=peak),
                   "s13": val(step[2013], "pop_mn", year=2013),
                   "s16": val(step[2016], "pop_mn", year=2016),
                   "s20": val(step[2020], "pop_mn", year=2020),
                   "s21": at(2021),
                   "s22": val(step[2022], "pop_mn", year=2022),
                   "one": val(1.0, "pop_mn"),
                   "n_after": val(peak - last, "count"),
                   "full": at(full)}),
        "demography.fertility": ctx.story(
            title=ctx.text(
                en="Fertility never reached replacement and keeps falling",
                pt="Fecundidade nunca chegou à reposição e segue caindo"),
            beats=[
                (ctx.text(en="The distance to replacement more than doubled",
                          pt="A distância da reposição mais que dobrou"),
                 ctx.text(
                    en="The dashed line is {repl} children per woman, where "
                       "each generation replaces itself. In {first_year} the "
                       "rate sat {gap0} below it; in {obs_year}, {gap1}.",
                    pt="A linha tracejada é {repl} filhos por mulher, onde "
                       "cada geração se repõe. Em {first_year} a taxa ficava "
                       "{gap0} abaixo dela; em {obs_year}, {gap1}.")),
                (ctx.text(en="Over half the fall came after {y19_year}",
                          pt="Mais da metade da queda é pós-{y19_year}"),
                 ctx.text(
                    en="The rate lost {d_early} in the {n_early} years up to "
                       "{y19_year}, and {d_late} in the {n_late} years up to "
                       "{obs_year}.",
                    pt="A taxa perdeu {d_early} nos {n_early} anos até "
                       "{y19_year}, e {d_late} nos {n_late} anos até "
                       "{obs_year}.")),
                (ctx.text(en="Below replacement, yet the population grows",
                          pt="Abaixo da reposição, e a população cresce"),
                 ctx.text(
                    en="In every plotted year the rate stayed under {repl}, "
                       "and the population still gained {gain} from "
                       "{first_year} to {full_year}. IBGE puts the peak in "
                       "{peak_year}.",
                    pt="Em todos os anos da linha a taxa ficou abaixo de "
                       "{repl}, e a população ainda ganhou {gain} de "
                       "{first_year} a {full_year}. O IBGE põe o pico em "
                       "{peak_year}.")),
            ],
            facts={"repl": val(replacement, "dec1", year=obs),
                   "first": at(first), "obs": at(obs), "full": at(full),
                   "gap0": val(gap0, "dec2", year=first),
                   "gap1": val(gap1, "dec2", year=obs),
                   "y19": at(2019),
                   "d_early": val(d_early, "dec2", year=2019),
                   "d_late": val(d_late, "dec2", year=obs),
                   "n_early": val(2019 - first, "count", year=2019),
                   "n_late": val(obs - 2019, "count", year=obs),
                   "gain": val(gain, "pop_mn"),
                   "peak": at(peak)}),
        "demography.birth_death": ctx.story(
            title=ctx.text(
                en="Births fall and deaths rise: the margin shrinks",
                pt="Nascimentos caem e óbitos sobem: a folga encolhe"),
            beats=[
                (ctx.text(en="Births per death: from {r0} to {r1}",
                          pt="Nascimentos por óbito: de {r0} a {r1}"),
                 ctx.text(
                    en="Dividing the green line by the black one gives {r0} "
                       "in {r0_year}, {r1} in {r1_year} and {r2} in "
                       "{r2_year} (projection). These are rates from "
                       "IBGE's model, not registered deaths.",
                    pt="Dividindo a linha verde pela preta: {r0} em "
                       "{r0_year}, {r1} em {r1_year} e {r2} em {r2_year} "
                       "(projeção). São taxas do modelo do IBGE, não óbitos "
                       "registrados.")),
                (ctx.text(en="The closing comes mostly from births",
                          pt="A aproximação vem mais dos nascimentos"),
                 ctx.text(
                    en="From {r0_year} to {r1_year} the green line fell "
                       "{b_fall} per thousand, while the black one rose "
                       "{d_rise}. Most of the ground the lines closed came "
                       "from births.",
                    pt="De {r0_year} a {r1_year} a linha verde caiu "
                       "{b_fall} por mil, enquanto a preta subiu {d_rise}. "
                       "A maior parte do espaço que as linhas fecharam veio "
                       "dos nascimentos.")),
                (ctx.text(en="Two years rose more than thirteen",
                          pt="Dois anos subiram mais que treze"),
                 ctx.text(
                    en="Deaths went from {d06} to {d19} per thousand in "
                       "{n_slow} years, then to {d21} in {n_jump} years, "
                       "in {d21_year}. In {r1_year}, {d24}: still above "
                       "{d19_year}.",
                    pt="Os óbitos foram de {d06} a {d19} por mil em "
                       "{n_slow} anos, e a {d21} em {n_jump} anos, "
                       "em {d21_year}. Em {r1_year}, {d24}: ainda acima de "
                       "{d19_year}.")),
            ],
            facts={"r0": val(ratio[first], "dec1", year=first),
                   "r1": val(ratio[obs], "dec1", year=obs),
                   "r2": val(ratio[last], "dec1", year=last),
                   "b_fall": val(b_fall, "dec1", year=obs),
                   "d_rise": val(d_rise, "dec1", year=obs),
                   "d06": val(dr[first], "dec1", year=first),
                   "d19": val(dr[2019], "dec1", year=2019),
                   "d21": val(dr[2021], "dec1", year=2021),
                   "d24": val(dr[obs], "dec1", year=obs),
                   "n_slow": val(2019 - first, "count", year=2019),
                   "n_jump": val(2021 - 2019, "count", year=2021)}),
        "demography.natural_migration": ctx.story(
            title=ctx.text(
                en="IBGE: peak in {peak_year}; deaths pass births in "
                   "{cross_year}",
                pt="IBGE: pico em {peak_year}; óbitos passam nascimentos "
                   "em {cross_year}"),
            beats=[
                (ctx.text(en="Peak and crossing: neighbouring years",
                          pt="Pico e cruzamento: anos vizinhos"),
                 ctx.text(
                    en="In IBGE's model the population peaks in {peak_year} "
                       "and deaths overtake births one year later, in "
                       "{cross_year}. The green line, {n_obs} in "
                       "{obs_year}, is heading to zero.",
                    pt="No modelo do IBGE a população atinge o pico em "
                       "{peak_year} e os óbitos superam os nascimentos um "
                       "ano depois, em {cross_year}. A linha verde, "
                       "{n_obs} em {obs_year}, caminha para o zero.")),
                (ctx.text(en="Same low in {n21_year} and {n26_year}",
                          pt="Mesmo piso em {n21_year} e {n26_year}"),
                 ctx.text(
                    en="Births minus deaths: {n21} per thousand in "
                       "{n21_year}, {n26} in {n26_year} (projection). In "
                       "{n21_year}: births {b21}, deaths {d21}. In "
                       "{n26_year}: births {b26}, deaths {d26}.",
                    pt="Nascimentos menos óbitos: {n21} por mil em "
                       "{n21_year}, {n26} em {n26_year} (projeção). Em "
                       "{n21_year}: nascimentos {b21}, óbitos {d21}. Em "
                       "{n26_year}: nascimentos {b26}, óbitos {d26}.")),
                (ctx.text(en="Migration is small and always negative",
                          pt="A migração é pequena e sempre negativa"),
                 ctx.text(
                    en="The purple line stays between {m_lo} and {m_hi} "
                       "per thousand: more people leave than arrive. In "
                       "{m21_year}, {m21}. Sources differ (UN, IBGE): the "
                       "lines do not add up exactly.",
                    pt="A linha roxa fica entre {m_lo} e {m_hi} por mil: "
                       "saem mais pessoas do que entram. Em {m21_year} era "
                       "{m21}. Fontes diferentes (ONU e IBGE): as linhas "
                       "não somam exato.")),
            ],
            facts={"peak": at(peak), "cross": at(cross),
                   "obs": at(obs),
                   "n_obs": val(nat[obs], "dec1", year=obs),
                   "n21": val(nat[2021], "dec1", year=2021),
                   "n26": val(nat[last], "dec1", year=last),
                   "b21": val(br[2021], "dec1", year=2021),
                   "d21": val(dr[2021], "dec1", year=2021),
                   "b26": val(br[last], "dec1", year=last),
                   "d26": val(dr[last], "dec1", year=last),
                   "m_lo": val(min(nm.values()), "dec1",
                               year=min(nm, key=nm.get)),
                   "m_hi": val(max(nm.values()), "dec1",
                               year=max(nm, key=nm.get)),
                   "m21": val(nm[2021], "dec1", year=2021)}),
    }


def security_stories(ctx) -> dict:
    """Insights for the four panels of the security plate (Brasil).

    Every number is read from the CSVs the plate draws; the only years typed
    into a sentence are events the plate marks (the 2014-16 band, 2020). No
    cause is named: the plate draws none, and the subject is deaths.
    """
    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil security stories: {why}; rewrite the "
                             f"copy that depends on it")

    at = lambda y: val(0, "count", year=y)

    def per(count, base):
        return {y: v / base[y] * 1e5 for y, v in count.items() if y in base}

    reg = {y: v for y, v in ctx.col("social/homicides.csv", "rate")
           if y <= full}
    est = dict(ctx.col("social/homicides.csv", "est_rate"))
    mvi = {y: v for y, v in ctx.col("social/violence_fbsp.csv", "mvi_rate")
           if y <= full}
    pop = {y: v * 1e6 for y, v in ctx.col("social/population.csv", "pop_mn")}
    fpop = dict(ctx.col("social/demography.csv", "population_female"))
    suicide = {y: v for y, v in per(
        dict(ctx.col("social/deaths.csv", "suicide")), pop).items()
        if y >= 2006}
    road = {y: v for y, v in per(
        dict(ctx.col("social/deaths.csv", "road")), pop).items() if y >= 2006}
    who_s = {y: v for y, v in ctx.col("social/security.csv",
                                      "suicide_per_100k") if y >= 2006}
    who_r = {y: v for y, v in ctx.col("social/security.csv",
                                      "road_deaths_per_100k") if y >= 2006}
    police = per(dict(ctx.col("social/violence_fbsp.csv", "police_killings")),
                 pop)
    wom = per(dict(ctx.col("social/violence_fbsp.csv", "women_homicides")),
              fpop)
    fem = per(dict(ctx.col("social/violence_fbsp.csv", "femicides")), fpop)

    # ---------------------------------------------------------- homicide
    r_last, m_last, e_last = max(reg), max(mvi), max(est)
    e_first = min(est)
    peak = max(reg, key=reg.get)
    need(max(est, key=est.get) == peak and max(mvi, key=mvi.get) == peak,
         "the three homicide series no longer peak in the same year")
    need(all(reg[y] < reg[peak] for y in reg if y > peak)
         and all(est[y] < est[peak] for y in est if y > peak)
         and all(mvi[y] < mvi[peak] for y in mvi if y > peak)
         and r_last > peak and m_last > peak,
         "a homicide series is no longer below its peak after the peak")
    reg_fall = round((1 - reg[r_last] / reg[peak]) * 100)
    rcl = 2019      # the reclassification year the plate marks
    prev = rcl - 1
    need(all(y in d for d in (reg, est, mvi) for y in (prev, rcl)),
         "the marked year has no homicide values")
    need(all(mvi[y] < reg[y] for y in mvi if y in reg and y <= prev)
         and all(mvi[y] > reg[y] for y in mvi if y in reg and rcl <= y),
         "the FBSP line no longer crosses above the registered one at the "
         "marked year")
    need(all(est[y] > reg[y] for y in est if y in reg),
         "the estimated line is no longer above the registered one")
    gap = {y: est[y] - reg[y] for y in est if y in reg}
    need(max(gap, key=gap.get) == rcl and gap[rcl] > gap[prev] > gap[prev - 1],
         "the hidden-homicide gap no longer peaks in the marked year")
    fall = lambda s: round((1 - s[rcl] / s[prev]) * 100)
    need(r_last < m_last and mvi[r_last] > reg[r_last]
         and mvi[m_last] < reg[r_last],
         "the FBSP line no longer ends below the red one only for its "
         "extra year")

    # ----------------------------------------------------------- suicide
    s_first, s_last = min(suicide), max(suicide)
    s_peak = max(suicide, key=suicide.get)
    need(s_first == 2006 and s_last == full and s_peak < s_last
         and suicide[s_last] > suicide[s_first],
         "suicide no longer rises to a peak before the last year")
    rise = round(suicide[s_last] / suicide[s_first] * 100 - 100)
    back = round((1 - suicide[s_last] / suicide[s_peak]) * 100)
    need(back >= 1, "suicide has not receded from its peak")
    steps = [y for y in sorted(suicide) if y > s_first]
    ups = [y for y in steps if suicide[y] > suicide[y - 1]]
    downs = [y for y in steps if y not in ups]
    need(len(downs) == 4, "suicide no longer has exactly four years "
         "without a rise")
    jump = {y: suicide[y] / suicide[y - 1] - 1 for y in steps}
    j_year = max(jump, key=jump.get)
    need(j_year == 2021, "the largest suicide jump is no longer the year "
         "after the 2020 band")
    w_last = max(who_s)
    need(w_last < s_last and min(who_s) == s_first and w_last in suicide,
         "the WHO suicide line no longer starts in the first year and ends "
         "before the SIM one")
    raw_rise = round((suicide[w_last] / suicide[s_first] - 1) * 100)
    who_rise = round((who_s[w_last] / who_s[s_first] - 1) * 100)
    need(who_rise < raw_rise, "the age-adjusted rise is no longer smaller")

    # -------------------------------------------------------------- road
    rd_peak = max(road, key=road.get)
    rd_low = min((y for y in road if y > rd_peak), key=road.get)
    rd_last = max(road)
    need(rd_last == full and rd_peak < rd_low < rd_last
         and road[rd_low] < road[rd_last] < road[rd_peak],
         "road deaths are no longer peak, then low, then a partial return")
    note_pct = round((1 - road[rd_last] / road[rd_peak]) * 100)
    fall_pct = round((1 - road[rd_low] / road[rd_peak]) * 100)
    rise_pct = round((road[rd_last] / road[rd_low] - 1) * 100)
    regained = round((road[rd_last] - road[rd_low])
                     / (road[rd_peak] - road[rd_low]) * 100)
    match = min((y for y in road if rd_peak < y < rd_low),
                key=lambda y: abs(road[y] - road[rd_last]))
    need(abs(road[match] - road[rd_last]) < 0.3,
         "no year of the fall matches the last road rate any more")
    w_r_last = max(who_r)
    need(all(who_r[y] > road[y] for y in who_r if y in road)
         and w_r_last < rd_last and rd_low == w_r_last
         and who_r[rd_peak] - road[rd_peak]
         > who_r[rd_low] - road[rd_low],
         "the WHO road line no longer closes in on the SIM one by the low")

    # -------------------------------------------------------------- lens
    both = set(police) & set(wom) & set(fem)
    l_first, l_last = min(both), max(both)
    need(l_last == full and l_first < 2018, "the lens no longer spans "
         "from before 2018 to the last full year")
    share = lambda y: round(fem[y] / wom[y] * 100)
    need(share(l_last) >= 1.9 * share(l_first)
         and wom[l_last] < wom[l_first] and fem[l_last] > fem[l_first]
         and all(wom[y] > fem[y] for y in both),
         "femicide is no longer about twice its share while the total falls")
    non = {y: wom[y] - fem[y] for y in both}
    need(non[l_last] < wom[l_last] and non[l_last] < non[l_first]
         and (non[l_first] - non[l_last]) > (wom[l_first] - wom[l_last]),
         "the cases without the label no longer fall more than the total")
    p_mid = 2018
    p_after = [police[y] for y in sorted(police) if y >= p_mid]
    need(l_first < p_mid and police[p_mid] > police[l_first]
         and max(p_after) - min(p_after) < 0.3
         and police[l_first] < min(p_after),
         "police deaths no longer rise early and then hold level")
    pgap = lambda y: wom[y] - police[y]
    need(pgap(l_first) > pgap(l_last) > 0,
         "the police and women's lines no longer close in without crossing")

    return {
        "security.homicide": ctx.story(
            title=ctx.text(
                en="In all three counts, the rate never regained its "
                   "{peak_year} peak",
                pt="Nas três contagens, a taxa não voltou ao pico de "
                   "{peak_year}"),
            beats=[
                (ctx.text(en="A {reg_fall}% fall that looks gentle",
                          pt="Uma queda de {reg_fall}% que parece suave"),
                 ctx.text(
                    en="On a log scale each step multiplies the value, so "
                       "big falls look small. Red goes from {reg_peak} in "
                       "{peak_year} to {reg_last} in {reg_last_year}: "
                       "{reg_fall}% lower.",
                    pt="Na escala logarítmica, cada degrau multiplica o "
                       "valor e quedas grandes parecem pequenas. A vermelha "
                       "vai de {reg_peak} em {peak_year} a {reg_last} em "
                       "{reg_last_year}: {reg_fall}% a menos.")),
                (ctx.text(en="In {rcl_year}, blue crosses red",
                          pt="Em {rcl_year}, a azul cruza a vermelha"),
                 ctx.text(
                    en="Up to {prev_year} blue sits below red; from "
                       "{rcl_year} to {reg_last_year}, above. In the marked "
                       "year red falls {reg_fall19}%; blue, another source, "
                       "{mvi_fall19}%.",
                    pt="Até {prev_year} a azul fica abaixo da vermelha; de "
                       "{rcl_year} a {reg_last_year}, acima. No ano marcado "
                       "a vermelha cai {reg_fall19}%; a azul, outra fonte, "
                       "{mvi_fall19}%.")),
                (ctx.text(en="Hidden homicides peak in {rcl_year}",
                          pt="Homicídios ocultos: máximo em {rcl_year}"),
                 ctx.text(
                    en="Dashed adds estimated hidden homicides to red. The "
                       "addition goes from {gap18} per 100,000 in "
                       "{prev_year} to {gap19} in {rcl_year}, the largest "
                       "in the series.",
                    pt="A tracejada soma à vermelha uma estimativa de "
                       "homicídios ocultos. A soma vai de {gap18} por 100 "
                       "mil em {prev_year} a {gap19} em {rcl_year}, a maior "
                       "da série.")),
                (ctx.text(en="Blue's last point has an extra year",
                          pt="A azul tem um ano a mais"),
                 ctx.text(
                    en="In {mvi_last_year} blue ({mvi_last}) looks below "
                       "red, which ends in {reg_last_year}. But in "
                       "{reg_last_year} blue is {mvi_at_reg} and red "
                       "{reg_last}.",
                    pt="Em {mvi_last_year} a azul ({mvi_last}) parece "
                       "abaixo da vermelha, que termina em {reg_last_year}. "
                       "Mas em {reg_last_year} a azul é {mvi_at_reg} e a "
                       "vermelha, {reg_last}.")),
            ],
            facts={"peak": at(peak),
                   "reg_peak": val(reg[peak], "dec1", year=peak),
                   "reg_last": val(reg[r_last], "dec1", year=r_last),
                   "reg_fall": val(reg_fall, "count"),
                   "rcl": at(rcl), "prev": at(prev),
                   "reg_fall19": val(fall(reg), "count"),
                   "mvi_fall19": val(fall(mvi), "count"),
                   "gap18": val(gap[prev], "dec1", year=prev),
                   "gap19": val(gap[rcl], "dec1", year=rcl),
                   "mvi_last": val(mvi[m_last], "dec1", year=m_last),
                   "mvi_at_reg": val(mvi[r_last], "dec1", year=r_last)}),
        "security.suicide": ctx.story(
            title=ctx.text(
                en="The suicide rate rose {rise}% from {s_first_year} to "
                   "{s_last_year}",
                pt="A taxa de suicídio subiu {rise}% de {s_first_year} a "
                   "{s_last_year}"),
            beats=[
                (ctx.text(en="Peak in {s_peak_year}, not at the end",
                          pt="Pico em {s_peak_year}, não no fim"),
                 ctx.text(
                    en="The top note compares the first and last years. The "
                       "rate hit {s_peak} in {s_peak_year} and has since "
                       "receded {back}%, to {s_last} in {s_last_year}.",
                    pt="A nota do topo compara o primeiro e o último ano. A "
                       "taxa chegou a {s_peak} em {s_peak_year} e recuou "
                       "{back}% desde então, para {s_last} em "
                       "{s_last_year}.")),
                (ctx.text(en="It rose in {ups} of {steps} years",
                          pt="Subiu em {ups} de {steps} anos"),
                 ctx.text(
                    en="Only {d1_year}, {d2_year}, {d3_year} and {d4_year} saw no rise. The "
                       "climb is steady, not one isolated leap.",
                    pt="Só {d1_year}, {d2_year}, {d3_year} e {d4_year} não tiveram alta. A "
                       "subida é constante, não um salto isolado.")),
                (ctx.text(en="The biggest leap came in {j_year}",
                          pt="O maior salto foi em {j_year}"),
                 ctx.text(
                    en="The rate rose {jump}% in {j_year}, the largest "
                       "one-year rise, right after the 2020 band. The chart "
                       "shows the dates side by side, not a link.",
                    pt="A taxa subiu {jump}% em {j_year}, a maior alta em "
                       "um ano, logo depois da faixa de 2020. O gráfico "
                       "mostra as datas lado a lado, não uma ligação.")),
                (ctx.text(en="Age-adjusted, the rise is smaller",
                          pt="Ajustada por idade, a alta é menor"),
                 ctx.text(
                    en="From {s_first_year} to {w_last_year}, the crude rate "
                       "rose {raw_rise}%; the WHO one, age-adjusted and from "
                       "another source, {who_rise}%. Grey stops in "
                       "{w_last_year}.",
                    pt="De {s_first_year} a {w_last_year}, a taxa bruta "
                       "subiu {raw_rise}%; a da OMS, ajustada por idade e de "
                       "outra fonte, {who_rise}%. A cinza para em "
                       "{w_last_year}.")),
            ],
            facts={"rise": val(rise, "count"),
                   "s_first": at(s_first),
                   "s_last": val(suicide[s_last], "dec1", year=s_last),
                   "s_peak": val(suicide[s_peak], "dec1", year=s_peak),
                   "back": val(back, "count"),
                   "ups": val(len(ups), "count"),
                   "steps": val(len(steps), "count"),
                   "d1": at(downs[0]), "d2": at(downs[1]),
                   "d3": at(downs[2]), "d4": at(downs[3]),
                   "j": at(j_year),
                   "jump": val(round(jump[j_year] * 100), "count",
                               year=j_year),
                   "raw_rise": val(raw_rise, "count"),
                   "who_rise": val(who_rise, "count"),
                   "w_last": at(w_last)}),
        "security.road_deaths": ctx.story(
            title=ctx.text(
                en="Road deaths fell until {rd_low_year} and then rose "
                   "again",
                pt="Mortes no trânsito caíram até {rd_low_year} e voltaram "
                   "a subir"),
            beats=[
                (ctx.text(en="The fall exceeds the note's",
                          pt="A queda supera a da nota"),
                 ctx.text(
                    en="The note shows {rd_peak} to {rd_last}, {note_pct}% "
                       "lower. The low, {rd_low} in {rd_low_year}, is "
                       "{fall_pct}% below the {rd_peak_year} peak.",
                    pt="A nota mostra {rd_peak} para {rd_last}, {note_pct}% "
                       "a menos. O fundo, {rd_low} em {rd_low_year}, fica "
                       "{fall_pct}% abaixo do pico de {rd_peak_year}.")),
                (ctx.text(en="Back to the {rd_match_year} level",
                          pt="De volta ao nível de {rd_match_year}"),
                 ctx.text(
                    en="At {rd_last} in {rd_last_year}, the rate is near the "
                       "{rd_match} of {rd_match_year}. The rise from the low, "
                       "{rise_pct}%, recovered {regained}% of the earlier "
                       "fall.",
                    pt="Com {rd_last} em {rd_last_year}, a taxa está perto "
                       "dos {rd_match} de {rd_match_year}. A alta desde o "
                       "fundo, {rise_pct}%, recuperou {regained}% da queda "
                       "anterior.")),
                (ctx.text(en="The WHO line closes in, then stops",
                          pt="A OMS se aproxima e para"),
                 ctx.text(
                    en="The gap between grey and yellow shrinks from "
                       "{gap_peak} in {rd_peak_year} to {gap_low} in "
                       "{rd_low_year}. Grey ends there, so it cannot check "
                       "the recent rise.",
                    pt="A distância entre a cinza e a amarela cai de "
                       "{gap_peak} em {rd_peak_year} para {gap_low} em "
                       "{rd_low_year}. A cinza termina aí, então não "
                       "confere a alta recente.")),
            ],
            facts={"rd_peak": val(road[rd_peak], "dec1", year=rd_peak),
                   "rd_low": val(road[rd_low], "dec1", year=rd_low),
                   "rd_last": val(road[rd_last], "dec1", year=rd_last),
                   "note_pct": val(note_pct, "count"),
                   "fall_pct": val(fall_pct, "count"),
                   "rise_pct": val(rise_pct, "count"),
                   "regained": val(regained, "count"),
                   "rd_match": val(road[match], "dec1", year=match),
                   "gap_peak": val(who_r[rd_peak] - road[rd_peak], "dec1",
                                   year=rd_peak),
                   "gap_low": val(who_r[rd_low] - road[rd_low], "dec1",
                                  year=rd_low)}),
        "security.lens": ctx.story(
            title=ctx.text(
                en="Women's homicides fall; police-intervention deaths "
                   "level off",
                pt="Homicídio de mulheres cai; intervenção policial "
                   "estabiliza"),
            beats=[
                (ctx.text(en="Femicide: from {share_first}% to "
                             "{share_last}% of total",
                          pt="Feminicídio: de {share_first}% a "
                             "{share_last}% do total"),
                 ctx.text(
                    en="Of women's homicides, {share_first}% were classed as "
                       "femicide in {l_first_year}; in {l_last_year}, "
                       "{share_last}%. The chart's note says much of this "
                       "rise is classification.",
                    pt="Dos homicídios de mulheres, {share_first}% eram "
                       "classificados como feminicídio em {l_first_year}; "
                       "em {l_last_year}, {share_last}%. A nota do gráfico "
                       "diz que boa parte dessa alta é classificação.")),
                (ctx.text(en="Total does not depend on the label",
                          pt="O total não depende da etiqueta"),
                 ctx.text(
                    en="All women's homicides go from {wom_first} to "
                       "{wom_last} per 100,000 women. The grey band, cases "
                       "without the label, falls more in points: {non_first} to "
                       "{non_last}.",
                    pt="Todos os homicídios de mulheres vão de {wom_first} "
                       "a {wom_last} por 100 mil mulheres. A faixa cinza, "
                       "casos sem a etiqueta, cai mais em pontos: de {non_first} a "
                       "{non_last}.")),
                (ctx.text(en="Police: a rise, then a plateau",
                          pt="Polícia: uma subida e depois um patamar"),
                 ctx.text(
                    en="Deaths from police intervention go from {p_first} "
                       "in {l_first_year} to {p_mid} in {p_mid_year}, then "
                       "stay between {p_min} and {p_max}. The panel shows "
                       "nothing before {l_first_year}.",
                    pt="As mortes por intervenção policial vão de "
                       "{p_first} em {l_first_year} a {p_mid} em "
                       "{p_mid_year}, e ficam entre {p_min} e {p_max}. O "
                       "painel não mostra nada antes de {l_first_year}.")),
                (ctx.text(en="Purple and black use different bases",
                          pt="Roxa e preta têm bases diferentes"),
                 ctx.text(
                    en="Purple is per 100,000 people; black, per 100,000 "
                       "women. They close from {gap_first} apart to "
                       "{gap_last}, but they measure different groups.",
                    pt="A roxa é por 100 mil habitantes; a preta, por 100 "
                       "mil mulheres. Elas se aproximam de {gap_first} para "
                       "{gap_last}, mas medem grupos diferentes.")),
            ],
            facts={"l_first": at(l_first), "l_last": at(l_last),
                   "share_first": val(share(l_first), "count"),
                   "share_last": val(share(l_last), "count"),
                   "wom_first": val(wom[l_first], "dec2", year=l_first),
                   "wom_last": val(wom[l_last], "dec2", year=l_last),
                   "non_first": val(non[l_first], "dec2", year=l_first),
                   "non_last": val(non[l_last], "dec2", year=l_last),
                   "p_first": val(police[l_first], "dec2", year=l_first),
                   "p_mid": val(police[p_mid], "dec2", year=p_mid),
                   "p_min": val(min(p_after), "dec2"),
                   "p_max": val(max(p_after), "dec2"),
                   "gap_first": val(pgap(l_first), "dec2", year=l_first),
                   "gap_last": val(pgap(l_last), "dec2", year=l_last)}),
    }


def mortality_stories(ctx) -> dict:
    """Insights for the four panels of the mortality plate (11_epidemics)."""
    from core import rates

    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil mortality stories: {why}; rewrite the "
                             f"copy that depends on it")

    registered = dict(ctx.col("social/deaths.csv", "registered"))
    model = dict(ctx.col("social/population.csv", "deaths"))
    pop = {y: v * 1e6 for y, v in ctx.col("social/population.csv", "pop_mn")}
    covid_n = dict(ctx.col("social/epidemic_deaths.csv", "covid"))
    flu_n = dict(ctx.col("social/epidemic_deaths.csv", "influenza"))
    dengue_n = dict(ctx.col("social/epidemic_deaths.csv", "dengue"))
    first = ctx.c.years[0]

    def per(count, base, lo=first, hi=None):
        hi = full if hi is None else hi
        ys, vs = rates.per(
            {y: v for y, v in count.items() if lo <= y <= hi}, pop, base)
        return dict(zip(ys, vs))

    pre = 2019
    rate = per(registered, 1e3)
    mrate = per(model, 1e3, hi=2024)
    m_end = max(mrate)
    top = max(rate, key=rate.get)
    after = {y: v for y, v in rate.items() if y > top}
    low = min(after, key=after.get)

    # ------------------------------------------------ panel 1: death rate
    need(top > pre and top == 2021, "the highest death rate is not 2021")
    need(rate[top] - rate[pre] > 2 * (rate[pre] - rate[first]) > 0,
         "the rise to the peak is no longer more than double the earlier rise")
    need(after and rate[low] > rate[pre],
         "the lowest rate after the peak is no longer above 2019's")
    need(mrate[first] > rate[first] and mrate[pre] > rate[pre]
         and mrate[m_end] < rate[m_end] and m_end < full,
         "the model no longer starts above the registered line and ends below")
    need(mrate[first] - rate[first] > mrate[pre] - rate[pre] > 0,
         "the model-registered gap no longer narrows before 2020")

    death_rate = ctx.story(
        title=ctx.text(
            en="The death rate rose more from {pre_year} to {peak_year} than "
               "in the years before",
            pt="A taxa de mortes subiu mais de {pre_year} a {peak_year} do "
               "que nos anos antes"),
        beats=[
            (ctx.text(en="A short climb outweighs a long one",
                      pt="Subida curta pesa mais que a longa"),
             ctx.text(
                en="From {first_year} to {pre_year} the rate rose {rise_pre} "
                   "per 1,000 people. From {pre_year} to {peak_year} it rose "
                   "{rise_pk}: more than double, in far less time.",
                pt="De {first_year} a {pre_year}, a taxa subiu {rise_pre} por "
                   "mil habitantes. De {pre_year} a {peak_year}, subiu "
                   "{rise_pk}: mais que o dobro, em muito menos tempo.")),
            (ctx.text(en="The floor after the peak is higher",
                      pt="Depois do pico, piso mais alto"),
             ctx.text(
                en="The lowest rate since {peak_year} is {low} in "
                   "{low_year}, still above the {r_pre} of {pre_year}. An "
                   "ageing population lifts a crude rate alone, and this "
                   "chart cannot separate the two.",
                pt="A menor taxa desde {peak_year} é {low}, em {low_year}, "
                   "ainda acima dos {r_pre} de {pre_year}. Uma população que "
                   "envelhece eleva sozinha a taxa bruta, e o gráfico não "
                   "separa as duas coisas.")),
            (ctx.text(en="The model line crosses the registry",
                      pt="A linha do modelo cruza o registro"),
             ctx.text(
                en="The IBGE model sat {gap_first} per 1,000 above the "
                   "registered deaths in {first_year}, {gap_pre} in "
                   "{pre_year}. In {m_end_year} it is below: {m_end} "
                   "against {r_end}.",
                pt="O modelo do IBGE ficava {gap_first} por mil acima dos "
                   "óbitos registrados em {first_year}, e {gap_pre} em "
                   "{pre_year}. Em {m_end_year} está abaixo: {m_end} contra "
                   "{r_end}.")),
        ],
        facts={"first": val(rate[first], "dec1", year=first),
               "pre": val(rate[pre], "dec1", year=pre),
               "peak": val(rate[top], "dec1", year=top),
               "rise_pre": val(rate[pre] - rate[first], "dec1", year=pre),
               "rise_pk": val(rate[top] - rate[pre], "dec1", year=top),
               "low": val(rate[low], "dec1", year=low),
               "r_pre": val(rate[pre], "dec1", year=pre),
               "gap_first": val(mrate[first] - rate[first], "dec2",
                                year=first),
               "gap_pre": val(mrate[pre] - rate[pre], "dec2", year=pre),
               "m_end": val(mrate[m_end], "dec1", year=m_end),
               "r_end": val(rate[m_end], "dec1", year=m_end)})

    # ------------------------------------------------ panel 2: excess
    window = range(2015, 2020)
    base = sum(registered[y] for y in window) / 5
    exc = {y: (v / base - 1) * 100 for y, v in registered.items() if y >= 2015}
    aft = list(range(2020, full + 1))
    cum = sum(registered[y] - base for y in aft)
    pk = max(exc, key=exc.get)
    lo_y = min(aft, key=lambda y: exc[y])
    need(all(exc[y] > 0 for y in aft), "a year since 2020 is not above average")
    need(pk == 2021, "the highest excess is not 2021")
    need(cum > base, "the cumulative excess is no longer above one typical year")
    need(registered[pk] - base > cum / 4,
         "the peak year no longer carries a quarter of the cumulative excess")
    need(exc[2015] < 0 < exc[pre] and exc[pre] > exc[2015] + 5,
         "the baseline years no longer drift upward")
    need(lo_y not in (2020, 2021) and exc[lo_y] > 5,
         "the lowest post-2020 excess is not a later year above +5%")
    need(abs(exc[full] - exc[2020]) < 3,
         "the latest excess is no longer near 2020's")

    excess_deaths = ctx.story(
        title=ctx.text(
            en="No year since 2020 has returned to the 2015–19 average",
            pt="Nenhum ano desde 2020 voltou à média de 2015–19"),
        beats=[
            (ctx.text(en="{cum} million deaths above the average",
                      pt="{cum} milhão de óbitos acima da média"),
             ctx.text(
                en="From 2020 to {last_year}, each year's gap to the 2015–19 "
                   "average sums to {cum} million: more than one whole "
                   "typical year ({base}). {pk_year} alone adds "
                   "{pk_n} thousand.",
                pt="De 2020 a {last_year}, a soma da diferença de cada ano "
                   "para a média de 2015–19 é {cum} milhão: mais que um ano "
                   "típico inteiro ({base}). Só {pk_year} soma "
                   "{pk_n} mil.")),
            (ctx.text(en="The ruler was already drifting up",
                      pt="A régua já subia antes de 2020"),
             ctx.text(
                en="With no pandemic, the bars go from 2015 ({e15}) to "
                   "2019 ({e19}). Ageing and growth lift the count by "
                   "themselves, and the chart does not separate that from "
                   "the later bars.",
                pt="Sem pandemia, as barras vão de 2015 ({e15}) a 2019 "
                   "({e19}). Envelhecimento e crescimento elevam a "
                   "contagem sozinhos, e o gráfico não separa isso das "
                   "barras seguintes.")),
            (ctx.text(en="Floor since 2020: {low}",
                      pt="Piso desde 2020: {low}"),
             ctx.text(
                en="The closest to the average was {low_year}, at {low}. "
                   "{last_year}, a preliminary year, is {last}, close to "
                   "the {e20} of 2020.",
                pt="O mais perto da média foi {low_year}, com {low}. "
                   "{last_year}, ano preliminar, marca {last}, perto dos "
                   "{e20} de 2020.")),
        ],
        facts={"cum": val(cum / 1e6, "dec1"),
               "base": val(base, "count", year=2019),
               "pk_n": val((registered[pk] - base) / 1e3, "count", year=pk),
               "pk": val(0, "count", year=pk),
               "e15": val(exc[2015], "pct_s", year=2015),
               "e19": val(exc[pre], "pct_s", year=pre),
               "e20": val(exc[2020], "pct_s", year=2020),
               "low": val(exc[lo_y], "pct_s", year=lo_y),
               "last": val(exc[full], "pct_s")})

    # ------------------------------------------------ panel 3: COVID-19
    cv = {y: v for y, v in covid_n.items() if y >= 2020}
    cr = per(cv, 1e5, lo=2020)
    cpk = max(cr, key=cr.get)
    tot = sum(cv[y] for y in range(2020, full + 1))
    two = cv[2020] + cv[2021]
    both = sum(registered[y] - base for y in (2020, 2021))
    need(min(cv) == 2020 and cpk == 2021, "the COVID-19 peak is not 2021")
    need(two / tot > 0.8, "2020-21 no longer carry over 80% of the deaths")
    need(all(cr[y + 1] < cr[y] for y in range(cpk, full)),
         "COVID-19 no longer falls every year after the peak")
    need(cr[full] < 2 and cr[cpk + 1] < cr[cpk] / 5,
         "the fall after the peak is no longer steep")
    need(both > two, "the 2020-21 excess is no longer above the COVID-19 count")

    covid = ctx.story(
        title=ctx.text(
            en="COVID-19 was packed into 2020–21, then nearly vanished",
            pt="A covid se concentrou em 2020–21 e depois quase sumiu"),
        beats=[
            (ctx.text(en="Two years hold {share} of the deaths",
                      pt="Dois anos guardam {share} das mortes"),
             ctx.text(
                en="From 2020 to {tot_year}, {tot} deaths had COVID-19 as "
                   "the underlying cause. {two} of them are in 2020 and 2021.",
                pt="De 2020 a {tot_year}, {tot} óbitos tiveram a covid como "
                   "causa básica. {two} deles estão em 2020 e 2021.")),
            (ctx.text(en="In {c_pk_year}, {perday} deaths a day",
                      pt="Em {c_pk_year}, {perday} mortes por dia"),
             ctx.text(
                en="The {c_pk} per 100,000 of the tallest bar equals {n_pk} "
                   "deaths: {perday} a day, averaged over the whole year.",
                pt="Os {c_pk} por 100 mil da barra mais alta equivalem a "
                   "{n_pk} óbitos: {perday} por dia, na média do ano "
                   "inteiro.")),
            (ctx.text(en="Down {drop} times in one year",
                      pt="Queda de {drop} vezes em um ano"),
             ctx.text(
                en="{c_a} per 100,000 in 2022, {drop} times less than in "
                   "{c_pk_year}. By {c_last_year}: {c_last}.",
                pt="{c_a} por 100 mil em 2022, {drop} vezes menos que em "
                   "{c_pk_year}. Em {c_last_year}: {c_last}.")),
            (ctx.text(en="It counts one cause, not all the excess",
                      pt="Conta uma causa, não todo o excesso"),
             ctx.text(
                en="The excess panel sums {ex2} deaths above average in "
                   "2020–21; here, {two}. The two measures do not say what "
                   "the other deaths were. Before 2020 the code included "
                   "other viruses.",
                pt="O painel de excesso soma {ex2} óbitos acima da média em "
                   "2020–21; aqui, {two}. As duas medidas não dizem de que "
                   "morreram os demais. Antes de 2020, o código incluía "
                   "outras viroses.")),
        ],
        facts={"share": val(two / tot * 100, "pct", year=2021),
               "tot": val(tot, "count"),
               "two": val(two, "count", year=2021),
               "perday": val(cv[cpk] / 365, "count", year=cpk),
               "c_pk": val(cr[cpk], "count", year=cpk),
               "n_pk": val(cv[cpk], "count", year=cpk),
               "drop": val(cr[cpk] / cr[cpk + 1], "dec1", year=cpk + 1),
               "c_a": val(cr[cpk + 1], "count", year=cpk + 1),
               "c_last": val(cr[full], "dec1"),
               "ex2": val(both, "count", year=2021)})

    # ------------------------------------------------ panel 4: lens
    fl = per(flu_n, 1e5)
    dg = per(dengue_n, 1e5)
    h1 = 2009
    dpk = max(dg, key=dg.get)
    fpk = max(fl, key=fl.get)
    need(fl[h1] > 5 * fl[h1 - 1] and fl[h1] > fl[h1 + 1],
         "H1N1 is no longer a one-year spike")
    need(fpk == full and fl[full] > 2 * fl[h1],
         "the latest influenza reading is no longer over twice the H1N1 peak")
    need(dpk == full - 1 and dg[dpk] > 4 * dg[dpk - 1] and dg[full] < dg[dpk],
         "dengue is no longer a record the year before the last, above 4x")
    need(full == 2025, "the dengue code change the plate notes is dated 2025")
    need(cr[cpk] > 50 * dg[dpk], "COVID-19 is no longer over 50x dengue's peak")

    lens = ctx.story(
        title=ctx.text(
            en="Flu and dengue peaks are small next to COVID-19's",
            pt="Os picos de gripe e dengue são pequenos perto da covid"),
        beats=[
            (ctx.text(en="Today's flu passes the H1N1 peak",
                      pt="Gripe de hoje passa o pico do H1N1"),
             ctx.text(
                en="The dashed line marks H1N1: {fl_h1} per 100,000 in "
                   "{fl_h1_year}, {x_h1} times the year before. {fl_last_year}, "
                   "preliminary, reads {fl_last}: more than double.",
                pt="A linha tracejada marca o H1N1: {fl_h1} por 100 mil em "
                   "{fl_h1_year}, {x_h1} vezes o ano anterior. {fl_last_year}, "
                   "preliminar, marca {fl_last}: mais que o dobro.")),
            (ctx.text(en="Dengue jumped {x_dg} times in {dg_pk_year}",
                      pt="A dengue saltou {x_dg} vezes em {dg_pk_year}"),
             ctx.text(
                en="{dg_pk} per 100,000 in {dg_pk_year}, against {dg_prev} the "
                   "year before and {dg_last} in {fl_last_year}. The line sums "
                   "the old and the new dengue code, changed in 2025.",
                pt="{dg_pk} por 100 mil em {dg_pk_year}, contra {dg_prev} no "
                   "ano anterior e {dg_last} em {fl_last_year}. A linha soma o "
                   "código antigo e o novo da dengue, trocado em 2025.")),
            (ctx.text(en="COVID-19: {x_cv} times the dengue peak",
                      pt="Covid: {x_cv} vezes o pico da dengue"),
             ctx.text(
                en="COVID-19 reached {c_pk} per 100,000 in {c_pk_year}; the "
                   "dengue record is {dg_pk}. This axis is far smaller than "
                   "the COVID-19 panel's: here the peaks look bigger than "
                   "they are.",
                pt="A covid chegou a {c_pk} por 100 mil em {c_pk_year}; o "
                   "recorde da dengue é {dg_pk}. Este eixo é bem menor que "
                   "o do painel da covid: aqui os picos parecem maiores do "
                   "que são.")),
        ],
        facts={"fl_h1": val(fl[h1], "dec2", year=h1),
               "x_h1": val(fl[h1] / fl[h1 - 1], "count", year=h1),
               "fl_last": val(fl[full], "dec2"),
               "x_dg": val(dg[dpk] / dg[dpk - 1], "count", year=dpk),
               "dg_pk": val(dg[dpk], "dec2", year=dpk),
               "dg_prev": val(dg[dpk - 1], "dec2", year=dpk - 1),
               "dg_last": val(dg[full], "dec2"),
               "x_cv": val(cr[cpk] / dg[dpk], "count", year=dpk),
               "c_pk": val(cr[cpk], "count", year=cpk)})

    return {"mortality.death_rate": death_rate,
            "mortality.excess_deaths": excess_deaths,
            "mortality.covid": covid,
            "mortality.lens": lens}


def migration_stories(ctx) -> dict:
    """Insights for the three drawn panels of the migration plate (12_migration).

    "migration.flows" is a pending panel (nothing drawn), so it has no story.
    """
    full = ctx.LAST_FULL_YEAR

    def val(value, spec, year=None):
        return ctx.fact([(full if year is None else year, float(value))],
                        spec, year=year)

    def need(ok, why):
        if not ok:
            raise ValueError(f"brasil migration stories: {why}; rewrite the "
                             f"copy that depends on it")

    first = ctx.c.years[0]
    net = dict(ctx.col("social/demography.csv", "net_migration"))
    pop = dict(ctx.col("social/demography.csv", "population"))
    rate = {y: net[y] / pop[y] * 1000 for y in net
            if y in pop and first <= y <= full}
    fb = dict(ctx.col("migration/stock_census.csv", "foreign_born_pct"))
    fc = dict(ctx.col("migration/stock_census.csv", "foreign_citizens_pct"))
    fb_n = dict(ctx.col("migration/stock_census.csv", "foreign_born"))
    fc_n = dict(ctx.col("migration/stock_census.csv", "foreign_citizens"))
    nat = dict(ctx.col("migration/stock_census.csv", "naturalized_brazilians"))
    nbr = dict(ctx.col("migration/stock_census.csv",
                       "native_brazilians_born_abroad"))
    tot = dict(ctx.col("migration/stock_census.csv", "total_population"))
    lat = dict(ctx.col("migration/origins_census.csv", "latin_america_born"))

    # ------------------------------------------------ panel 1: net migration
    need(sorted(rate) == list(range(first, full + 1)),
         "the net-migration series has gaps in the plotted years")
    need(all(v < 0 for v in rate.values()),
         "a year is no longer a net outflow")
    hi = min(rate, key=rate.get)               # deepest outflow
    lo = max(rate, key=rate.get)               # shallowest outflow
    need(lo == 2020 and lo + 1 in rate and rate[lo + 1] < 2 * rate[lo],
         "the shallowest outflow is no longer 2020, or it no longer snaps "
         "back to more than double the next year")
    thr = 1.0
    above = [y for y in sorted(rate) if -rate[y] > thr]
    run, runs = [], []
    for y in sorted(rate):
        if -rate[y] > thr:
            run.append(y)
        else:
            if run:
                runs.append(run)
            run = []
    if run:
        runs.append(run)
    last_run = runs[-1]
    need(last_run[-1] == full and len(last_run) >= 3
         and len(last_run) == max(len(r) for r in runs)
         and len(last_run) < len(above),
         "the latest run of years above 1 per 1,000 is no longer the longest "
         "and unbroken to the last full year")
    l10, l22 = min(lat), max(lat)
    need(len(lat) == 2 and lat[l22] > lat[l10]
         and all(rate[y] < 0 for y in range(l10, l22 + 1)),
         "the two census years are not both covered by an all-negative "
         "net-migration run, or Latin America-born residents no longer rise")

    net_story = ctx.story(
        title=ctx.text(
            en="UN model: more people leave Brazil than arrive, every year",
            pt="Modelo da ONU: todo ano saem mais pessoas do que entram"),
        beats=[
            (ctx.text(en="Not one year above zero",
                      pt="Nenhum ano acima de zero"),
             ctx.text(
                en="In all {n_years} years, {first_year} to {last_year}, more "
                   "people leave than arrive: a surplus of departures "
                   "between {mild} and {deep} per 1,000 residents.",
                pt="Nos {n_years} anos, de {first_year} a {last_year}, saem "
                   "mais pessoas do que entram: excesso de saídas entre "
                   "{mild} e {deep} por mil habitantes.")),
            (ctx.text(en="The smallest loss was in the COVID band",
                      pt="Menor perda: o ano da covid"),
             ctx.text(
                en="{deep_year} lost {deep} per 1,000 ({deep_n} thousand "
                   "people). {mild_year} lost {mild}, {ratio} times less. "
                   "In {back_year} it is {back} again.",
                pt="{deep_year} perdeu {deep} por mil ({deep_n} mil "
                   "pessoas). {mild_year} perdeu {mild}, {ratio} vezes "
                   "menos. Em {back_year} volta a {back}.")),
            (ctx.text(en="The longest streak is the latest",
                      pt="A maior sequência é a mais recente"),
             ctx.text(
                en="{streak} years in a row, {streak_from_year} to "
                   "{last_year}, lose more than {one} per 1,000. Of the "
                   "{n_years}, {n_over} pass that line.",
                pt="{streak} anos seguidos, de {streak_from_year} a "
                   "{last_year}, perdem mais de {one} por mil. Dos "
                   "{n_years}, {n_over} passam dessa linha.")),
            (ctx.text(en="A negative balance is not zero arrivals",
                      pt="Saldo negativo não é zero chegadas"),
             ctx.text(
                en="The line is arrivals minus departures. The census still "
                   "counts {la22} thousand residents born in Latin America "
                   "in {la22_year}, up from {la10} thousand in {la10_year}.",
                pt="A linha é chegadas menos saídas. O censo ainda conta "
                   "{la22} mil residentes nascidos na América Latina em "
                   "{la22_year}, contra {la10} mil em {la10_year}.")),
        ],
        facts={"n_years": val(len(rate), "count"),
               "last": val(0, "count"),
               "deep": val(-rate[hi], "dec2", year=hi),
               "mild": val(-rate[lo], "dec2", year=lo),
               "deep_n": val(-net[hi] / 1e3, "count", year=hi),
               "ratio": val(rate[hi] / rate[lo], "dec1", year=lo),
               "back": val(-rate[lo + 1], "dec2", year=lo + 1),
               "first": val(0, "count", year=first),
               "streak": val(len(last_run), "count"),
               "streak_from": val(0, "count", year=last_run[0]),
               "one": val(thr, "count"),
               "n_over": val(len(above), "count"),
               "la22": val(lat[l22] / 1e3, "count", year=l22),
               "la10": val(lat[l10] / 1e3, "count", year=l10)})

    # ------------------------------------------------ panel 2: foreign-born
    y = max(fb)
    need(len(fb) == 1 and len(fc) == 1 and set(fb) == set(fc) == set(fb_n),
         "the stock is no longer a single census point")
    need(fb_n[y] - fc_n[y] == nat[y] + nbr[y] > 0,
         "born abroad minus foreign citizens no longer equals naturalized "
         "plus Brazilians by birth born abroad")
    need(fb[y] > fc[y] and nat[y] > nbr[y],
         "the born-abroad share is no longer above the foreign-citizen one, "
         "or naturalized no longer outnumber Brazilians by birth")
    need(0.2 < (nat[y] + nbr[y]) / fb_n[y] < 0.3,
         "the Brazilian-citizen share of those born abroad is no longer "
         "near a quarter")
    need(1e6 <= fb_n[y] < 2e6,
         "born abroad is no longer between one and two million (the copy "
         "says 'milhão' in the singular)")
    gap = nat[y] + nbr[y]

    born_story = ctx.story(
        title=ctx.text(
            en="{share} of residents born abroad are Brazilian citizens",
            pt="{share} dos nascidos fora são cidadãos brasileiros"),
        beats=[
            (ctx.text(en="The gap between the lines is Brazilians",
                      pt="O vão entre as linhas: brasileiros"),
             ctx.text(
                en="Born abroad ({fb}) minus foreign citizens ({fc}) leaves "
                   "{gap} thousand people: {nat} thousand naturalized, "
                   "{nbr} thousand Brazilian by birth.",
                pt="Nascidos fora ({fb}) menos cidadãos estrangeiros ({fc}) "
                   "deixa {gap} mil pessoas: {nat} mil naturalizadas, "
                   "{nbr} mil brasileiras de nascença.")),
            (ctx.text(en="One resident in {inv}",
                      pt="Um residente em cada {inv}"),
             ctx.text(
                en="{fbn} million people were born abroad: {fb} of the "
                   "{pop} million residents counted in the {fb_year} census.",
                pt="{fbn} milhão de pessoas nasceu fora: {fb} dos {pop} "
                   "milhões de residentes contados no censo de {fb_year}.")),
            (ctx.text(en="One census, no direction yet",
                      pt="Um censo só, sem direção ainda"),
             ctx.text(
                en="Both lines are a single {fb_year} point, so this panel "
                   "cannot say whether {fb} is more or less than before. "
                   "Only the next panel looks at 2010, and only Latin America.",
                pt="Duas linhas, um único ponto de {fb_year}: não dá para "
                   "saber se {fb} é mais ou menos que antes. Só o próximo "
                   "painel olha 2010, e só a América Latina.")),
        ],
        facts={"share": val(gap / fb_n[y] * 100, "pct", year=y),
               "fb": val(fb[y], "pct2", year=y),
               "fc": val(fc[y], "pct2", year=y),
               "gap": val(gap / 1e3, "count", year=y),
               "nat": val(nat[y] / 1e3, "count", year=y),
               "nbr": val(nbr[y] / 1e3, "count", year=y),
               "inv": val(100 / fb[y], "count", year=y),
               "fbn": val(fb_n[y] / 1e6, "dec2", year=y),
               "pop": val(tot[y] / 1e6, "dec1", year=y)})

    # ------------------------------------------------ panel 3: Latin America
    need(len(lat) == 2 and lat[l22] / lat[l10] > 3,
         "Latin America-born residents no longer more than triple")

    lens_story = ctx.story(
        title=ctx.text(
            en="Born in Latin America: {x} times the {la10_year} total",
            pt="Nascidos na América Latina: {x} vezes o total de {la10_year}"),
        beats=[
            (ctx.text(en="{add} thousand more residents",
                      pt="{add} mil residentes a mais"),
             ctx.text(
                en="From {la10} thousand in {la10_year} to {la22} thousand "
                   "in {la22_year}: the extra {add} thousand is more than "
                   "double the {la10_year} total.",
                pt="De {la10} mil em {la10_year} a {la22} mil em "
                   "{la22_year}: os {add} mil a mais são mais que o dobro "
                   "do total de {la10_year}.")),
            (ctx.text(en="The water level, not the tap",
                      pt="O nível da água, não a torneira"),
             ctx.text(
                en="Bars count who lives here on census day. The rise is "
                   "not {add} thousand arrivals: people who left or died "
                   "between censuses are no longer in the count.",
                pt="As barras contam quem mora aqui no dia do censo. A alta "
                   "não é de {add} mil chegadas: quem saiu ou morreu entre "
                   "os censos não está mais na conta.")),
            (ctx.text(en="Two photos, {span} years apart",
                      pt="Duas fotos, {span} anos de distância"),
             ctx.text(
                en="Nothing between {la10_year} and {la22_year} is drawn. "
                   "Steady growth and a late jump would look the same, "
                   "and other birthplaces are not in this panel.",
                pt="Nada entre {la10_year} e {la22_year} aparece. "
                   "Crescimento constante e salto tardio ficariam iguais, "
                   "e outros países de nascimento não entram neste "
                   "painel.")),
        ],
        facts={"x": val(lat[l22] / lat[l10], "dec1", year=l22),
               "la10": val(lat[l10] / 1e3, "count", year=l10),
               "la22": val(lat[l22] / 1e3, "count", year=l22),
               "add": val((lat[l22] - lat[l10]) / 1e3, "count", year=l22),
               "span": val(l22 - l10, "count", year=l22)})

    return {"migration.net": net_story,
            "migration.foreign_born": born_story,
            "migration.lens": lens_story}
