# Generated by configen, do not edit.
# See https://github.com/facebookresearch/hydra/tree/master/tools/configen
# fmt: off
# isort:skip_file
# flake8: noqa

from dataclasses import dataclass
from bolts.fair.data.datamodules.tabular.admissions import AdmissionsSens
from bolts.fair.data.datamodules.tabular.adult import AdultSens
from bolts.fair.data.datamodules.tabular.crime import CrimeSens
from bolts.fair.data.datamodules.tabular.health import HealthSens
from bolts.fair.data.datamodules.tabular.law import LawSens
from kit.torch.data import TrainingMode
from typing import Any


@dataclass
class AdultDataModuleConf:
    _target_: str = "bolts.fair.data.AdultDataModule"
    bin_nationality: bool = False
    sens_feat: AdultSens = AdultSens.sex
    bin_race: bool = False
    discrete_feats_only: bool = False
    batch_size: int = 100
    num_workers: int = 0
    val_prop: float = 0.2
    test_prop: float = 0.2
    seed: int = 0
    persist_workers: bool = False
    pin_memory: bool = True
    stratified_sampling: bool = False
    instance_weighting: bool = False
    scaler: Any = None  # Optional[ScalerType]
    training_mode: TrainingMode = TrainingMode.epoch


@dataclass
class AdmissionsDataModuleConf:
    _target_: str = "bolts.fair.data.AdmissionsDataModule"
    sens_feat: AdmissionsSens = AdmissionsSens.gender
    disc_feats_only: bool = False
    batch_size: int = 100
    num_workers: int = 0
    val_prop: float = 0.2
    test_prop: float = 0.2
    seed: int = 0
    persist_workers: bool = False
    pin_memory: bool = True
    stratified_sampling: bool = False
    instance_weighting: bool = False
    scaler: Any = None  # Optional[ScalerType]
    training_mode: TrainingMode = TrainingMode.epoch


@dataclass
class LawDataModuleConf:
    _target_: str = "bolts.fair.data.LawDataModule"
    sens_feat: LawSens = LawSens.sex
    discrete_feats_only: bool = False
    batch_size: int = 100
    num_workers: int = 0
    val_prop: float = 0.2
    test_prop: float = 0.2
    seed: int = 0
    persist_workers: bool = False
    pin_memory: bool = True
    stratified_sampling: bool = False
    instance_weighting: bool = False
    scaler: Any = None  # Optional[ScalerType]
    training_mode: TrainingMode = TrainingMode.epoch


@dataclass
class CrimeDataModuleConf:
    _target_: str = "bolts.fair.data.CrimeDataModule"
    sens_feat: CrimeSens = CrimeSens.raceBinary
    disc_feats_only: bool = False
    batch_size: int = 100
    num_workers: int = 0
    val_prop: float = 0.2
    test_prop: float = 0.2
    seed: int = 0
    persist_workers: bool = False
    pin_memory: bool = True
    stratified_sampling: bool = False
    instance_weighting: bool = False
    scaler: Any = None  # Optional[ScalerType]
    training_mode: TrainingMode = TrainingMode.epoch


@dataclass
class HealthDataModuleConf:
    _target_: str = "bolts.fair.data.HealthDataModule"
    sens_feat: HealthSens = HealthSens.sex
    disc_feats_only: bool = False
    batch_size: int = 100
    num_workers: int = 0
    val_prop: float = 0.2
    test_prop: float = 0.2
    seed: int = 0
    persist_workers: bool = False
    pin_memory: bool = True
    stratified_sampling: bool = False
    instance_weighting: bool = False
    scaler: Any = None  # Optional[ScalerType]
    training_mode: TrainingMode = TrainingMode.epoch
