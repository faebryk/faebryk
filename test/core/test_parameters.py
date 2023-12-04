# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from typing import TypeVar

from faebryk.core.core import logger as core_logger
from faebryk.library.Constant import Constant
from faebryk.library.Operation import Operation
from faebryk.library.Range import Range
from faebryk.library.Set import Set
from faebryk.library.TBD import TBD

logger = logging.getLogger(__name__)
core_logger.setLevel(logger.getEffectiveLevel())


class TestParameters(unittest.TestCase):
    def test_operations(self):
        T = TypeVar("T")

        def assertIsInstance(obj, cls: type[T]) -> T:
            self.assertIsInstance(obj, cls)
            assert isinstance(obj, cls)
            return obj

        # Constant
        ONE = Constant(1)
        self.assertEqual(ONE, 1)

        TWO = Constant(2)
        self.assertEqual(assertIsInstance(ONE + TWO, Constant).value, 3)
        self.assertEqual(assertIsInstance(ONE - TWO, Constant).value, -1)

        self.assertEqual(assertIsInstance((ONE / TWO) / TWO, Constant).value, 1 / 4)

        # Range
        R_ONE_TEN = Range(1, 10)
        self.assertEqual(assertIsInstance(R_ONE_TEN + TWO, Range).as_tuple(), (3, 12))

        R_TWO_THREE = Range(2, 3)
        self.assertEqual(
            assertIsInstance(R_ONE_TEN + R_TWO_THREE, Range).as_tuple(), (3, 13)
        )

        # Set
        S_FIVE_NINE = Set(set(Constant(x) for x in range(5, 10)))

    def test_resolution(self):
        ...


if __name__ == "__main__":
    unittest.main()
