from faebryk.library.has_overriden_name import has_overriden_name


class has_overriden_name_defined(has_overriden_name.impl()):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def get_name(self):
        return self.name
