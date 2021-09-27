"""Main script."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from enum import Enum, auto
import logging
from typing import Any, Final, Optional
import warnings

from ethicml import (
    LRCV,
    TNR,
    TPR,
    Accuracy,
    Agarwal,
    DataTuple,
    InAlgorithm,
    Kamiran,
    Prediction,
    ProbPos,
    diff_per_sensitive_attribute,
    metric_per_sensitive_attribute,
    ratio_per_sensitive_attribute,
)
from ethicml.algorithms.inprocess.oracle import Oracle
import hydra
from hydra.core.config_store import ConfigStore
from hydra.utils import instantiate
from omegaconf import DictConfig, MISSING, OmegaConf
import pandas as pd
import pytorch_lightning as pl
import pytorch_lightning.loggers as pll
from sklearn.preprocessing import MinMaxScaler

from paf.architectures import PafModel
from paf.architectures.model import CycleGan, NearestNeighbourModel
from paf.architectures.model.model_components import AE
from paf.architectures.model.naive import NaiveModel
from paf.base_templates.base_module import BaseDataModule
from paf.callbacks.callbacks import L1Logger
from paf.config_classes.conduit.fair.data.configs import (  # type: ignore[import]
    AdmissionsDataModuleConf,
    AdultDataModuleConf,
    CrimeDataModuleConf,
    HealthDataModuleConf,
    LawDataModuleConf,
)
from paf.config_classes.paf.architectures.model.configs import (  # type: ignore[import]
    CycleGanConf,
)
from paf.config_classes.paf.architectures.model.model_components.configs import (  # type: ignore[import]
    AEConf,
    ClfConf,
)
from paf.config_classes.paf.data_modules.configs import (  # type: ignore[import]
    LilliputDataModuleConf,
    SemiAdultDataModuleConf,
    SimpleXDataModuleConf,
    ThirdWayDataModuleConf,
)
from paf.config_classes.pytorch_lightning.trainer.configs import (  # type: ignore[import]
    TrainerConf,
)
from paf.ethicml_extension.oracle import DPOracle
from paf.log_progress import do_log
from paf.plotting import label_plot
from paf.scoring import get_miri_metrics, produce_baselines
from paf.selection import baseline_selection_rules, produce_selection_groups

LOGGER = logging.getLogger(__name__)


class ModelType(Enum):
    PAF = auto()
    NN = auto()


@dataclass
class ExpConfig:
    """Experiment config."""

    lr: float = 1.0e-3
    weight_decay: float = 1.0e-3
    momentum: float = 0.9
    seed: int = 42
    log_offline: Optional[bool] = False
    tags: str = ""
    baseline: bool = False
    model: ModelType = ModelType.PAF


@dataclass
class Config:
    """Base Config Schema."""

    _target_: str = "paf.main.Config"
    data: Any = MISSING
    enc: Any = MISSING  # put config files for this into `conf/model/`
    clf: Any = MISSING  # put config files for this into `conf/model/`
    trainer: Any = MISSING
    exp: ExpConfig = MISSING
    exp_group: Optional[str] = None


warnings.simplefilter(action='ignore', category=RuntimeWarning)

CS = ConfigStore.instance()
CS.store(name="config_schema", node=Config)  # General Schema
CS.store(name="trainer_schema", node=TrainerConf, package="trainer")
CS.store(name="clf_schema", node=ClfConf, package="clf")

ENC_PKG: Final[str] = "enc"
ENC_GROUP: Final[str] = "schema/enc"
CS.store(name="enc_schema", node=AEConf, package=ENC_PKG, group=ENC_GROUP)
CS.store(name="cyclegan", node=CycleGanConf, package=ENC_PKG, group=ENC_GROUP)

DATA_PKG: Final[str] = "data"  # package:dir_within_config_path
DATA_GROUP: Final[str] = "schema/data"  # group
CS.store(name="adult-bolt", node=AdultDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="admiss-bolt", node=AdmissionsDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="crime-bolt", node=CrimeDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="health-bolt", node=HealthDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="law-bolt", node=LawDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="semi-synth", node=SemiAdultDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="lilliput", node=LilliputDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="synth", node=SimpleXDataModuleConf, package=DATA_PKG, group=DATA_GROUP)
CS.store(name="third", node=ThirdWayDataModuleConf, package=DATA_PKG, group=DATA_GROUP)


@hydra.main(config_path="configs", config_name="base_conf")
def launcher(hydra_config: DictConfig) -> None:
    """Instantiate with hydra and get the experiments running!"""
    cfg: Config = instantiate(hydra_config, _recursive_=True, _convert_="partial")
    run_paf(cfg, raw_config=OmegaConf.to_container(hydra_config, resolve=True, enum_to_str=True))


def run_paf(cfg: Config, raw_config: Any) -> None:
    """Run the X Autoencoder."""
    pl.seed_everything(cfg.exp.seed, workers=True)
    data: BaseDataModule = cfg.data
    data.scaler = MinMaxScaler()
    data.prepare_data()
    data.setup()

    LOGGER.info(f"data_dim={data.size()}, num_s={data.card_s}")

    wandb_logger = pll.WandbLogger(
        entity="predictive-analytics-lab",
        project=f"paf_journal_{cfg.exp_group}",
        tags=cfg.exp.tags.split("/")[:-1],
        config=raw_config,
        offline=cfg.exp.log_offline,
    )
    cfg.trainer.logger = wandb_logger

    clf_trainer = copy.deepcopy(cfg.trainer)
    model_trainer = copy.deepcopy(cfg.trainer)
    _model_trainer = copy.deepcopy(cfg.trainer)

    # make_data_plots(data, cfg.trainer.logger)

    encoder = None
    if cfg.exp.model is ModelType.PAF:
        encoder: AE | CycleGan = cfg.enc
        encoder.build(
            num_s=data.card_s,
            data_dim=data.size()[0],
            s_dim=data.dim_s[0],
            cf_available=data.cf_available if hasattr(data, "cf_available") else False,
            feature_groups=data.feature_groups,
            outcome_cols=data.disc_features + data.cont_features,
            scaler=data.scaler,
        )

        enc_trainer = cfg.trainer
        enc_trainer.callbacks += [
            L1Logger(),
            # MmdLogger(),
            # FeaturePlots()
        ]
        enc_trainer.tune(model=encoder, datamodule=data)
        enc_trainer.fit(model=encoder, datamodule=data)
        enc_trainer.test(datamodule=data)

        classifier = cfg.clf
        classifier.build(
            num_s=data.card_s,
            data_dim=data.size()[0],
            s_dim=data.dim_s[0],
            cf_available=data.cf_available if hasattr(data, "cf_available") else False,
            feature_groups=data.feature_groups,
            outcome_cols=data.disc_features + data.cont_features,
            scaler=None,
        )
        clf_trainer.tune(model=classifier, datamodule=data)
        clf_trainer.fit(model=classifier, datamodule=data)
        clf_trainer.test(datamodule=data)

        model = PafModel(encoder=encoder, classifier=classifier)

    elif cfg.exp.model == ModelType.NN:
        classifier = NaiveModel(in_size=cfg.data.size()[0])
        clf_trainer.tune(model=classifier, datamodule=data)
        clf_trainer.fit(model=classifier, datamodule=data)

        model = NearestNeighbourModel(clf_model=classifier, data=data)

    model_trainer.fit(model=model, datamodule=data)
    model_trainer.test(model=model, ckpt_path=None, datamodule=data)

    evaluate(cfg, model, wandb_logger, data, encoder, classifier, _model_trainer)

    if cfg.exp.baseline:
        baseline_models(data, wandb_logger)

    if not cfg.exp.log_offline and wandb_logger is not None:
        wandb_logger.experiment.finish()


def evaluate(
    cfg: Config,
    model: pl.LightningModule,
    wandb_logger: pll.WandbLogger,
    data: BaseDataModule,
    encoder: pl.LightningModule,
    classifier: pl.LightningModule,
    _model_trainer: pl.Trainer,
) -> None:

    for fair_bool in (True, False):
        if cfg.exp.model == ModelType.PAF:
            preds = produce_selection_groups(
                model.pd_results, data, model.recon_0, model.recon_1, wandb_logger
            )
        else:
            preds = baseline_selection_rules(model.pd_results, wandb_logger, fair=fair_bool)
        multiple_metrics(
            preds,
            data.test_datatuple,
            f"{model.name}_{fair_bool=}-Post-Selection",
            wandb_logger,
        )
        if isinstance(data, BaseDataModule) and data.cf_available:
            assert data.true_test_datatuple is not None
            multiple_metrics(
                preds,
                data.true_test_datatuple,
                f"{model.name}_{fair_bool=}-TrueLabels",
                wandb_logger,
            )
            get_miri_metrics(
                method=f"Miri/{model.name}_{fair_bool=}",
                acceptance=DataTuple(
                    x=data.test_datatuple.x.copy(),
                    s=data.test_datatuple.s.copy(),
                    y=preds.hard.to_frame(),
                ),
                graduated=data.true_test_datatuple,
                logger=wandb_logger,
            )

    if cfg.exp.model == ModelType.PAF:
        # === This is only for reporting ====
        _model = PafModel(encoder=encoder, classifier=classifier)
        _model_trainer.test(model=_model, ckpt_path=None, dataloaders=data.train_dataloader())
        produce_selection_groups(
            _model.pd_results, data, _model.recon_0, _model.recon_1, wandb_logger, "Train"
        )
        # === === ===

        our_clf_preds = Prediction(
            hard=pd.Series(model.all_preds.squeeze(-1).detach().cpu().numpy())
        )
        multiple_metrics(
            our_clf_preds,
            data.test_datatuple,
            f"{model.name}-Real-World-Preds",
            wandb_logger,
        )
        if isinstance(data, BaseDataModule) and data.cf_available:
            multiple_metrics(
                our_clf_preds,
                data.test_datatuple,
                f"{model.name}-Real-World-Preds",
                wandb_logger,
            )
            assert data.true_test_datatuple is not None
            get_miri_metrics(
                method=f"Miri/{model.name}-Real-World-Preds",
                acceptance=DataTuple(
                    x=data.test_datatuple.x.copy(),
                    s=data.test_datatuple.s.copy(),
                    y=our_clf_preds.hard.to_frame(),
                ),
                graduated=data.true_test_datatuple,
                logger=wandb_logger,
            )
        if isinstance(cfg.enc, AE) and cfg.trainer.max_epochs > 1:
            produce_baselines(
                encoder=encoder,
                datamodule=data,
                logger=wandb_logger,
                test_mode=cfg.trainer.fast_dev_run,
            )
            produce_baselines(
                encoder=classifier,
                datamodule=data,
                logger=wandb_logger,
                test_mode=cfg.trainer.fast_dev_run,
            )


def baseline_models(data: BaseDataModule, wandb_logger: pll.WandbLogger) -> None:
    baselines: set[InAlgorithm] = {
        # NaiveModel(in_size=data.data_dim[0]),
        LRCV(),
        Oracle(),
        DPOracle(),
        # EqOppOracle(),
        Kamiran(),
        # ZafarFairness(),
        # Kamishima(),
        Agarwal(),
    }
    for base_model in baselines:
        LOGGER.info("=== %s ===", base_model.name)
        try:
            results = base_model.run(data.train_datatuple, data.test_datatuple)
        except ValueError:
            continue
        multiple_metrics(results, data.test_datatuple, base_model.name, wandb_logger)
        if isinstance(data, BaseDataModule):
            LOGGER.info("=== %s and 'True' Data ===", str(base_model.name))
            results = base_model.run(data.train_datatuple, data.test_datatuple)
            assert data.true_test_datatuple is not None
            multiple_metrics(
                results, data.true_test_datatuple, f"{base_model.name}-TrueLabels", wandb_logger
            )
            get_miri_metrics(
                method=f"Miri/{base_model.name}",
                acceptance=DataTuple(
                    x=data.test_datatuple.x.copy(),
                    s=data.test_datatuple.s.copy(),
                    y=results.hard.to_frame(),
                ),
                graduated=data.true_test_datatuple,
                logger=wandb_logger,
            )


def multiple_metrics(
    preds: Prediction, target: DataTuple, name: str, logger: pll.WandbLogger
) -> None:
    """Get multiple metrics."""
    try:
        label_plot(target.replace(y=preds.hard.to_frame()), logger, name)
    except (IndexError, KeyError):
        pass

    for metric in [Accuracy(), ProbPos(), TPR(), TNR()]:
        general_str = f"Results/{name}/{metric.name}"
        do_log(general_str, metric.score(preds, target), logger)
        per_group = metric_per_sensitive_attribute(preds, target, metric)
        for key, result in per_group.items():
            do_log(f"{general_str}-{key}", result, logger)
        for key, result in diff_per_sensitive_attribute(per_group).items():
            do_log(f"{general_str}-Abs-Diff-{key}", result, logger)
        for key, result in ratio_per_sensitive_attribute(per_group).items():
            do_log(
                "{g_str}-Ratio-{k}".format(g_str=general_str, k=key.replace('/', '\\')),
                result,
                logger,
            )


if __name__ == '__main__':
    launcher()
