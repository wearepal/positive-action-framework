"""Test the selection rules."""

import numpy as np
import pandas as pd
import torch

from paf.selection import produce_selection_groups, selection_rules
from paf.utils import facct_mapper, facct_mapper_2, facct_mapper_outcomes


def test_sr() -> None:

    s0s0 = torch.tensor(
        [
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
        ]
    ).unsqueeze(-1)

    s0s1 = torch.tensor(
        [
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
        ]
    ).unsqueeze(-1)

    s1s0 = torch.tensor(
        [
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
        ]
    ).unsqueeze(-1)

    s1s1 = torch.tensor(
        [
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
        ]
    ).unsqueeze(-1)

    trues = torch.tensor(
        [
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
        ]
    ).unsqueeze(-1)

    act = torch.tensor(
        [
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
        ]
    ).unsqueeze(-1)

    group = torch.tensor(
        [
            0,
            0,
            1,
            1,
            2,
            2,
            3,
            3,
            4,
            4,
            5,
            5,
            6,
            6,
            7,
            7,
            8,
            8,
            9,
            9,
            10,
            10,
            11,
            11,
            12,
            12,
            13,
            13,
            14,
            14,
            15,
            15,
            16,
            16,
            17,
            17,
            18,
            18,
            19,
            19,
            20,
            20,
            21,
            21,
            22,
            22,
            23,
            23,
            24,
            24,
            25,
            25,
            26,
            26,
            27,
            27,
            28,
            28,
            29,
            29,
            30,
            30,
            31,
            31,
        ]
    ).unsqueeze(-1)

    next_map = torch.tensor(
        [
            5,
            5,
            6,
            6,
            3,
            3,
            4,
            4,
            7,
            7,
            7,
            7,
            3,
            3,
            4,
            4,
            7,
            7,
            7,
            7,
            1,
            1,
            4,
            4,
            7,
            7,
            7,
            7,
            1,
            1,
            2,
            2,
            8,
            8,
            7,
            7,
            8,
            8,
            8,
            8,
            8,
            8,
            7,
            7,
            8,
            8,
            8,
            8,
            8,
            8,
            7,
            7,
            8,
            8,
            8,
            8,
            8,
            8,
            7,
            7,
            1,
            1,
            2,
            2,
        ]
    ).unsqueeze(-1)

    outcome = torch.tensor(
        [
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
        ]
    ).unsqueeze(-1)

    fair_out = torch.tensor(
        [
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            1,
            1,
            1,
        ]
    ).unsqueeze(-1)

    pd_results = pd.DataFrame(
        torch.cat([s0s0, s0s1, s1s0, s1s1, trues, act], dim=1).cpu().numpy(),
        columns=["s1_0_s2_0", "s1_0_s2_1", "s1_1_s2_0", "s1_1_s2_1", "true_s", "actual"],
    )

    decision = selection_rules(pd_results)

    np.testing.assert_array_equal(decision, group.squeeze(-1).cpu().numpy())

    to_return = facct_mapper(pd.Series(decision))

    pd.testing.assert_series_equal(to_return, pd.Series(next_map.squeeze(-1).cpu().numpy()))

    next_up = facct_mapper_outcomes(facct_mapper_2(to_return), fair=False)

    pd.testing.assert_series_equal(next_up, pd.Series(outcome.squeeze(-1).cpu().numpy()))

    preds = produce_selection_groups(outcomes=pd_results, data=None, data_name="test")

    pd.testing.assert_series_equal(
        pd.Series(preds.hard.values), pd.Series(outcome.squeeze(-1).cpu().numpy())
    )

    next_up = facct_mapper_outcomes(facct_mapper_2(to_return), fair=True)

    pd.testing.assert_series_equal(next_up, pd.Series(fair_out.squeeze(-1).cpu().numpy()))

    preds = produce_selection_groups(outcomes=pd_results, data=None, fair=True, data_name="test")

    pd.testing.assert_series_equal(
        pd.Series(preds.hard.values), pd.Series(fair_out.squeeze(-1).cpu().numpy())
    )
