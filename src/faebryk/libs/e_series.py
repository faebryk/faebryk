import logging
from math import ceil, floor, log10
from typing import Tuple

from faebryk.core.core import Parameter
from faebryk.library.Constant import Constant
from faebryk.library.Range import Range

logger = logging.getLogger(__name__)

E192 = [
    1.00,
    1.01,
    1.02,
    1.04,
    1.05,
    1.06,
    1.07,
    1.09,
    1.10,
    1.11,
    1.13,
    1.14,
    1.15,
    1.17,
    1.18,
    1.20,
    1.21,
    1.23,
    1.24,
    1.26,
    1.27,
    1.29,
    1.30,
    1.32,
    1.33,
    1.35,
    1.37,
    1.38,
    1.40,
    1.42,
    1.43,
    1.45,
    1.47,
    1.49,
    1.50,
    1.52,
    1.54,
    1.56,
    1.58,
    1.60,
    1.62,
    1.64,
    1.65,
    1.67,
    1.69,
    1.72,
    1.74,
    1.76,
    1.78,
    1.80,
    1.82,
    1.84,
    1.87,
    1.89,
    1.91,
    1.93,
    1.96,
    1.98,
    2.00,
    2.03,
    2.05,
    2.08,
    2.10,
    2.13,
    2.15,
    2.18,
    2.21,
    2.23,
    2.26,
    2.29,
    2.32,
    2.34,
    2.37,
    2.40,
    2.43,
    2.46,
    2.49,
    2.52,
    2.55,
    2.58,
    2.61,
    2.64,
    2.67,
    2.71,
    2.74,
    2.77,
    2.80,
    2.84,
    2.87,
    2.91,
    2.94,
    2.98,
    3.01,
    3.05,
    3.09,
    3.12,
    3.16,
    3.20,
    3.24,
    3.28,
    3.32,
    3.36,
    3.40,
    3.44,
    3.48,
    3.52,
    3.57,
    3.61,
    3.65,
    3.70,
    3.74,
    3.79,
    3.83,
    3.88,
    3.92,
    3.97,
    4.02,
    4.07,
    4.12,
    4.17,
    4.22,
    4.27,
    4.32,
    4.37,
    4.42,
    4.48,
    4.53,
    4.59,
    4.64,
    4.70,
    4.75,
    4.81,
    4.87,
    4.93,
    4.99,
    5.05,
    5.11,
    5.17,
    5.23,
    5.30,
    5.36,
    5.42,
    5.49,
    5.56,
    5.62,
    5.69,
    5.76,
    5.83,
    5.90,
    5.97,
    6.04,
    6.12,
    6.19,
    6.26,
    6.34,
    6.42,
    6.49,
    6.57,
    6.65,
    6.73,
    6.81,
    6.90,
    6.98,
    7.06,
    7.15,
    7.23,
    7.32,
    7.41,
    7.50,
    7.59,
    7.68,
    7.77,
    7.87,
    7.96,
    8.06,
    8.16,
    8.25,
    8.35,
    8.45,
    8.56,
    8.66,
    8.76,
    8.87,
    8.98,
    9.09,
    9.20,
    9.31,
    9.42,
    9.53,
    9.65,
    9.76,
    9.88,
]

E96 = [
    1.00,
    1.02,
    1.05,
    1.07,
    1.10,
    1.13,
    1.15,
    1.18,
    1.21,
    1.24,
    1.27,
    1.30,
    1.33,
    1.37,
    1.40,
    1.43,
    1.47,
    1.50,
    1.54,
    1.58,
    1.62,
    1.65,
    1.69,
    1.74,
    1.78,
    1.82,
    1.87,
    1.91,
    1.96,
    2.00,
    2.05,
    2.10,
    2.15,
    2.21,
    2.26,
    2.32,
    2.37,
    2.43,
    2.49,
    2.55,
    2.61,
    2.67,
    2.74,
    2.80,
    2.87,
    2.94,
    3.01,
    3.09,
    3.16,
    3.24,
    3.32,
    3.40,
    3.48,
    3.57,
    3.65,
    3.74,
    3.83,
    3.92,
    4.02,
    4.12,
    4.22,
    4.32,
    4.42,
    4.53,
    4.64,
    4.75,
    4.87,
    4.99,
    5.11,
    5.23,
    5.36,
    5.49,
    5.62,
    5.76,
    5.90,
    6.04,
    6.19,
    6.34,
    6.49,
    6.65,
    6.81,
    6.98,
    7.15,
    7.32,
    7.50,
    7.68,
    7.87,
    8.06,
    8.25,
    8.45,
    8.66,
    8.87,
    9.09,
    9.31,
    9.53,
    9.76,
]

