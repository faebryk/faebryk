# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.can_attach_via_pinmap import can_attach_via_pinmap
from faebryk.library.CD4011 import CD4011
from faebryk.library.DIP import DIP
from faebryk.library.has_defined_footprint import has_defined_footprint


class TI_CD4011BE(CD4011):
    def __init__(self):
        super().__init__()
        fp = DIP(pin_cnt=14, spacing_mm=7.62, long_pads=False)
        self.add_trait(has_defined_footprint(fp))
        fp.get_trait(can_attach_via_pinmap).attach(
            {
                "7": self.IFs.power.NODEs.lv,
                "14": self.IFs.power.NODEs.hv,
                "3": self.NODEs.gates[0].IFs.outputs[0].NODEs.signal,
                "4": self.NODEs.gates[1].IFs.outputs[0].NODEs.signal,
                "11": self.NODEs.gates[2].IFs.outputs[0].NODEs.signal,
                "10": self.NODEs.gates[3].IFs.outputs[0].NODEs.signal,
                "1": self.NODEs.gates[0].IFs.inputs[0].NODEs.signal,
                "2": self.NODEs.gates[0].IFs.inputs[1].NODEs.signal,
                "5": self.NODEs.gates[1].IFs.inputs[0].NODEs.signal,
                "6": self.NODEs.gates[1].IFs.inputs[1].NODEs.signal,
                "12": self.NODEs.gates[2].IFs.inputs[0].NODEs.signal,
                "13": self.NODEs.gates[2].IFs.inputs[1].NODEs.signal,
                "9": self.NODEs.gates[3].IFs.inputs[0].NODEs.signal,
                "8": self.NODEs.gates[3].IFs.inputs[1].NODEs.signal,
            }
        )
