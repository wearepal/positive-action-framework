"""Data Module for simple data."""
from __future__ import annotations
from typing import Optional, Tuple

from kit import implements, parsable
import numpy as np
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader

from paf.base_templates.base_module import BaseDataModule
from paf.base_templates.dataset_utils import CFDataTupleDataset
from paf.datasets.lilliput import lilliput


class LilliputDataModule(BaseDataModule):
    """Simple 1d, configurable, data."""

    @parsable
    def __init__(
        self,
        alpha: float,
        gamma: float,
        seed: int,
        num_samples: int,
        num_workers: int,
        batch_size: int,
        cf_available: bool = True,
        train_dims: Optional[Tuple[int, ...]] = None,
    ):
        super().__init__()
        self.alpha = alpha
        self._cf_available = cf_available
        self.gamma = gamma
        self.seed = seed
        self.num_samples = num_samples
        self.train_dims = train_dims
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.scaler = None

    @implements(LightningDataModule)
    def prepare_data(self) -> None:
        # called only on 1 GPU
        (
            dataset,
            factual_data,
            cf_data,
            data_true_outcome,
            best_guess,
            s0s0,
            s0s1,
            s1s0,
            s1s1,
        ) = lilliput(
            seed=self.seed, alpha=self.alpha, num_samples=self.num_samples, gamma=self.gamma
        )
        self.best_guess = best_guess
        self.s0_s0 = s0s0
        self.s0_s1 = s0s1
        self.s1_s0 = s1s0
        self.s1_s1 = s1s1
        self.dataset = dataset
        self.factual_data = factual_data
        self.cf_data = cf_data
        self.card_s = factual_data.s.nunique().values[0]
        self.card_y = factual_data.y.nunique().values[0]
        self.data_dim = factual_data.x.shape[1:]
        self.dim_x = self.data_dim
        self.dims = self.data_dim
        self.dim_s = (1,) if self.factual_data.s.ndim == 1 else self.factual_data.s.shape[1:]
        self.column_names = [str(col) for col in factual_data.x.columns]
        self.outcome_columns = [str(col) for col in factual_data.y.columns]

        num_train = int(self.factual_data.x.shape[0] * 0.7)
        num_val = int(self.factual_data.x.shape[0] * 0.1)
        rng = np.random.RandomState(self.seed)
        idx = rng.permutation(self.factual_data.x.index)
        train_indices = idx[:num_train]
        val_indices = idx[num_train : num_train + num_val]
        test_indices = idx[num_train + num_val :]

        scale_split = self.scale_and_split(
            self.factual_data, dataset, train_indices, val_indices, test_indices
        )
        self.train_datatuple = scale_split.train
        self.val_datatuple = scale_split.val
        self.test_datatuple = scale_split.test

        true_scale_split = self.scale_and_split(
            data_true_outcome, dataset, train_indices, val_indices, test_indices
        )
        self.true_train_datatuple = true_scale_split.train
        self.true_val_datatuple = true_scale_split.val
        self.true_test_datatuple = true_scale_split.test

        cf_scale_split = self.scale_and_split(
            self.cf_data, dataset, train_indices, val_indices, test_indices
        )
        self.cf_train_datatuple = cf_scale_split.train
        self.cf_val_datatuple = cf_scale_split.val
        self.cf_test_datatuple = cf_scale_split.test

        self.make_feature_groups(dataset, factual_data)

    @implements(BaseDataModule)
    def _train_dataloader(self, shuffle: bool = True, drop_last: bool = True) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                dataset=self.train_datatuple,
                cf_dataset=self.cf_train_datatuple,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.continuous_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=shuffle,
            drop_last=drop_last,
        )

    @implements(LightningDataModule)
    def val_dataloader(self, shuffle: bool = False, drop_last: bool = False) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                dataset=self.val_datatuple,
                cf_dataset=self.cf_val_datatuple,
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
                dataset=self.test_datatuple,
                cf_dataset=self.cf_test_datatuple,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.continuous_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=shuffle,
            drop_last=drop_last,
        )