E48 = [
    1.00,
    1.05,
    1.10,
    1.15,
    1.21,
    1.27,
    1.33,
    1.40,
    1.47,
    1.54,
    1.62,
    1.69,
    1.78,
    1.87,
    1.96,
    2.05,
    2.15,
    2.26,
    2.37,
    2.49,
    2.61,
    2.74,
    2.87,
    3.01,
    3.16,
    3.32,
    3.48,
    3.65,
    3.83,
    4.02,
    4.22,
    4.42,
    4.64,
    4.87,
    5.11,
    5.36,
    5.62,
    5.90,
    6.19,
    6.49,
    6.81,
    7.15,
    7.50,
    7.87,
    8.25,
    8.66,
    9.09,
    9.53,
]

E24 = [
    1.0,
    1.1,
    1.2,
    1.3,
    1.5,
    1.6,
    1.8,
    2.0,
    2.2,
    2.4,
    2.7,
    3.0,
    3.3,
    3.6,
    3.9,
    4.3,
    4.7,
    5.1,
    5.6,
    6.2,
    6.8,
    7.5,
    8.2,
    9.1,
]

E12 = [
    1.0,
    1.2,
    1.5,
    1.8,
    2.2,
    2.7,
    3.3,
    3.9,
    4.7,
    5.6,
    6.8,
    8.2,
]

E6 = [
    1.0,
    1.5,
    2.2,
    3.3,
    4.7,
    6.8,
]

E3 = [
    1.0,
    2.2,
    4.7,
]

E_ALL = sorted(list(set(E24 + E48 + E96 + E192)))


def e_series_in_range(value_range: Range, e_series: list = E_ALL):
    """
    Returns a list of E series values that are within the specified range.
    """
    # append 10 to fix the result when R1 is close to 10
    e_series += [10]
    result = []
    lower_exp = int(floor(log10(value_range.min)))
    upper_exp = int(ceil(log10(value_range.max)))
    for exp in range(lower_exp, upper_exp):
        for e in e_series:
            val = e * 10**exp
            if val >= value_range.min and val <= value_range.max:
                result.append(val)
    return result


