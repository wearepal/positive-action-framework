from __future__ import annotations
from dataclasses import dataclass
from typing import NamedTuple

import pandas as pd
from torch import Tensor

__all__ = ["Results", "PafResults", "MmdReportingResults"]


@dataclass
class Results:
    pd_results: pd.DataFrame
    x: Tensor
    s: Tensor
    y: Tensor
    cf_x: Tensor
    preds: Tensor
    recon: Tensor
    recons_0: Tensor
    recons_1: Tensor


@dataclass
class PafResults(Results):
    enc_z: Tensor
    clf_z0: Tensor
    clf_z1: Tensor
    clf_z: Tensor
    enc_s_pred: Tensor
    preds_0_0: Tensor
    preds_0_1: Tensor
    preds_1_0: Tensor
    preds_1_1: Tensor
    cycle_loss: Tensor | None
    cyc_vals: pd.DataFrame


class MmdReportingResults(NamedTuple):
    recon: Tensor
    cf_recon: Tensor
    s0_dist: Tensor
    s1_dist: Tensor
