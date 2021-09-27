"""Basic tests."""
from __future__ import annotations
import copy
from typing import Final

from hydra.core.config_store import ConfigStore
from hydra.experimental import compose, initialize
from hydra.utils import instantiate
from omegaconf import OmegaConf
import pytest
import pytorch_lightning as pl
from sklearn.preprocessing import MinMaxScaler
import torch

from paf.architectures.paf_model import PafModel
from paf.config_classes.paf.data_modules.configs import (  # type: ignore[import]
    LilliputDataModuleConf,
    SimpleAdultDataModuleConf,
    SimpleXDataModuleConf,
    ThirdWayDataModuleConf,
)
from paf.config_classes.pytorch_lightning.trainer.configs import (  # type: ignore[import]
    TrainerConf,
)
from paf.main import Config, run_paf

cs = ConfigStore.instance()
cs.store(name="config_schema", node=Config)  # General Schema
cs.store(name="trainer_schema", node=TrainerConf, package="trainer")

CFG_PTH: Final[str] = "../paf/configs"
SCHEMAS: Final[list[str]] = [
    "enc=basic",
    "clf=basic",
    "exp=unit_test",
    "trainer=unit_test",
]


@pytest.mark.parametrize(
    "dm_schema", ["ad", "adm", "law", "semi", "lill", "synth"]  # "crime", "health"
)
def test_with_initialize(dm_schema: str) -> None:
    """Quick run on models to check nothing's broken."""
    with initialize(config_path=CFG_PTH):
        # config is relative to a module
        hydra_cfg = compose(
            config_name="base_conf",
            overrides=[f"data={dm_schema}"] + SCHEMAS,
        )
        cfg: Config = instantiate(hydra_cfg, _recursive_=True, _convert_="partial")
        run_paf(cfg, raw_config=OmegaConf.to_container(hydra_cfg, resolve=True, enum_to_str=True))


@pytest.mark.parametrize(
    "dm_schema,cf_available",
    [
        ("third", True),
        ("lill", True),
        ("synth", True),
        ("ad", False),
        ("adm", False),
        ("crime", False),
        ("law", False),
        ("health", False),
    ],
)
def test_data(dm_schema: str, cf_available: bool) -> None:
    """Test the data module."""
    with initialize(config_path="../paf/configs"):
        # config is relative to a module
        hydra_cfg = compose(
            config_name="base_conf",
            overrides=[f"data={dm_schema}"] + SCHEMAS,
        )
        cfg: Config = instantiate(hydra_cfg, _recursive_=True, _convert_="partial")
        pl.seed_everything(0)

        cfg.data.prepare_data()
        cfg.data.setup()

        assert cf_available == (
            cfg.data.cf_available if hasattr(cfg.data, "cf_available") else False
        )

        assert cfg.data.card_s == 2
        assert cfg.data.card_y == 2

        for batch in cfg.data.train_dataloader():
            if cf_available:
                with pytest.raises(AssertionError):
                    torch.testing.assert_allclose(batch.x, batch.cfx)
                with pytest.raises(AssertionError):
                    torch.testing.assert_allclose(batch.s, batch.cfs)
                with pytest.raises(AssertionError):
                    torch.testing.assert_allclose(batch.y, batch.cfy)
            else:
                torch.testing.assert_allclose(batch.x, batch.x)
                torch.testing.assert_allclose(batch.s, batch.s)
                torch.testing.assert_allclose(batch.y, batch.y)


@pytest.mark.parametrize(
    "dm_schema,cf_available", [("third", True), ("lill", True), ("synth", True), ("ad", False)]
)
def test_datamods(dm_schema: str, cf_available: bool) -> None:
    """Test the flip dataset function."""
    with initialize(config_path=CFG_PTH):
        # config is relative to a module
        hydra_cfg = compose(
            config_name="base_conf",
            overrides=[f"data={dm_schema}"] + SCHEMAS,
        )
        cfg: Config = instantiate(hydra_cfg, _recursive_=True, _convert_="partial")
        pl.seed_everything(0)
        data = cfg.data
        data.prepare_data()
        cfg.data.setup()

        training_dl = data.train_dataloader(shuffle=False, drop_last=False)
        training_dl2 = data.test_dataloader()

        for (tr_batch, te_batch) in zip(training_dl, training_dl2):
            with pytest.raises(AssertionError):
                torch.testing.assert_allclose(tr_batch.x, te_batch.x)


