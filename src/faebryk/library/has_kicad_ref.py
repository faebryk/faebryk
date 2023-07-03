from faebryk.core.core import NodeTrait


class has_kicad_ref(NodeTrait):
    def get_ref(self) -> str:
        raise NotImplementedError()
