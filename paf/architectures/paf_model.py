"""AIES Model."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from conduit.data import TernarySample
import pandas as pd
import pytorch_lightning as pl
from ranzen import implements
import torch
from torch import Tensor, nn
from torch.optim.lr_scheduler import ExponentialLR

__all__ = ["PafModel", "TestStepOut"]

from tqdm import tqdm

from paf.base_templates import Batch, CfBatch

from . import PafResults
from .model import CycleGan, NearestNeighbour
from .model.model_components import AE, Clf, augment_recons, index_by_s


@dataclass
class TestStepOut:
    enc_z: Tensor
    clf_z0: Tensor
    clf_z1: Tensor
    enc_s_pred: Tensor
    x: Tensor
    s: Tensor
    y: Tensor
    recon: Tensor
    cf_recon: Tensor
    recons_0: Tensor
    recons_1: Tensor
    preds: Tensor
    preds_0_0: Tensor
    preds_0_1: Tensor
    preds_1_0: Tensor
    preds_1_1: Tensor


class PafModel(pl.LightningModule):
    """Model."""

    def __init__(self, *, encoder: AE | CycleGan, classifier: Clf):
        super().__init__()
        self.enc = encoder
        self.clf = classifier

    @property
    def name(self) -> str:
        return f"PAF_{self.enc.name}"

    @implements(nn.Module)
    @torch.no_grad()
    def forward(self, *, x: Tensor, s: Tensor) -> dict[str, tuple[Tensor, ...]]:
        recons: list[Tensor] | None = None
        if isinstance(self.enc, AE):
            enc_fwd = self.enc.forward(x=x, s=s)
            recons = enc_fwd.x
        elif isinstance(self.enc, CycleGan):
            cyc_fwd = self.enc.forward(real_s0=x, real_s1=x)
            recons = [cyc_fwd.fake_s0, cyc_fwd.fake_s1]
        assert recons is not None
        return self.clf.from_recons(recons)

    @implements(pl.LightningModule)
    def training_step(self, batch: tuple[Tensor, ...], batch_idx: int) -> Tensor:
        """Empty as we do not train the model end to end."""

    @implements(pl.LightningModule)
    def configure_optimizers(self) -> tuple[list[torch.optim.Optimizer], list[ExponentialLR]]:
        """Empty as we do not train the model end to end."""

    @implements(pl.LightningModule)
    def predict_step(self, batch: Batch | CfBatch | TernarySample, *_: Any) -> TestStepOut:
        if isinstance(self.enc, AE):
            constraint_mask = torch.zeros_like(batch.x)
            constraint_mask[:, self.enc.indices] += 1
            enc_fwd = self.enc.forward(x=batch.x, s=batch.s, constraint_mask=constraint_mask)
            enc_z = enc_fwd.z
            enc_s_pred = enc_fwd.s
            recons = enc_fwd.x
        elif isinstance(self.enc, CycleGan):
            cyc_fwd = self.enc.forward(
                real_s0=torch.cat([batch.x, batch.s.unsqueeze(dim=-1)], dim=1)
                if self.enc.s_as_input
                else batch.x,
                real_s1=torch.cat([batch.x, batch.s.unsqueeze(dim=-1)], dim=1)
                if self.enc.s_as_input
                else batch.x,
            )
            recons = [
                cyc_fwd.fake_s0[:, :-1] if self.enc.s_as_input else cyc_fwd.fake_s0,
                cyc_fwd.fake_s1[:, :-1] if self.enc.s_as_input else cyc_fwd.fake_s1,
            ]
            enc_z = torch.ones_like(batch.x)
            enc_s_pred = torch.ones_like(batch.s)
        elif isinstance(self.enc, NearestNeighbour):
            recons = self.enc.forward(x=batch.x, s=batch.s).x
            enc_z = torch.ones_like(batch.x)
            enc_s_pred = torch.ones_like(batch.s)
        else:
            raise NotImplementedError()
        augmented_recons = augment_recons(
            batch.x, self.enc.invert(index_by_s(recons, 1 - batch.s), batch.x), batch.s
        )

        vals: dict[str, Tensor | dict[str, Tensor]] = {
            "enc_z": enc_z,
            "enc_s_pred": enc_s_pred,
            "x": batch.x,
            "s": batch.s,
            "y": batch.y,
            "recon": index_by_s(augmented_recons, batch.s),
            "cf_recon": index_by_s(augmented_recons, 1 - batch.s),
            "recons_0": self.enc.invert(recons[0], batch.x),
            "recons_1": self.enc.invert(recons[1], batch.x),
            "preds": self.clf.threshold(
                index_by_s(self.clf.forward(x=batch.x, s=batch.s)[-1], batch.s)
            ),
        }

        for i, recon in enumerate(augmented_recons):
            clf_out = self.clf.forward(x=recon, s=torch.ones_like(batch.s) * i)
            vals[f"clf_z{i}"] = clf_out.z
            vals.update({f"preds_{i}_{j}": self.clf.threshold(clf_out.y[j]) for j in range(2)})
        return TestStepOut(**vals)

    def collate_results(self, outputs: list[TestStepOut], *, cycle_steps: int = 0) -> PafResults:
        preds_0_0 = torch.cat([_r.preds_0_0 for _r in outputs], 0)
        preds_0_1 = torch.cat([_r.preds_0_1 for _r in outputs], 0)
        preds_1_0 = torch.cat([_r.preds_1_0 for _r in outputs], 0)
        preds_1_1 = torch.cat([_r.preds_1_1 for _r in outputs], 0)
        x = torch.cat([_r.x for _r in outputs], 0)
        s = torch.cat([_r.s for _r in outputs], 0)
        preds = torch.cat([_r.preds for _r in outputs], 0)
        clf_z0 = torch.cat([_r.clf_z0 for _r in outputs], 0)
        clf_z1 = torch.cat([_r.clf_z1 for _r in outputs], 0)

        recons = torch.cat([_r.recon for _r in outputs], 0)
        recons_0 = torch.cat([_r.recons_0 for _r in outputs], 0)
        recons_1 = torch.cat([_r.recons_1 for _r in outputs], 0)

        mse_loss_fn = nn.MSELoss(reduction="none")
        _recons = [recons_0.clone(), recons_1.clone()]
        torch.tensor(0.0)
        cyc_dict = {}

        cycle_loss = None
        for i in tqdm(range(cycle_steps), desc="Cycle Measure"):
            _cfx = self.enc.invert(index_by_s(_recons, 1 - s), x).cpu()
            if isinstance(self.enc, (AE, NearestNeighbour)):
                cf_fwd = self.enc.forward(x=_cfx, s=1 - s.cpu())
                _og = self.enc.invert(index_by_s(cf_fwd.x, s), x)
            else:
                cf_fwd = self.enc.forward(
                    real_s0=torch.cat([_cfx, s.unsqueeze(dim=-1)], dim=1)
                    if self.enc.s_as_input
                    else _cfx,
                    real_s1=torch.cat([_cfx, s.unsqueeze(dim=-1)], dim=1)
                    if self.enc.s_as_input
                    else _cfx,
                )
                recon = index_by_s(cf_fwd.x, s)
                _og = self.enc.invert(recon[:, :-1] if self.enc.s_as_input else recon)
            cycle_loss = mse_loss_fn(_og, x.cpu())
            cyc_dict[f"Cycle_loss/{i}"] = cycle_loss.detach().mean(dim=-1).cpu().numpy().tolist()
            if isinstance(self.enc, (AE, NearestNeighbour)):
                _fwd = self.enc.forward(x=_og, s=1 - s.cpu())
                _recons = _fwd.x
            else:
                _fwd = self.enc.forward(
                    real_s0=torch.cat([_og, s.unsqueeze(dim=-1)], dim=1)
                    if self.enc.s_as_input
                    else _og,
                    real_s1=torch.cat([_og, s.unsqueeze(dim=-1)], dim=1)
                    if self.enc.s_as_input
                    else _og,
                )
                _recons = [_fwd.x[0][:, :-1], _fwd.x[1][:, :-1]] if self.enc.s_as_input else _fwd.x

        return PafResults(
            enc_z=torch.cat([_r.enc_z for _r in outputs], 0),
            enc_s_pred=torch.cat([_r.enc_s_pred for _r in outputs], 0),
            clf_z0=clf_z0,
            clf_z1=clf_z1,
            clf_z=torch.cat([clf_z0, clf_z1], dim=0),
            s=s,
            x=x,
            y=torch.cat([_r.y for _r in outputs], 0),
            recon=recons,
            cf_x=torch.cat([_r.cf_recon for _r in outputs], 0),
            recons_0=recons_0,
            recons_1=recons_1,
            preds=preds,
            preds_0_0=preds_0_0,
            preds_0_1=preds_0_1,
            preds_1_0=preds_1_0,
            preds_1_1=preds_1_1,
            pd_results=pd.DataFrame(
                torch.cat(
                    [
                        preds_0_0,
                        preds_0_1,
                        preds_1_0,
                        preds_1_1,
                        s.unsqueeze(-1),
                        preds,
                    ],
                    dim=1,
                )
                .to(torch.long)
                .cpu()
                .numpy(),
                columns=["s1_0_s2_0", "s1_0_s2_1", "s1_1_s2_0", "s1_1_s2_1", "true_s", "actual"],
            ),
            cycle_loss=cycle_loss,
            cyc_vals=pd.DataFrame.from_dict(cyc_dict),
        )
