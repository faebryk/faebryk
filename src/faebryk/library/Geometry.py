import logging
import math
from abc import ABC, abstractmethod
from typing import Iterable, Self, TypeVar

from faebryk.core.core import Module, ModuleInterface, Node, Parameter, Trait
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Constant import Constant
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Vector(ABC):
    def __init__(self, coords: list[float]) -> None:
        self.coords = coords

    def __truediv__(self, other: float):
        return self.from_vector(Vector([c / other for c in self.coords]))

    def __mul__(self, other: float):
        return self.from_vector(Vector([c * other for c in self.coords]))

    def __abs__(self):
        return math.sqrt(sum([x**2 for x in self.coords]))

    def __add__(self, other: Self) -> Self:
        assert type(self) is type(other)
        return self.from_vector(
            Vector([c1 + c2 for c1, c2 in zip(self.coords, other.coords)])
        )

    def __sub__(self, other: Self) -> Self:
        assert type(self) is type(other)
        return self.from_vector(
            Vector([c1 - c2 for c1, c2 in zip(self.coords, other.coords)])
        )

    @property
    def dim(self):
        return len(self.coords)

    T = TypeVar("T", bound="Vector")

    @classmethod
    def from_vector(cls: type[T], vector: "Vector") -> T:
        if cls is not Vector:
            raise NotImplementedError()
        return vector

    def __repr__(self) -> str:
        return f"{type(self).__name__}({','.join([str(c) for c in self.coords])})"


class Space(Module):
    def __init__(self, quantization: float, vector_type: type[Vector]) -> None:
        super().__init__()

        self.quantization = quantization
        self.vector = vector_type

        class NODES(Module.NODES()):
            zero = Anchor()

        self.NODEs = NODES(self)


class PixelSpace(Space):
    class PixelVector(Vector):
        def __init__(self, x: float, y: float) -> None:
            super().__init__([x, y])

        @property
        def x(self):
            return int(self.coords[0])

        @property
        def y(self):
            return int(self.coords[1])

        @classmethod
        def from_vector(cls, vector: Vector):
            assert len(vector.coords) == 2
            return cls(*vector.coords)

    def __init__(self, dimensions: PixelVector):
        super().__init__(1, self.PixelVector)

        self.dimensions = dimensions
        self.NODEs.zero.add_trait(
            can_be_projected_into_vector_space_defined(self.PixelVector(0, 0))
        )


class can_be_projected_into_vector_space(Trait):
    @abstractmethod
    def project(self, space: Space) -> list[Vector]:
        ...


class does_operations_in_vector_space(Trait):
    @abstractmethod
    def execute(self, space: Space) -> list[Node]:
        ...


class can_be_projected_into_vector_space_defined(
    can_be_projected_into_vector_space.impl()
):
    def __init__(self, vector: Vector) -> None:
        super().__init__()
        self.vector = vector

    def project(self, space: Space) -> list[Vector]:
        return [self.vector]


def anchor_projection(space: Space, anchors: Iterable["Anchor"]) -> list[Vector]:
    return [
        a.get_trait(can_be_projected_into_vector_space).project(space)[0]
        for a in anchors
    ]


