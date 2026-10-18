"""RVA-13: learn observed station dwell only, with causal observation times.

No revenue/network correction, C70/V212 change, or mechanical-cause inference.
No coefficient: median of past comparable dwell intervals, cold physics intact.
"""
import statistics

VERSION = 1


class DwellModel:
    def __init__(self):
        self.observations = []

    def observe(self, context, completed_tick, dwell_bounds):
        lo, hi = dwell_bounds
        if not isinstance(context, str) or not context or not 0 <= lo <= hi:
            raise ValueError('Explicit context and physical interval required')
        self.observations.append(dict(context=context, completed_tick=completed_tick,
                                      dwell_bounds=[lo, hi]))

    def predict(self, context, forecast_tick, physical_dwell):
        rows = [r for r in self.observations if r['context'] == context
                and r['completed_tick'] < forecast_tick]
        if not rows:
            return {'status': 'cold_physics', 'dwell': physical_dwell, 'bounds': None, 'n': 0}
        bounds = [statistics.median(r['dwell_bounds'][i] for r in rows) for i in (0, 1)]
        return {'status': 'past_observed_station_dwell', 'dwell': statistics.mean(bounds),
                'bounds': bounds, 'n': len(rows), 'cause': 'not_identified'}
