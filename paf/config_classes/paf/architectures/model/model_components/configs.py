# Generated by configen, do not edit.
# See https://github.com/facebookresearch/hydra/tree/master/tools/configen
# fmt: off
# isort:skip_file
# flake8: noqa

from dataclasses import dataclass, field
from omegaconf import MISSING
from paf.mmd import KernelType
from typing import Any


@dataclass
class AEConf:
    _target_: str = "paf.architectures.model.model_components.AE"
    s_as_input: bool = MISSING
    latent_dims: int = MISSING
    encoder_blocks: int = MISSING
    latent_multiplier: int = MISSING
    adv_blocks: int = MISSING
    decoder_blocks: int = MISSING
    adv_weight: float = MISSING
    mmd_weight: float = MISSING
    cycle_weight: float = MISSING
    target_weight: float = MISSING
    proxy_weight: float = MISSING
    lr: float = MISSING
    mmd_kernel: KernelType = MISSING
    scheduler_rate: float = MISSING
    weight_decay: float = MISSING
    debug: bool = MISSING


@dataclass
class ClfConf:
    _target_: str = "paf.architectures.model.model_components.Clf"
    adv_weight: float = MISSING
    pred_weight: float = MISSING
    mmd_weight: float = MISSING
    lr: float = MISSING
    s_as_input: bool = MISSING
    latent_dims: int = MISSING
    mmd_kernel: Any = MISSING  # Union[str, KernelType]
    scheduler_rate: float = MISSING
    weight_decay: float = MISSING
    use_iw: bool = MISSING
    encoder_blocks: int = MISSING
    adv_blocks: int = MISSING
    decoder_blocks: int = MISSING
    latent_multiplier: int = MISSING
    debug: bool = MISSING
