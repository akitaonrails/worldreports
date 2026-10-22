"""The country registry, and the boundary that keeps countries apart.

Every country in this atlas was once its own repository, and the one thing
that must survive the merge is that a plate about Brazil can only ever read
Brazilian numbers. Nothing here is advisory: a country's data, its catalogs
and its output directory are reachable only through the `Country` it belongs
to, and every path is resolved against that country's own directory and
checked before it is opened.

    c = Country.load("brasil")
    t = c.table("macro/gdp.csv")      # countries/brasil/data/macro/gdp.csv
    c.table("../france/data/x.csv")   # DataIsolationError

`tests/test_isolation.py` runs every country's full build with the filesystem
instrumented and fails if a single read or write lands outside that country's
directory, so the guarantee is checked rather than remembered.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import yaml

from core import plotting

ROOT = Path(__file__).resolve().parent.parent
COUNTRIES_DIR = ROOT / "countries"


class DataIsolationError(RuntimeError):
    """Raised when a build tries to reach outside its own country."""


class Palette(SimpleNamespace):
    """A country's colours.

    Two kinds of name live here. The semantic slots — ``ink``, ``muted``,
    ``paper``, ``band`` and friends — are what the shared drawing code in
    ``core.style`` and ``core.plotting`` uses, so those must exist for every
    country. On top of them each country keeps the names its own plates were
    written against (``BLUE`` for France, ``GREEN`` for Brazil, ``CELESTE``
    for Argentina), which is why the plate code reads ``p.CELESTE`` and not
    ``p.primary``: the colours stay exactly what they were before the merge.
    """

    #: Slots the shared drawing code depends on.
    REQUIRED = (
        "ink", "muted", "faint", "paper", "card", "grid", "spine", "band",
        "primary", "alert", "series",
    )

    #: Slots the plates refer to in upper case, because that is how they
    #: were written when each country was its own repository. Both
    #: spellings resolve to the same colour, so `p.ink` and `p.INK` cannot
    #: drift apart.
    ALSO_UPPER = ("ink", "muted", "faint", "paper", "card", "grid", "spine",
                  "band", "band_dark", "primary", "alert")

    @classmethod
    def from_config(cls, cfg: dict) -> "Palette":
        missing = [k for k in cls.REQUIRED if k not in cfg]
        if missing:
            raise ValueError(f"palette is missing {', '.join(missing)}")
        cfg = dict(cfg)
        for slot in cls.ALSO_UPPER:
            if slot in cfg:
                cfg.setdefault(slot.upper(), cfg[slot])
        return cls(**cfg)

    def cycle(self, i: int) -> str:
        """The i-th series colour, wrapping — so a panel cannot run out."""
        return self.series[i % len(self.series)]


@dataclass(frozen=True)
class Locale:
    """One language a country publishes in."""

    code: str           # ISO 639-1, the directory name: pt, en, fr, es, ko
    html_lang: str      # what goes in <html lang="...">: pt-BR, en, ko
    og_locale: str      # Open Graph wants the underscored form: pt_BR
    endonym: str        # the language's name in itself, for the switcher


def within(base: Path, rel: str, slug: str = "") -> Path:
    """Resolve `rel` under `base`, refusing anything that escapes it.

    This is the boundary the whole monorepo rests on: five countries in one
    repository, and nothing that draws one country's plate may read
    another country's numbers. Checked after resolution rather than by
    inspecting the string, so a symlink, a `..` segment and an absolute
    path are all caught by the same test.

    It is a module function and not only a method because a country may
    keep its own CSV reader — Argentina does — and that reader has to pass
    through the same door rather than reimplement the check beside it.
    """
    base = Path(base).resolve()
    who = f"{slug}: " if slug else ""
    if Path(rel).is_absolute():
        raise DataIsolationError(
            f"{who}absolute path {rel!r} — country data is addressed "
            f"relative to its own directory")
    target = (base / rel).resolve()
    if target != base and base not in target.parents:
        raise DataIsolationError(
            f"{who}{rel!r} resolves to {target}, outside {base}. "
            f"A plate may only read its own country's data.")
    return target


@dataclass(frozen=True)
class Country:
    """One country's identity, data and output location."""

    slug: str                     # the URL segment and directory name
    name: dict                    # display name per locale
    wordmark: str                 # the masthead word
    flag_emoji: str
    locales: tuple                # Locale objects, publication order
    default_locale: str
    palette: Palette
    years: tuple                  # the x-axis span every plate shares
    last_full_year: int           # past this, annual totals are partial
    tick_every: int               # label every Nth year on the x-axis
    recessions: tuple             # (start, end, label) bands drawn behind data
    currency: str                 # ISO 4217; the formatting lives in the
                                  # country's own money.py, because the
                                  # thresholds genuinely differ
    seo: dict                     # title, description, keywords, spatial
    sources: dict                 # the institutions named in the dek
    dir: Path = field(repr=False)
    spine: bool = False           # held to PLATE_SPINE.md by test_spine

    # ---------------------------------------------------------- loading
    @staticmethod
    @lru_cache(maxsize=None)
    def load(slug: str) -> "Country":
        d = (COUNTRIES_DIR / slug).resolve()
        if d.parent != COUNTRIES_DIR.resolve() or not d.is_dir():
            raise DataIsolationError(f"no such country: {slug!r}")
        return Country.from_dir(d, slug)

    @staticmethod
    def from_dir(d: Path, slug: str | None = None) -> "Country":
        """A country from its directory's country.yaml.

        `load` is the way in for the atlas: it resolves a slug under
        countries/ and refuses anything else. This is what it calls once
        it has, and what a test uses to build a throwaway country in a
        temporary directory.
        """
        d = Path(d).resolve()
        slug = slug or d.name
        cfg = yaml.safe_load((d / "country.yaml").read_text(encoding="utf-8"))
        if cfg["slug"] != slug:
            raise ValueError(
                f"countries/{slug}/country.yaml declares slug {cfg['slug']!r}")

        locales = tuple(
            Locale(code=l["code"], html_lang=l.get("html_lang", l["code"]),
                   og_locale=l.get("og_locale", l["code"]),
                   endonym=l["endonym"])
            for l in cfg["locales"]
        )
        codes = [l.code for l in locales]
        if cfg["default_locale"] not in codes:
            raise ValueError(
                f"{slug}: default_locale {cfg['default_locale']!r} is not "
                f"among {codes}")
        if len(set(codes)) != len(codes):
            raise ValueError(f"{slug}: duplicate locale codes in {codes}")

        y = cfg["years"]
        return Country(
            slug=slug,
            name=cfg["name"],
            wordmark=cfg.get("wordmark", cfg["name"]["en"]),
            flag_emoji=cfg["flag_emoji"],
            locales=locales,
            default_locale=cfg["default_locale"],
            palette=Palette.from_config(cfg["palette"]),
            years=tuple(range(y["from"], y["to"] + 1)),
            last_full_year=cfg["last_full_year"],
            tick_every=cfg.get("tick_every", 2),
            recessions=tuple(
                (b["from"], b["to"], b["label"]) for b in cfg.get("bands", [])),
            currency=cfg["currency"]["code"],
            seo=cfg["seo"],
            sources=cfg.get("sources", {}),
            dir=d,
            spine=bool(cfg.get("spine", False)),
        )

    @staticmethod
    def all() -> list["Country"]:
        """Every country, in the order the home page lists them."""
        slugs = sorted(
            p.parent.name for p in COUNTRIES_DIR.glob("*/country.yaml"))
        return [Country.load(s) for s in slugs]

    # ------------------------------------------------------- the boundary
    def _within(self, base: Path, rel: str) -> Path:
        return within(base, rel, self.slug)

    @property
    def data_dir(self) -> Path:
        return self.dir / "data"

    @property
    def out_dir(self) -> Path:
        return self.dir / "output"

    def data(self, rel: str) -> Path:
        """Path to one of this country's CSVs."""
        return self._within(self.data_dir.resolve(), rel)

    def out(self, rel: str) -> Path:
        out = self.out_dir.resolve()
        out.mkdir(parents=True, exist_ok=True)
        p = self._within(out, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # --------------------------------------------------------- the data
    def table(self, rel: str) -> dict | None:
        """Read one of this country's CSVs as columns, or None if absent.

        Delegates to core.plotting.read_table so there is exactly one CSV
        reader in the project: blanks are NaN, years are ints, text stays
        text, and the '#' provenance header is skipped.
        """
        return plotting.read_table(self.data(rel))

    def comments(self, rel: str) -> list[str]:
        """The '#' provenance lines at the top of one of this country's CSVs."""
        return plotting.comments(self.data(rel))

    def rows(self, rel: str, key: str = "year") -> dict | None:
        """The same CSV keyed by year: ``{2006: {"gdp": ...}, ...}``."""
        path = self.data(rel)
        if not path.exists():
            return None
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(
                ln for ln in fh if not ln.lstrip().startswith("#"))
            return {int(float(r[key])): r for r in reader if r.get(key)}

    def has(self, rel: str) -> bool:
        return self.data(rel).exists()

    # -------------------------------------------------------- formatting
    def locale(self, code: str) -> Locale:
        for l in self.locales:
            if l.code == code:
                return l
        raise KeyError(f"{self.slug} does not publish in {code!r}")

    @property
    def locale_codes(self) -> tuple:
        return tuple(l.code for l in self.locales)

    def url(self, locale: str | None = None) -> str:
        """This country's path on the site, always with a trailing slash."""
        return f"/{self.slug}/" + (f"{locale}/" if locale else "")
