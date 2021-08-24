"""Data Module for simple data."""
from __future__ import annotations
from typing import Optional, Tuple

from kit import implements
import numpy as np
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader

from paf.base_templates.base_module import BaseDataModule
from paf.base_templates.dataset_utils import CFDataTupleDataset
from paf.datasets.simple_x import simple_x_data


class SimpleXDataModule(BaseDataModule):
    """Simple 1d, configurable, data."""

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
        data = simple_x_data(
            seed=self.seed,
            num_samples=self.num_samples,
            alpha=self.alpha,
            gamma=self.gamma,
            random_shift=0,
            binary_s=1,
        )
        self.dataset = data.dataset
        self.best_guess = None
        self.factual_data = data.true
        self.card_s = data.true.s.nunique().values[0]
        self.card_y = data.true.y.nunique().values[0]
        self.data_dim = data.true.x.shape[1:]
        self.dims = self.data_dim
        self.dim_s = (1,) if self.factual_data.s.ndim == 1 else self.factual_data.s.shape[1:]
        self.column_names = [str(col) for col in data.true.x.columns]
        self.outcome_columns = [str(col) for col in data.true.y.columns]

        num_train = int(self.factual_data.x.shape[0] * 0.7)
        num_val = int(self.factual_data.x.shape[0] * 0.1)
        rng = np.random.RandomState(self.seed)
        idx = rng.permutation(self.factual_data.x.index)
        train_indices = idx[:num_train]
        val_indices = idx[num_train : num_train + num_val]
        test_indices = idx[num_train + num_val :]

        self.make_feature_groups(data.dataset, data.true)

        self.train_datatuple, self.val_datatuple, self.test_datatuple = self.scale_and_split(
            data.true, data.dataset, train_indices, val_indices, test_indices
        )
        (
            self.true_train_datatuple,
            self.true_val_datatuple,
            self.true_test_datatuple,
        ) = self.scale_and_split(
            data.true_outcomes, data.dataset, train_indices, val_indices, test_indices
        )
        (
            self.cf_train_datatuple,
            self.cf_val_datatuple,
            self.cf_test_datatuple,
        ) = self.scale_and_split(data.cf, data.dataset, train_indices, val_indices, test_indices)

    @implements(BaseDataModule)
    def _train_dataloader(self, shuffle: bool = True, drop_last: bool = True) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                self.train_datatuple,
                cf_dataset=self.cf_train_datatuple,
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
                self.val_datatuple,
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
                self.test_datatuple,
                cf_dataset=self.cf_test_datatuple,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.continuous_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=shuffle,
            drop_last=drop_last,
        )
