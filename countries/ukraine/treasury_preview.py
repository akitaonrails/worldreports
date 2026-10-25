#!/usr/bin/env python3
"""Review-only national Treasury chart, NOT a canonical comparison plate.

Uses reviewed local Ukraine CSV only. The fiscal spine has no slot for
nominal Ukrainian Treasury cash expenditures; do not substitute these values
for general-government accrual or COFOG. Produce SVG previews for source QA
without registering a misleading fifth comparison chapter.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "data" / "fiscal" / "treasury_functional.csv"
TEXT = {
    "en": (
        "Ukraine — consolidated Treasury expenditure",
        "Nominal cash-budget outturn, calendar years 2011–2025",
        "UAH billion • functional classification",
        "Defence", "All other functions", "Defence share of functional total (%)",
        "National Treasury classification; NOT IMF general-government accrual or COFOG",
        "Source: State Treasury via NBU budget API; MoF Budget of Ukraine 2024, §2.3",
        "2025: MoF annual matches NBU; earlier December edition was UAH 6.92bn lower.",
    ),
    "uk": (
        "Україна — видатки зведеного бюджету",
        "Касове виконання в поточних цінах, 2011–2025 рр.",
        "млрд грн • функціональна класифікація",
        "Оборона", "Інші функції", "Частка оборони у видатках (%)",
        "Національна класифікація Казначейства; НЕ облік за МВФ чи COFOG",
        "Джерело: Казначейство через API НБУ; Мінфін, Бюджет України 2024, §2.3",
        "2025: річний звіт Мінфіну підтверджує НБУ; груднева редакція менша на 6,92 млрд грн.",
    ),
    "pt": (
        "Ucrânia — despesas do orçamento consolidado",
        "Execução de caixa nominal, anos civis de 2011 a 2025",
        "UAH bilhões • classificação funcional",
        "Defesa", "Outras funções", "Participação da defesa no total (%)",
        "Classificação nacional do Tesouro; NÃO são contas de competência do FMI/COFOG",
        "Fonte: Tesouro via API do NBU; Min. das Finanças, Budget of Ukraine 2024, §2.3",
        "2025: relatório anual do Ministério confirma o NBU; dezembro anterior era UAH 6,92 bi menor.",
    ),
}


def read_series():
    with CSV.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 15:
        raise ValueError("Curated annual window is not complete")
    years, defence, others, shares = [], [], [], []
    for expected, r in zip(range(2011, 2026), rows, strict=True):
        year = int(r["year"])
        if year != expected or r["source_dt"] != f"{year+1}0101":
            raise ValueError(f"Incorrect fiscal-year convention at {year}")
        total = Decimal(r["total_million_uah"])
        armed = Decimal(r["defence_million_uah"])
        if not (0 <= armed <= total):
            raise ValueError("Defence exceeds published Treasury functional total")
        years.append(year)
        defence.append(float(armed / Decimal(1000)))
        others.append(float((total - armed) / Decimal(1000)))
        shares.append(float(armed / total * Decimal(100)))
    return years, defence, others, shares


def render(out: Path, locale: str):
    title, sub, ylab, de, rest, share, caveat, source, unresolved = TEXT[locale]
    years, defence, others, shares = read_series()
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 8.5), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1]})
    fig.patch.set_facecolor("#FFFFFF")
    ax, bx = axes
    ax.stackplot(years, defence, others,
                 labels=(de, rest), colors=("#326D9C", "#C7D7E1"), alpha=0.95)
    ax.set_ylabel(ylab)
    ax.set_xlim(2011, 2025)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left", frameon=False, ncol=2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    bx.plot(years, shares, marker="o", ms=3, lw=2.0, color="#B07322")
    bx.set_ylim(0, 100)
    bx.set_yticks([0, 25, 50, 75, 100])
    bx.set_ylabel(share)
    bx.set_xticks(list(range(2011, 2026, 2)))
    for a in axes:
        a.grid(axis="y", alpha=0.22)
        a.spines["top"].set_visible(False)
        a.spines["right"].set_visible(False)
    fig.suptitle(title, fontsize=16, fontweight="bold")
    ax.set_title(sub, fontsize=10, loc="left")
    fig.text(0.09, 0.065, caveat, fontsize=8.3)
    fig.text(0.09, 0.043, source, fontsize=7.8)
    fig.text(0.09, 0.021, unresolved, fontsize=8.2)
    fig.subplots_adjust(top=0.86, bottom=0.18, left=0.12, right=0.96, hspace=0.18)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True,
                    help="Directory for review-only SVGs; not a site build input")
    args = ap.parse_args()
    for locale in ("uk", "en", "pt"):
        render(args.output / f"ukraine-treasury-national-review.{locale}.svg", locale)


if __name__ == "__main__":
    main()
