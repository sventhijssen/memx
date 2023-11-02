import time
from datetime import datetime
from typing import Any, Dict

from utils import config
from core.hardware.Crossbar import MemristorCrossbar
from core.decision_diagrams.BDD import BDD
from synth.CrossbarMapping2D import CrossbarMapping2D
from synth.CrossbarMapping3D import CrossbarMapping3D
from synth.KLabeling import KLabeling
from synth.SynthesisMethod import SynthesisMethod
from synth.VHLabeling import VHLabeling


class COMPACT(SynthesisMethod):

    def __init__(self, bdd: BDD, layers: int = 1):
        """
        This synthesis method is based on the COMPACT framework in [1], [2], and the FLOW-3D framework in [3].

        [1] Thijssen, S., Jha, S. K., & Ewetz, R. (2021, February).
        Compact: Flow-based computing on nanoscale crossbars with minimal semiperimeter.
        In 2021 Design, Automation & Test in Europe Conference & Exhibition (DATE) (pp. 232-237). IEEE.

        [2] Thijssen, S., Jha, S. K., & Ewetz, R. (2021).
        Compact: Flow-based computing on nanoscale crossbars with minimal semiperimeter and maximum dimension.
        IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 41(11), 4600-4611.

        [3] Thijssen, S., Jha, S. K., & Ewetz, R. (2023, January).
        FLOW-3D: Flow-Based Computing on 3D Nanoscale Crossbars with Minimal Semiperimeter.
        In 2023 28th Asia and South Pacific Design Automation Conference (ASP-DAC) (pp. 775-780). IEEE.
        """
        super(COMPACT, self).__init__(bdd)

        self.layers = layers

        if config.vh_labeling:
            self.labeling_method = VHLabeling(self.dd.dag)
            self.mapping_method = CrossbarMapping2D(self.dd.dag)
        else:
            self.labeling_method = KLabeling(self.dd.dag, self.layers)
            self.mapping_method = CrossbarMapping3D(self.dd.dag, self.layers)

        self.labeling = None

    def map(self) -> MemristorCrossbar:
        print("COMPACT started")
        print(datetime.now())

        self.start_time = time.time()
        self.labeling = self.labeling_method.label()
        crossbar = self.mapping_method.map(self.labeling)
        self.end_time = time.time()

        self.component = crossbar

        config.log.add_json(self.get_log())

        print("COMPACT stopped")

        return crossbar

    def get_log(self) -> Dict[str, Any]:
        return {
            "synthesis_method": self.__class__.__name__,
            "nodes": len(self.dd.dag.nodes),
            "edges": len(self.dd.dag.edges),
            "rows": self.component.get_rows(),
            "columns": self.component.get_columns(),
            "labeling": self.labeling_method.get_log(),
            "synthesis_time": self.end_time - self.start_time,
        }
