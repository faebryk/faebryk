# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from itertools import chain

from faebryk.core.core import LinkDirectShallow, Module
from faebryk.core.core import logger as core_logger
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.UART_Base import UART_Base
from faebryk.libs.util import times

logger = logging.getLogger(__name__)
core_logger.setLevel(logger.getEffectiveLevel())


# TODO move somewhere else
def print_stack(stack):
    from colorama import Fore

    for frame_info in stack:
        frame = frame_info[0]
        if "venv" in frame_info.filename:
            continue
        if "faebryk" not in frame_info.filename:
            continue
        # if frame_info.function not in ["_connect_across_hierarchies"]:
        #    continue
        yield (
            f"{Fore.RED} Frame in {frame_info.filename} at line {frame_info.lineno}:"
            f"{Fore.BLUE} {frame_info.function} {Fore.RESET}"
        )

        def pretty_val(value):
            if isinstance(value, dict):
                import pprint

                return (
                    ("\n" if len(value) > 1 else "")
                    + pprint.pformat(
                        {pretty_val(k): pretty_val(v) for k, v in value.items()},
                        indent=2,
                        width=120,
                    )
                ).replace("\n", f"\n    {Fore.RESET}")
            elif isinstance(value, type):
                return f"<class {value.__name__}>"
            return value

        for name, value in frame.f_locals.items():
            yield f"  {Fore.GREEN}{name}{Fore.RESET} = {pretty_val(value)}"


class TestHierarchy(unittest.TestCase):
    def test_up_connect(self):
        class UARTBuffer(Module):
            def __init__(self) -> None:
                super().__init__()

                class _IFs(super().IFS()):
                    bus1 = UART_Base()
                    bus2 = UART_Base()

                self.IFs = _IFs(self)

                bus1 = self.IFs.bus1
                bus2 = self.IFs.bus2

                bus1.NODEs.rx.NODEs.signal.connect(bus2.NODEs.rx.NODEs.signal)
                bus1.NODEs.tx.NODEs.signal.connect(bus2.NODEs.tx.NODEs.signal)
                bus1.NODEs.rx.NODEs.reference.connect(bus2.NODEs.rx.NODEs.reference)

        app = UARTBuffer()

        self.assertTrue(app.IFs.bus1.NODEs.rx.is_connected_to(app.IFs.bus2.NODEs.rx))
        self.assertTrue(app.IFs.bus1.NODEs.tx.is_connected_to(app.IFs.bus2.NODEs.tx))
        self.assertTrue(app.IFs.bus1.is_connected_to(app.IFs.bus2))

    def test_bridge(self):
        class Buffer(Module):
            def __init__(self) -> None:
                super().__init__()

                class _IFs(super().IFS()):
                    ins = times(2, Electrical)
                    outs = times(2, Electrical)

                    ins_l = times(2, ElectricLogic)
                    outs_l = times(2, ElectricLogic)

                self.IFs = _IFs(self)

                ref = ElectricLogic.connect_all_module_references(self)
                self.add_trait(has_single_electric_reference_defined(ref))

                for el, lo in chain(
                    zip(self.IFs.ins, self.IFs.ins_l),
                    zip(self.IFs.outs, self.IFs.outs_l),
                ):
                    lo.NODEs.signal.connect(el)

                for l1, l2 in zip(self.IFs.ins_l, self.IFs.outs_l):
                    l1.connect(
                        l2,
                        linkcls=LinkDirectShallow(
                            lambda link, gif: not isinstance(gif.node, Electrical)
                        ),
                    )

        class UARTBuffer(Module):
            def __init__(self) -> None:
                super().__init__()

                class _NODES(super().NODES()):
                    buf = Buffer()

                class _IFs(super().IFS()):
                    bus1 = UART_Base()
                    bus2 = UART_Base()

                self.IFs = _IFs(self)
                self.NODEs = _NODES(self)

                ElectricLogic.connect_all_module_references(self)

                bus1 = self.IFs.bus1
                bus2 = self.IFs.bus2
                buf = self.NODEs.buf

                bus1.NODEs.tx.NODEs.signal.connect(buf.IFs.ins[0])
                bus1.NODEs.rx.NODEs.signal.connect(buf.IFs.ins[1])
                bus2.NODEs.tx.NODEs.signal.connect(buf.IFs.outs[0])
                bus2.NODEs.rx.NODEs.signal.connect(buf.IFs.outs[1])

        import faebryk.core.core as c

        # Enable to see the stack trace of invalid connections
        # c.LINK_TB = True
        app = UARTBuffer()

        def _assert_no_link(mif1, mif2):
            link = mif1.is_connected_to(mif2)
            err = ""
            if link and c.LINK_TB:
                err = "\n" + ("\n".join(print_stack(link.tb)))
            self.assertFalse(link, err)

        bus1 = app.IFs.bus1
        bus2 = app.IFs.bus2
        buf = app.NODEs.buf

        # Check that the two buffer sides are not connected electrically
        _assert_no_link(buf.IFs.ins[0], buf.IFs.outs[0])
        _assert_no_link(buf.IFs.ins[1], buf.IFs.outs[1])
        _assert_no_link(bus1.NODEs.rx.NODEs.signal, bus2.NODEs.rx.NODEs.signal)
        _assert_no_link(bus1.NODEs.tx.NODEs.signal, bus2.NODEs.tx.NODEs.signal)

        # Check that the two buffer sides are connected logically
        self.assertTrue(bus1.NODEs.rx.is_connected_to(bus2.NODEs.rx))
        self.assertTrue(bus1.NODEs.tx.is_connected_to(bus2.NODEs.tx))
        self.assertTrue(bus1.is_connected_to(bus2))


if __name__ == "__main__":
    unittest.main()
