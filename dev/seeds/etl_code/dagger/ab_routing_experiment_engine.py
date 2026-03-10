"""A/B Routing Experiment Engine - Routing experiment metrics and convergence analysis."""

from etls import fact_packet_inspection, rpt_protocol_adoption

SUFFIXES = ["path_variants", "convergence"]


class AbRoutingExperimentEngine:
    def __init__(self):
        self.table = "rpt_routing_experiment_results"
        self.destination_tables = ["rpt_routing_experiment_results", "rpt_routing_variants"]
        self.schedule = "Daily at 04:30 UTC"
        self.category = "Network Science"
        self.networks = ["application_mesh"]

    def extract(self, start_date, end_date):
        self.packets = fact_packet_inspection(start_date, end_date).consume()
        self.adoption = rpt_protocol_adoption(start_date, end_date).consume()

    def transform(self, data):
        pass

    def load(self, data):
        pass
