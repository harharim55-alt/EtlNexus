"""NetFlow Capture - Raw network flow records from switches and routers."""

from etls import switch_interface_snapshot

SUFFIXES = []


class NetflowCapture:
    def __init__(self):
        self.table = "fact_netflow_records"
        self.destination_tables = ["fact_netflow_records", "dim_flow_sessions"]
        self.schedule = "Every 4 Hours"
        self.category = "Traffic Analytics"
        self.networks = ["heartbeat_probe", "backbone_core", "application_mesh"]

    def extract(self, start_date, end_date):
        self.ports = switch_interface_snapshot(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
