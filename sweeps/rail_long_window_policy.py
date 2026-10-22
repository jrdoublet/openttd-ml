"""Offline specification of a progressive long-distance RAIL discovery window.

This module is deliberately NOT wired into the game AI: it permits reviewing
the cadence, mode separation and search-budget envelopes before any runtime
or economic qualification. No ROI, economic score or financing decision is
changed here.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class DistanceBand:
    low: int
    high: int

    def __post_init__(self):
        if self.low > self.high:
            raise ValueError("empty distance band")

    @property
    def count(self):
        return self.high - self.low + 1


def window(stage: int, normal_cap: int = 200,
           map_width: int = 256, map_height: int = 256) -> Optional[DistanceBand]:
    """Cumulative interval; cap at the accessible Manhattan map span."""
    if stage < 0:
        return None
    if normal_cap < 0 or map_width < 1 or map_height < 1:
        raise ValueError("invalid normal cap or map dimensions")
    lower = max(normal_cap + 1, 224 - 16 * stage)
    upper = min(map_width + map_height - 2, 288 + 16 * stage)
    return DistanceBand(lower, upper) if lower <= upper else None


def fresh_bands(stage: int, normal_cap: int = 200,
                map_width: int = 256, map_height: int = 256) -> Tuple[DistanceBand, ...]:
    """Only new distance values, avoiding both normal and prior window scans."""
    current = window(stage, normal_cap, map_width, map_height)
    if current is None:
        return ()
    old = window(stage - 1, normal_cap, map_width, map_height)
    if old is None:
        return (current,)
    pieces = []
    if current.low < old.low:
        pieces.append(DistanceBand(current.low, old.low - 1))
    if old.high < current.high:
        pieces.append(DistanceBand(old.high + 1, current.high))
    return tuple(pieces)


@dataclass(frozen=True)
class WindowEvent:
    mode: str
    year: int
    month: int
    stage: int
    new_bands: Tuple[DistanceBand, ...]
    reason: str


@dataclass
class _ModeState:
    stage: int = -1
    last_change_month: int = -1
    shortage_streak: int = 0


@dataclass
class RailLongWindowPolicy:
    """Reviewable proposal, with independent pax and freight opening decisions.

    AIR enabled: passenger trigger uses AIR coverage of the top 30% towns.
    RAIL alone: passenger trigger uses own RAIL pax coverage, with a shortage
    fallback (both the normal short pool and cash precondition).
    Freight: no dependence on city population or AIR; use short freight pool
    scarcity. A minimum 24 game months applies to either mode.
    """

    start_year: int = 1970
    normal_cap: int = 200
    map_width: int = 256
    map_height: int = 256
    min_age_months: int = 24
    widen_every_months: int = 12
    min_cash_for_scout: int = 100_000
    min_coverage: float = 0.80
    max_annual_growth: float = 0.05
    shortage_threshold: int = 2
    min_shortage_months: int = 2
    pax: _ModeState = field(default_factory=_ModeState)
    freight: _ModeState = field(default_factory=_ModeState)
    _last_month: int = -1
    _last_year_cover: Dict[str, Tuple[int, float]] = field(default_factory=dict)

    def observe(self, year: int, month: int, *, mode_air: bool,
                mode_rail: bool = True, air_top30: Optional[float] = None,
                rail_pax_top30: Optional[float] = None,
                pax_short_startable: Optional[int] = None,
                freight_short_startable: Optional[int] = None,
                available_cash: int = 0) -> Tuple[WindowEvent, ...]:
        if not 1 <= month <= 12:
            raise ValueError("month must be 1..12")
        index = (year - self.start_year) * 12 + month - 1
        if index < self._last_month:
            raise ValueError("observations must be chronological")
        if index == self._last_month or not mode_rail:
            return ()
        self._last_month = index

        ready = index >= self.min_age_months
        liquid = available_cash >= self.min_cash_for_scout
        checks = (
            ("pax", self.pax, pax_short_startable),
            ("freight", self.freight, freight_short_startable),
        )
        for _, state, startable in checks:
            scarce = startable is not None and startable < self.shortage_threshold
            state.shortage_streak = state.shortage_streak + 1 if scarce and liquid else 0

        coverage_signal = False
        label = "air" if mode_air else "rail_pax"
        value = air_top30 if mode_air else rail_pax_top30
        if value is not None:
            if not 0.0 <= value <= 1.0:
                raise ValueError("coverage must be within 0..1")
            old = self._last_year_cover.get(label)
            if (old is not None and index - old[0] >= 12
                    and value >= self.min_coverage
                    and value - old[1] <= self.max_annual_growth + 1e-9):
                coverage_signal = True
            # A refresh at less than one year must not replace the reference
            # used for a 12-month comparison.
            if old is None or index - old[0] >= 12:
                self._last_year_cover[label] = (index, value)

        # During multimodal games a short-Rail-pax shortage is irrelevant:
        # it cannot independently override the AIR territory signal.
        pax_fallback = (not mode_air and self.pax.shortage_streak
                        >= self.min_shortage_months)
        conditions = (
            ("pax", self.pax, coverage_signal or pax_fallback,
             "coverage_plateau" if coverage_signal else "short_pax_pool"),
            ("freight", self.freight,
             self.freight.shortage_streak >= self.min_shortage_months,
             "short_freight_pool"),
        )
        events = []
        for mode, state, enabled, reason in conditions:
            if not ready or not enabled:
                continue
            if (state.last_change_month >= 0
                    and index - state.last_change_month < self.widen_every_months):
                continue
            target = state.stage + 1
            new_bands = fresh_bands(
                target, self.normal_cap, self.map_width, self.map_height)
            if not new_bands:
                continue
            state.stage = target
            state.last_change_month = index
            events.append(WindowEvent(mode, year, month, target, new_bands, reason))
        return tuple(events)
