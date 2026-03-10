"""BGP Route Sync - Daily synchronization of transit routing tables."""

from etls import switch_interface_snapshot

SUFFIXES = ["peers", "prefixes", "as_paths", "communities", "route_maps", "dampened", "rib_entries"]


class BgpRouteSync:
    def __init__(self):
        self.table = "stg_bgp_announcements"
        self.destination_tables = ["stg_bgp_announcements", "stg_bgp_peers"]
        self.schedule = "Daily at 00:00 UTC"
        self.category = "Transit/Peering"
        self.networks = ["transit_exchange", "backbone_core"]

    def extract(self, start_date, end_date):
        self.ports = switch_interface_snapshot(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
