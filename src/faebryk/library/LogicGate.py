# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Sequence, TypeVar

from faebryk.core.core import Module, NodeTrait, TraitImpl
from faebryk.core.util import specialize_interface
from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Logic import Logic
from faebryk.libs.util import times

T = TypeVar("T", bound=Logic)


class LogicGate(Module):
    def __init__(
        self, input_cnt: Constant[int], output_cnt: Constant[int], *functions: TraitImpl
    ) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            inputs = times(input_cnt, Logic)
            outputs = times(output_cnt, Logic)

        self.IFs = IFS(self)

        for f in functions:
            self.add_trait(f)

    @staticmethod
    def op_(
        ins1: Sequence[Logic], ins2: Sequence[Logic], out: Sequence[T]
    ) -> Sequence[T]:
        assert len(ins1) == len(ins2)
        for in_if_mod, in_if in zip(ins1, ins2):
            in_if_mod.connect(in_if)
        return out

    def op(self, *ins: Logic):
        return self.op_(ins, self.IFs.inputs, self.IFs.outputs)


class ElectricLogicGate(LogicGate):
    def __init__(
        self, input_cnt: Constant[int], output_cnt: Constant[int], *functions: TraitImpl
    ) -> None:
        super().__init__(input_cnt, output_cnt, *functions)

        self.IFs_logic = self.IFs

        class IFS(Module.IFS()):
            inputs = times(input_cnt, ElectricLogic)
            outputs = times(output_cnt, ElectricLogic)

        self.IFs = IFS(self)

        for in_if_l, in_if_el in zip(self.IFs_logic.inputs, self.IFs.inputs):
            specialize_interface(in_if_l, in_if_el)
        for out_if_l, out_if_el in zip(self.IFs_logic.outputs, self.IFs.outputs):
            specialize_interface(out_if_l, out_if_el)

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )


class can_logic(NodeTrait):
    @abstractmethod
    def op(self, *ins: Logic) -> Logic:
        ...


class can_logic_or(can_logic):
    @abstractmethod
    def or_(self, *ins: Logic) -> Logic:
        ...

    def op(self, *ins: Logic) -> Logic:
        return self.or_(*ins)


class can_logic_and(can_logic):
    @abstractmethod
    def and_(self, *ins: Logic) -> Logic:
        ...

    def op(self, *ins: Logic) -> Logic:
        return self.and_(*ins)


class can_logic_nor(can_logic):
    @abstractmethod
    def nor(self, *ins: Logic) -> Logic:
        ...

    def op(self, *ins: Logic) -> Logic:
        return self.nor(*ins)


class can_logic_nand(can_logic):
    @abstractmethod
    def nand(self, *ins: Logic) -> Logic:
        ...

    def op(self, *ins: Logic) -> Logic:
        return self.nand(*ins)


class can_logic_xor(can_logic):
    @abstractmethod
    def xor(self, *ins: Logic) -> Logic:
        ...

    def op(self, *ins: Logic) -> Logic:
        return self.xor(*ins)


class can_logic_or_gate(can_logic_or.impl()):
    def on_obj_set(self) -> None:
        assert isinstance(self.get_obj(), LogicGate)

    def or_(self, *ins: Logic):
        obj = self.get_obj()
        assert isinstance(obj, LogicGate)
        return obj.op(*ins)[0]


class can_logic_nor_gate(can_logic_nor.impl()):
    def on_obj_set(self) -> None:
        assert isinstance(self.get_obj(), LogicGate)

    def nor(self, *ins: Logic):
        obj = self.get_obj()
        assert isinstance(obj, LogicGate)
        return obj.op(*ins)[0]


class can_logic_nand_gate(can_logic_nand.impl()):
    def on_obj_set(self) -> None:
        assert isinstance(self.get_obj(), LogicGate)

    def nand(self, *ins: Logic):
        obj = self.get_obj()
        assert isinstance(obj, LogicGate)
        return obj.op(*ins)[0]


class can_logic_xor_gate(can_logic_xor.impl()):
    def on_obj_set(self) -> None:
        assert isinstance(self.get_obj(), LogicGate)

    def xor(self, *ins: Logic):
        obj = self.get_obj()
        assert isinstance(obj, LogicGate)
        return obj.op(*ins)[0]


class OR(LogicGate):
    def __init__(self, input_cnt: Constant[int]):
        super().__init__(input_cnt, Constant(1), can_logic_or_gate())


class ElectricOR(ElectricLogicGate):
    def __init__(self, input_cnt: Constant[int]):
        super().__init__(input_cnt, Constant(1), can_logic_or_gate())


class NOR(LogicGate):
    def __init__(self, input_cnt: Constant[int]):
        super().__init__(input_cnt, Constant(1), can_logic_nor_gate())


class ElectricNOR(ElectricLogicGate):
    def __init__(self, input_cnt: Constant[int]):
        super().__init__(input_cnt, Constant(1), can_logic_nor_gate())


class NAND(ElectricLogicGate):
    def __init__(self, input_cnt: Constant[int]):
        super().__init__(input_cnt, Constant(1), can_logic_nand_gate())


class ElectricNAND(ElectricLogicGate):
    def __init__(self, input_cnt: Constant[int]) -> None:
        super().__init__(input_cnt, Constant(1), can_logic_nand_gate())


class XOR(ElectricLogicGate):
    def __init__(self, input_cnt: Constant[int]):
        super().__init__(input_cnt, Constant(1), can_logic_xor_gate())


class ElectricXOR(ElectricLogicGate):
    def __init__(self, input_cnt: Constant[int]) -> None:
        super().__init__(input_cnt, Constant(1), can_logic_xor_gate())
