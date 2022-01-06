
class KicadLibraryFootprint(Footprint):
    def __init__(self, kicad_lib: kicadlib, library_identifier: str) -> None:
        super().__init__()

        #TODO check in lib

        self.add_trait(has_kicad_footprint(library_identifier))