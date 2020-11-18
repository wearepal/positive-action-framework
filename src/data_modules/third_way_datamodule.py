"""Data Module for simple data."""
import numpy as np
from ethicml import DataTuple, implements
from pytorch_lightning import LightningDataModule
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader

from src.config_classes.dataclasses import ThirdWayConfig
from src.data_modules.base_module import BaseDataModule
from src.data_modules.dataset_utils import CFDataTupleDataset
from src.datasets.third_way import third_way_data


class ThirdWayDataModule(BaseDataModule):
    """Simple 1d, configurable, data."""

    def __init__(self, cfg: ThirdWayConfig):
        super().__init__()
        self.alpha = cfg.alpha
        self._cf_available = True
        self.gamma = cfg.gamma
        self.seed = cfg.seed
        self.num_samples = cfg.num_samples
        self.train_dims = None
        self._num_s = -1
        self._x_dim = -1
        self._s_dim = -1
        self.num_workers = cfg.num_workers
        self.batch_size = cfg.batch_size

    @implements(LightningDataModule)
    def prepare_data(self) -> None:
        # called only on 1 GPU
        dataset, true_data, cf_data = third_way_data(
            seed=self.seed,
            num_samples=self.num_samples,
            alpha=self.alpha,
            gamma=self.gamma,
            random_shift=0,
            binary_s=1,
        )
        self.dataset = dataset
        self.true_data = true_data
        self.cf_data = cf_data
        self.num_s = true_data.s.nunique().values[0]
        self.data_dim = true_data.x.shape[1]
        self.s_dim = true_data.s.shape[1]

        num_train = int(self.true_data.x.shape[0] * 0.8)
        rng = np.random.RandomState(self.seed)
        idx = rng.permutation(self.true_data.x.index)
        train_indices = idx[:num_train]
        test_indices = idx[num_train:]

        train = DataTuple(
            x=self.true_data.x.iloc[train_indices].reset_index(drop=True),
            s=self.true_data.s.iloc[train_indices].reset_index(drop=True),
            y=self.true_data.y.iloc[train_indices].reset_index(drop=True),
        )
        test = DataTuple(
            x=self.true_data.x.iloc[test_indices].reset_index(drop=True),
            s=self.true_data.s.iloc[test_indices].reset_index(drop=True),
            y=self.true_data.y.iloc[test_indices].reset_index(drop=True),
        )

        scaler = MinMaxScaler()
        scaler = scaler.fit(train.x[dataset.cont_features])
        train.x[dataset.cont_features] = scaler.transform(train.x[dataset.cont_features])
        test.x[dataset.cont_features] = scaler.transform(test.x[dataset.cont_features])

        self.train_data = train
        self.test_data = test

        counterfactual_train = DataTuple(
            x=self.cf_data.x.iloc[train_indices].reset_index(drop=True),
            s=self.cf_data.s.iloc[train_indices].reset_index(drop=True),
            y=self.cf_data.y.iloc[train_indices].reset_index(drop=True),
        )
        counterfactual_test = DataTuple(
            x=self.cf_data.x.iloc[test_indices].reset_index(drop=True),
            s=self.cf_data.s.iloc[test_indices].reset_index(drop=True),
            y=self.cf_data.y.iloc[test_indices].reset_index(drop=True),
        )

        self.scaler_cf = MinMaxScaler()
        self.scaler_cf = self.scaler_cf.fit(counterfactual_train.x[dataset.cont_features])
        counterfactual_train.x[dataset.cont_features] = self.scaler_cf.transform(
            counterfactual_train.x[dataset.cont_features]
        )
        counterfactual_test.x[dataset.cont_features] = self.scaler_cf.transform(
            counterfactual_test.x[dataset.cont_features]
        )

        self.cf_train = counterfactual_train
        self.cf_test = counterfactual_test

    @implements(LightningDataModule)
    def train_dataloader(self) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                self.train_data,
                cf_dataset=self.cf_train,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.cont_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=True,
        )

    @implements(LightningDataModule)
    def test_dataloader(self) -> DataLoader:
        return DataLoader(
            CFDataTupleDataset(
                self.test_data,
                cf_dataset=self.cf_test,
                disc_features=self.dataset.discrete_features,
                cont_features=self.dataset.cont_features,
            ),
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=False,
        )