@pytest.mark.parametrize("dm_schema", ["third", "lill", "synth", "adm", "ad"])
def test_enc(dm_schema: str) -> None:
    """Test the encoder network runs."""
    with initialize(config_path=CFG_PTH):
        # config is relative to a module
        hydra_cfg = compose(
            config_name="base_conf",
            overrides=[f"data={dm_schema}"] + SCHEMAS,
        )
        cfg: Config = instantiate(hydra_cfg, _recursive_=True, _convert_="partial")
        cfg.data.scaler = MinMaxScaler()

        cfg.data.prepare_data()
        cfg.data.setup()
        encoder = cfg.enc
        encoder.build(
            num_s=cfg.data.card_s,
            data_dim=cfg.data.size()[0],
            s_dim=cfg.data.dim_s[0],
            cf_available=cfg.data.cf_available if hasattr(cfg.data, "cf_available") else False,
            feature_groups=cfg.data.feature_groups,
            outcome_cols=cfg.data.disc_features + cfg.data.cont_features,
            scaler=cfg.data.scaler,
        )
        cfg.trainer.fit(model=encoder, datamodule=cfg.data)
        cfg.trainer.test(model=encoder, ckpt_path=None, datamodule=cfg.data)


@pytest.mark.parametrize("dm_schema", ["third", "lill", "synth", "ad"])
def test_clf(dm_schema: str) -> None:
    """Test the classifier network runs."""
    with initialize(config_path=CFG_PTH):
        # config is relative to a module
        hydra_cfg = compose(
            config_name="base_conf",
            overrides=[f"data={dm_schema}"] + SCHEMAS,
        )
        cfg: Config = instantiate(hydra_cfg, _recursive_=True, _convert_="partial")
        cfg.data.scaler = MinMaxScaler()

        cfg.data.prepare_data()
        cfg.data.setup()
        classifier = cfg.clf
        classifier.build(
            num_s=cfg.data.card_s,
            data_dim=cfg.data.size()[0],
            s_dim=cfg.data.dim_s[0],
            cf_available=cfg.data.cf_available if hasattr(cfg.data, "cf_available") else False,
            feature_groups=cfg.data.feature_groups,
            outcome_cols=cfg.data.disc_features + cfg.data.cont_features,
            scaler=cfg.data.scaler,
        )
        cfg.trainer.fit(model=classifier, datamodule=cfg.data)
        cfg.trainer.test(model=classifier, ckpt_path=None, datamodule=cfg.data)


@pytest.mark.parametrize("dm_schema", ["third", "lill", "synth", "ad"])
def test_clfmod(dm_schema: str) -> None:
    """Test the end to end."""
    with initialize(config_path=CFG_PTH):
        # config is relative to a module
        hydra_cfg = compose(
            config_name="base_conf",
            overrides=[f"data={dm_schema}"] + SCHEMAS,
        )
        cfg: Config = instantiate(hydra_cfg, _recursive_=True, _convert_="partial")
        cfg.data.scaler = MinMaxScaler()

        enc_trainer = copy.deepcopy(cfg.trainer)
        clf_trainer = copy.deepcopy(cfg.trainer)
        model_trainer = copy.deepcopy(cfg.trainer)

        data = cfg.data
        data.prepare_data()
        data.setup()
        encoder = cfg.enc
        encoder.build(
            num_s=data.card_s,
            data_dim=data.size()[0],
            s_dim=data.dim_s[0],
            cf_available=cfg.data.cf_available if hasattr(cfg.data, "cf_available") else False,
            feature_groups=data.feature_groups,
            outcome_cols=cfg.data.disc_features + cfg.data.cont_features,
            scaler=cfg.data.scaler,
        )
        enc_trainer.fit(model=encoder, datamodule=data)
        enc_trainer.test(model=encoder, ckpt_path=None, datamodule=data)

        classifier = cfg.clf
        classifier.build(
            num_s=data.card_s,
            data_dim=data.size()[0],
            s_dim=data.dim_s[0],
            cf_available=cfg.data.cf_available if hasattr(cfg.data, "cf_available") else False,
            feature_groups=data.feature_groups,
            outcome_cols=cfg.data.disc_features + cfg.data.cont_features,
            scaler=cfg.data.scaler,
        )
        clf_trainer.fit(model=classifier, datamodule=data)
        clf_trainer.test(model=classifier, ckpt_path=None, datamodule=data)

        model = PafModel(encoder=encoder, classifier=classifier)
        model_trainer.fit(model=model, datamodule=data)
        model_trainer.test(model=model, ckpt_path=None, datamodule=data)

        print(model.pd_results)