class Anchor(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class GIFS(ModuleInterface.GIFS()):
            ...

        self.GIFs = GIFS(self)

        class NODES(ModuleInterface.NODES()):
            ...

        self.NODEs = NODES(self)


class Translation(Module):
    def __init__(self, vector: Parameter) -> None:
        super().__init__()

        self.vector = vector

        class IFS(Module.IFS()):
            source = Anchor()
            destination = Anchor()

        self.IFs = IFS(self)

        class NODES(Node.NODES()):
            ...

        self.NODEs = NODES(self)

        self.add_trait(can_bridge_defined(self.IFs.source, self.IFs.destination))

        class _(does_operations_in_vector_space.impl()):
            def is_implemented(_self):
                return self.IFs.source.has_trait(
                    can_be_projected_into_vector_space
                ) and isinstance(self.vector, Constant)

            def execute(_self, space: Space):
                assert isinstance(self.vector, Constant)
                assert isinstance(self.vector.value, space.vector)

                base_vec = anchor_projection(space, [self.IFs.source])[0]
                out_vec = base_vec + self.vector.value

                self.IFs.destination.add_trait(
                    can_be_projected_into_vector_space_defined(out_vec)
                )
                return [self.IFs.destination]

        self.add_trait(_())

    def translate(self, src: Anchor, dst: Anchor, i=1):
        if i == 0:
            src.connect(dst)
            return dst

        if i > 1:
            return self.translate(
                Translation(self.vector).translate(src, Anchor()), dst, i - 1
            )

        src.connect_via(self, dst)

        return dst


class Rotation(Module):
    def __init__(self, angle: Parameter) -> None:
        super().__init__()

        self.angle = angle

        class IFS(Module.IFS()):
            center = Anchor()
            source = Anchor()
            destination = Anchor()

        self.IFs = IFS(self)

        class NODES(Node.NODES()):
            ...

        self.NODEs = NODES(self)

        class _(does_operations_in_vector_space.impl()):
            def is_implemented(_self):
                return all(
                    x.has_trait(can_be_projected_into_vector_space)
                    for x in [self.IFs.center, self.IFs.source]
                ) and isinstance(self.angle, Constant)

            def execute(_self, space: Space):
                assert isinstance(self.angle, Constant)

                source_vec, center_vec = anchor_projection(
                    space, [self.IFs.source, self.IFs.center]
                )
                diff_vec = source_vec - center_vec

                out_vec = center_vec + self.rotate_vector(diff_vec, self.angle.value)
                self.IFs.destination.add_trait(
                    can_be_projected_into_vector_space_defined(out_vec)
                )

                return [self.IFs.destination]

        self.add_trait(_())

    @staticmethod
    def rotate_vector(vector: "Vector", angle_deg: float):
        if vector.dim != 2:
            raise NotImplementedError("Only support 2D rotations for now")

        cos_angle = math.cos(angle_deg / 180 * math.pi)
        sin_angle = math.sin(angle_deg / 180 * math.pi)

        return vector.from_vector(
            Vector(
                [
                    vector.coords[0] * cos_angle - vector.coords[1] * sin_angle,
                    vector.coords[0] * sin_angle + vector.coords[1] * cos_angle,
                ]
            )
        )

    def rotate(self, center: Anchor, src: Anchor, dst: Anchor):
        self.IFs.center.connect(center)
        self.IFs.source.connect(src)
        self.IFs.destination.connect(dst)

        return dst


class Line(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            ends = times(2, Anchor)

        self.IFs = IFS(self)

        class NODES(Module.NODES()):
            ...

        self.NODEs = NODES(self)

        class _(can_be_projected_into_vector_space.impl()):
            def is_implemented(_self):
                return all(
                    x.has_trait(can_be_projected_into_vector_space)
                    for x in self.IFs.ends
                )

            @staticmethod
            def project(space: Space) -> list[Vector]:
                src, dst = anchor_projection(space, self.IFs.ends)
                diff_vec = dst - src
                count = int(abs(diff_vec) / space.quantization)

                return [src + diff_vec * i / count for i in range(count)]

        self.add_trait(_())

    def set_direction(self, vector: Parameter):
        # TODO translation has direction, line does not
        Translation(vector).translate(*self.IFs.ends)


class Circle(Module):
    def __init__(self, radius: Parameter) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            center = Anchor()
            radius = Anchor()

        self.IFs = IFS(self)

        class NODES(Module.NODES()):
            ...

        self.NODEs = NODES(self)

        self.translation = Translation(radius)
        self.translation.translate(self.IFs.center, self.IFs.radius)

        class _(can_be_projected_into_vector_space.impl()):
            def is_implemented(_self):
                return all(
                    x.has_trait(can_be_projected_into_vector_space)
                    for x in self.IFs.get_all()
                )

            @staticmethod
            def project(space: Space) -> list[Vector]:
                (center_vec, rad_end_vec) = anchor_projection(
                    space, [self.IFs.center, self.IFs.radius]
                )

                rad_vec = rad_end_vec - center_vec

                count = int(2 * math.pi * abs(rad_vec) / space.quantization)
                return [
                    center_vec + Rotation.rotate_vector(rad_vec, i * 360 / count)
                    for i in range(count)
                ]

        self.add_trait(_())

    def set_radius(self, radius: Parameter):
        self.translation.vector = radius

    def on_arc(self, angle: Parameter) -> Anchor:
        return Rotation(angle).rotate(
            self.IFs.center,
            self.IFs.radius,
            Anchor(),
        )
