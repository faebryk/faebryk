# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import glob
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import black
import typer
from faebryk.libs.tools.typer import typer_callback

# TODO use AST instead of string


@dataclass
class CTX:
    path: Path
    pypath: str


def get_ctx(ctx: typer.Context) -> "CTX":
    return ctx.obj


def write(ctx: typer.Context, contents: str, filename=""):
    path: Path = get_ctx(ctx).path
    if filename:
        path = path.with_stem(filename)
    contents = contents.strip()
    contents = black.format_file_contents(contents, fast=True, mode=black.FileMode())
    path.write_text(contents)

    typer.echo(f"File {path} created")


def get_name(ctx: typer.Context):
    return get_ctx(ctx).path.stem


@typer_callback(None)
def main(ctx: typer.Context, name: str, local: bool = True, overwrite: bool = False):
    """
    Can be called like this: > faebryk libadd
    Or python -m faebryk libadd
    Or python -m faebryk.tools.libadd
    For help invoke command without arguments.
    """

    if not local:
        import faebryk.library._F as F

        libfolder = Path(F.__file__).parent
        pypath = f"faebryk.library.{name}"
    else:
        libfolder = Path("library")
        if not libfolder.is_dir():
            if Path("src").is_dir():
                candidates = glob.glob("src/*/library")
                if not len(candidates) == 1:
                    raise FileNotFoundError(
                        f"Library folder not found, are you in the right directory? "
                        f"{candidates}"
                    )
                libfolder = Path(candidates[0])

        pypath = f".library.{name}"

    if not libfolder.exists():
        raise FileNotFoundError(
            f"Library folder {libfolder} not found, are you in the right directory?"
        )

    path = (libfolder / name).with_suffix(".py")

    if path.exists() and not overwrite:
        raise FileExistsError(f"File {path} already exists")

    ctx.obj = CTX(path=path, pypath=pypath)


@main.command()
def module(ctx: typer.Context, interface: bool = False):
    base = "Module" if not interface else "ModuleInterface"

    out = dedent(f"""
        # This file is part of the faebryk project
        # SPDX-License-Identifier: MIT

        import logging

        from faebryk.core.core import {base}

        logger = logging.getLogger(__name__)

        class {get_name(ctx)}({base}):
            @classmethod
            def NODES(cls):
                # submodules
                class _NODES(super().NODES()):
                    pass

                return _NODES

            @classmethod
            def PARAMS(cls):
                # parameters
                class _PARAMS(super().PARAMS()):
                    pass

                return _PARAMS

            @classmethod
            def IFS(cls):
                # interfaces
                class _IFS(super().IFS()):
                    pass

                return _IFS

            def __init__(self):
                # boilerplate
                super().__init__()
                self.IFs = self.IFS()(self)
                self.PARAMs = self.PARAMS()(self)
                self.NODEs = self.NODES()(self)

                # connections

                # traits
    """)

    write(ctx, out)


@main.command()
def trait(ctx: typer.Context, defined: bool = False):
    traitname = get_name(ctx)
    out = dedent(f"""
        # This file is part of the faebryk project
        # SPDX-License-Identifier: MIT

        import logging
        from abc import abstractmethod

        from faebryk.core.core import Trait

        logger = logging.getLogger(__name__)

        class {traitname}(Trait):
            @abstractmethod
            def DO_SOMETHING(self) -> None: ...
    """)

    write(ctx, out)

    if not defined:
        return

    implname = get_name(ctx) + "_defined"

    out = dedent(f"""
        # This file is part of the faebryk project
        # SPDX-License-Identifier: MIT

        import logging

        from {get_ctx(ctx).pypath} import {traitname}

        logger = logging.getLogger(__name__)

        class {implname}({traitname}.impl()):
            def DO_SOMETHING(self) -> None:
                pass
    """)

    write(ctx, out, filename=implname)


if __name__ == "__main__":
    main()
