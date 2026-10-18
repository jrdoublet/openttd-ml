"""CargoDist coverage contract. Source 15.3 script_station.hpp:100-169."""
from rva_dry_cycle import known


def distribution(mode, *, new_link, graph_ready, local_offer, capacity,
                 planned_via=None, waiting_via=None):
    if mode == 'manual':
        return {'status': 'estimated_manual', 'carried_month': min(local_offer, capacity)
                if all(known(v) and v >= 0 for v in (local_offer, capacity)) else None,
                'fallback': False}
    if mode not in ('symmetric', 'asymmetric') or new_link or not graph_ready:
        return {'status': 'reference_fallback_graph_forming_or_unknown',
                'carried_month': None, 'fallback': True,
                'bounds_month': [0, min(local_offer, capacity)]
                    if all(known(v) and v >= 0 for v in (local_offer, capacity)) else None}
    if not all(known(v) and v >= 0 for v in (planned_via, waiting_via, capacity)):
        return {'status': 'reference_fallback_missing_flow', 'carried_month': None, 'fallback': True}
    # Waiting is stock, NOT an additional permanent monthly flow.
    return {'status': 'estimated_existing_graph', 'carried_month': min(planned_via, capacity),
            'waiting_stock': waiting_via, 'fallback': False,
            'receipts': None, 'receipts_status': 'final_delivery_only'}
