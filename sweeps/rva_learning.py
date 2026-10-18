"""RVA-13: learn observed station dwell only, with causal observation times.

No revenue/network correction, C70/V212 change, or mechanical-cause inference.
No coefficient: median of past comparable dwell intervals, cold physics intact.
"""
import statistics
import copy
from rva_dry_cycle import known

VERSION = 1


class DwellModel:
    def __init__(self):
        self.observations = []

    def observe(self, context, completed_tick, dwell_bounds):
        lo, hi = dwell_bounds
        if (not isinstance(context, str) or not context or type(completed_tick) is not int
                or completed_tick < 0 or not all(known(v) for v in (lo, hi)) or not 0 <= lo <= hi):
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

    def save(self, fingerprint, saved_tick):
        if not isinstance(fingerprint,str) or not fingerprint or type(saved_tick) is not int or saved_tick<0:
            raise ValueError('Versioned world/model fingerprint and save tick required')
        return {'version':VERSION,'fingerprint':fingerprint,'saved_tick':saved_tick,
                'observations':copy.deepcopy([r for r in self.observations if r['completed_tick']<=saved_tick])}

    @classmethod
    def load(cls, state, fingerprint, resumed_tick):
        model = cls()
        model.load_status = 'cold_incompatible_state'
        if (not isinstance(state,dict) or type(state.get('version')) is not int or state.get('version')!=VERSION
                or state.get('fingerprint')!=fingerprint or not fingerprint
                or type(resumed_tick) is not int or resumed_tick<0
                or type(state.get('saved_tick')) is not int or state['saved_tick']>resumed_tick
                or state['saved_tick']<0 or not isinstance(state.get('observations'),list)):
            return model
        try:
            for row in state['observations']:
                if row['completed_tick']>state['saved_tick']:
                    raise ValueError('Future observation')
                model.observe(row['context'],row['completed_tick'],row['dwell_bounds'])
        except (ValueError,TypeError,KeyError):
            model.observations=[]
            model.load_status='cold_invalid_observations'
            return model
        model.load_status='restored'
        return model