def e_series_ratio(
    R1: Parameter, output_input_ratio: Parameter, e_values: list = E_ALL
) -> Tuple[float, float]:
    """
    Calculates the values for two components in the E series range which are bound by a
    ratio.

    output_input_ratio = R2/(R1 + R2)
    R2/or = r1 + r2
    R2 ( 1/or -1) = R1
    R2 = R1 / (1/OR -1)



    Returns a tuple of R1/R2 values, of which R1 is decided by component_value, and R2
    is chosen from the E series based on ratio.

    Can be used for a resistive divider.
    """

    # append 10 to fix the result when R1 is close to 10
    e_values += [10]

    if type(R1) is Constant:
        R1_value = R1.value

        if type(output_input_ratio) is Constant:
            output_input_ratio_value = output_input_ratio.value

            if output_input_ratio_value >= 1 or output_input_ratio_value <= 0:
                raise ValueError("Invalid output/input voltage ratio")

            R2_ideal = R1_value / (1 / output_input_ratio_value - 1)

            exponent = floor(log10(R2_ideal))
            e_values_exp = [e * 10**exponent for e in e_values]

            R2_value = min(e_values_exp, key=lambda x: abs(x - R2_ideal))

            return (R1_value, R2_value)

        elif type(output_input_ratio) is Range:
            if (
                output_input_ratio.min >= 1
                or output_input_ratio.min <= 0
                and output_input_ratio.max >= 1
                and output_input_ratio.max <= 0
            ):
                raise ValueError("Invalid output/input voltage ratio")

            target_ratio = (output_input_ratio.max + output_input_ratio.min) / 2

            R2_ideal = R1_value / (1 / target_ratio - 1)

            exponent = floor(log10(R2_ideal))
            e_values_exp = [e * 10**exponent for e in e_values]

            R2_value = min(e_values_exp, key=lambda x: abs(x - R2_ideal))

            real_ratio = R2_value / (R1_value + R2_value)

            if (
                real_ratio > output_input_ratio.max
                or real_ratio < output_input_ratio.min
            ):
                raise ValueError(
                    """
                    Calculated optimum R1 R2 value pair gives output/input voltage
                    ratio outside of specified range.
                    Consider Increasing the output/input range or using a broader E
                    value series
                    """
                )

            return (R1_value, R2_value)

    elif type(R1) is Range:
        if type(output_input_ratio) is Constant:
            output_input_ratio_value = output_input_ratio.value
            if output_input_ratio_value >= 1 or output_input_ratio_value <= 0:
                raise ValueError("Invalid output/input voltage ratio")

            results = []
            R1_values = []
            for exponent in range(floor(log10(R1.min)), ceil(log10(R1.max))):
                R1_values += [
                    e * 10**exponent
                    for e in e_values
                    if e * 10**exponent >= R1.min and e * 10**exponent <= R1.max
                ]

            for R1_value in R1_values:
                R2_ideal = R1_value / (1 / output_input_ratio_value - 1)

                exponent = floor(log10(R2_ideal))
                e_values_exp = [e * 10**exponent for e in e_values]

                R2_value = min(e_values_exp, key=lambda x: abs(x - R2_ideal))

                real_ratio = R2_value / (R1_value + R2_value)

                results.append((real_ratio, (R1_value, R2_value)))

            optimum = min(results, key=lambda x: abs(x[0] - output_input_ratio_value))
            return optimum[1]

        elif type(output_input_ratio) is Range:
            if (
                output_input_ratio.min >= 1
                or output_input_ratio.min <= 0
                and output_input_ratio.max >= 1
                and output_input_ratio.max <= 0
            ):
                raise ValueError("Invalid output/input voltage ratio")

            target_ratio = (output_input_ratio.max + output_input_ratio.min) / 2

            results = []
            R1_values = []
            for exponent in range(floor(log10(R1.min)), ceil(log10(R1.max))):
                R1_values += [
                    e * 10**exponent
                    for e in e_values
                    if e * 10**exponent >= R1.min and e * 10**exponent <= R1.max
                ]

            for R1_value in R1_values:
                R2_ideal = R1_value / (1 / target_ratio - 1)

                exponent = floor(log10(R2_ideal))
                e_values_exp = [e * 10**exponent for e in e_values]

                R2_value = min(e_values_exp, key=lambda x: abs(x - R2_ideal))

                real_ratio = R2_value / (R1_value + R2_value)

                results.append((real_ratio, (R1_value, R2_value)))

            optimum = min(results, key=lambda x: abs(x[0] - target_ratio))

            logger.debug(
                f"target ratio: {target_ratio:.3f}, optimum ratio: {optimum[0]:.3f}, "
                f"ratio range: {output_input_ratio.min:.3f} - "
                f"{output_input_ratio.max:.3f}"
            )
            if (
                optimum[0] > output_input_ratio.max
                or optimum[0] < output_input_ratio.min
            ):
                raise ValueError(
                    "Calculated optimum R1 R2 value pair gives output/input voltage "
                    "ratio outside of specified range. Consider Increasing the "
                    "output/input range, R1 value range, or using a broader E value "
                    "series"
                )

            return optimum[1]

    raise NotImplementedError
