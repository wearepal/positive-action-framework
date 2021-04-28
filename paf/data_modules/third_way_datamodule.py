"""Data Module for simple data."""
import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from ethicml import Prediction, implements
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader

from paf.base_templates.base_module import BaseDataModule
from paf.base_templates.dataset_utils import CFDataTupleDataset
from paf.datasets.third_way import third_way_data
from paf.selection import selection_rules
from paf.utils import facct_mapper

log = logging.getLogger(__name__)


class ThirdWayDataModule(BaseDataModule):
    """Simple 1d, configurable, data."""

    def __init__(
        self,
        acceptance_rate: float,
        alpha: float,
        beta: float,
        gamma: float,
        seed: int,
        num_samples: int,
        num_workers: int,
        batch_size: int,
        num_features: int,
        xi: float,
        num_hidden_features: int,
        cf_available: bool = True,
        train_dims: Optional[Tuple[int, ...]] = None,
    ):
        super().__init__()
        self.acceptance_rate = acceptance_rate
        self.alpha = alpha
        self.beta = beta
        self._cf_available = cf_available
        self.gamma = gamma
        self.seed = seed
        self.num_samples = num_samples
        self.train_dims = train_dims
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.num_features = num_features
        self.xi = xi
        self.num_hidden_features = num_hidden_features

    @implements(LightningDataModule)
    def prepare_data(self) -> None:
        # called only on 1 GPU
        (
            dataset,
            factual_data,
            cf_data,
            data_true_outcome,
            s1_0_s2_0_data,
            s1_0_s2_1_data,
            s1_1_s2_0_data,
            s1_1_s2_1_data,
        ) = third_way_data(
            seed=self.seed,
            num_samples=self.num_samples,
            acceptance_rate=self.acceptance_rate,
            alpha=self.alpha,
            gamma=self.gamma,
            random_shift=0,
            binary_s=1,
            num_features=self.num_features,
            beta=self.beta,
            xi=self.xi,
            num_hidden_features=self.num_hidden_features,
        )
        self.dataset = dataset
        self.factual_data = factual_data
        self.cf_data = cf_data
        self.s1_0_s2_0_data = s1_0_s2_0_data
        self.s1_0_s2_1_data = s1_0_s2_1_data
        self.s1_1_s2_0_data = s1_1_s2_0_data
        self.s1_1_s2_1_data = s1_1_s2_1_data
        self.num_s = factual_data.s.nunique().values[0]
        self.data_dim = factual_data.x.shape[1]
        self.s_dim = factual_data.s.shape[1]
        self.column_names = factual_data.x.columns
        self.outcome_columns = factual_data.y.columns

        num_train = int(self.factual_data.x.shape[0] * 0.8)
        num_val = 0  # int(self.factual_data.x.shape[0] * 0.1)
        rng = np.random.RandomState(self.seed)
        idx = rng.permutation(self.factual_data.x.index)
        train_indices = idx[:num_train]
        val_indices = idx[num_train : num_train + num_val]
        test_indices = idx[num_train + num_val :]

        self.make_feature_groups(dataset, factual_data)

        self.train_data, self.val_data, self.test_data = self.scale_and_split(
            self.factual_data, dataset, train_indices, val_indices, test_indices
        )
        self.true_train_data, self.true_val_data, self.true_test_data = self.scale_and_split(
            data_true_outcome, dataset, train_indices, val_indices, test_indices
        )
        self.cf_train, self.cf_val, self.cf_test = self.scale_and_split(
            self.cf_data, dataset, train_indices, val_indices, test_indices
        )
        self.s1_0_s2_0_train, self.s1_0_s2_0_val, self.s1_0_s2_0_test = self.scale_and_split(
            self.s1_0_s2_0_data, dataset, train_indices, val_indices, test_indices
        )
        self.s1_0_s2_1_train, self.s1_0_s2_1_val, self.s1_0_s2_1_test = self.scale_and_split(
            self.s1_0_s2_1_data, dataset, train_indices, val_indices, test_indices
        )
        self.s1_1_s2_0_train, self.s1_1_s2_0_val, self.s1_1_s2_0_test = self.scale_and_split(
            self.s1_1_s2_0_data, dataset, train_indices, val_indices, test_indices
        )
        self.s1_1_s2_1_train, self.s1_1_s2_1_val, self.s1_1_s2_1_test = self.scale_and_split(
            self.s1_1_s2_1_data, dataset, train_indices, val_indices, test_indices
        )

        pd_results = pd.concat(
            [
                self.s1_0_s2_0_test.y.rename(columns={"outcome": "s1_0_s2_0"}),
                self.s1_0_s2_1_test.y.rename(columns={"outcome": "s1_0_s2_1"}),
                self.s1_1_s2_0_test.y.rename(columns={"outcome": "s1_1_s2_0"}),
                self.s1_1_s2_1_test.y.rename(columns={"outcome": "s1_1_s2_1"}),
                self.test_data.s.rename(columns={"sens": "true_s"}),
                self.test_data.y.rename(columns={"outcome": "actual"}),
            ],
            axis=1,
        )
        log.info(pd_results.info)

        pd_results["decision"] = selection_rules(pd_results)
        log.info(pd_results["decision"].value_counts())
        asdfasdf = facct_mapper(Prediction(hard=pd_results["decision"]))
        log.info(asdfasdf.info)

    # def scale_and_split(
    #     self,
    #     datatuple: DataTuple,
    #     dataset: Dataset,
    #     train_indices: np.ndarray,
    #     test_indices: np.ndarray,
    # ) -> Tuple[DataTuple, DataTuple]:
    #     """Scale a datatuple and split to train/test."""
    #     train = DataTuple(
    #         x=datatuple.x.iloc[train_indices].reset_index(drop=True),
    #         s=datatuple.s.iloc[train_indices].reset_index(drop=True),
    #         y=datatuple.y.iloc[train_indices].reset_index(drop=True),
    #     )
    #     test = DataTuple(
    #         x=datatuple.x.iloc[test_indices].reset_index(drop=True),
    #         s=datatuple.s.iloc[test_indices].reset_index(drop=True),
    #         y=datatuple.y.iloc[test_indices].reset_index(drop=True),
    #     )
    #
    #     scaler = MinMaxScaler()
    #     scaler = scaler.fit(train.x[dataset.continuous_features])
    #     train.x[dataset.continuous_features] = scaler.transform(
    #         train.x[dataset.continuous_features]
    #     )
    #     test.x[dataset.continuous_features] = scaler.transform(test.x[dataset.continuous_features])
    #     return train, test

    @implements(BaseDataModule)
    def _train_dataloader(self, shuffle: bool = False, drop_last: bool = False) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                self.train_data,
                cf_dataset=self.cf_train,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.continuous_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=shuffle,
            drop_last=drop_last,
        )

    @implements(BaseDataModule)
    def _val_dataloader(self, shuffle: bool = False, drop_last: bool = False) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                self.val_data,
                cf_dataset=self.cf_val,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.continuous_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=shuffle,
            drop_last=drop_last,
        )

    @implements(BaseDataModule)
    def _test_dataloader(self, shuffle: bool = False, drop_last: bool = False) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                self.test_data,
                cf_dataset=self.cf_test,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.continuous_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=shuffle,
            drop_last=drop_last,
        )