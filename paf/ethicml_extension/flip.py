"""Demographic Parity Label flipping approach."""
from __future__ import annotations
from abc import abstractmethod

from ethicml import DataTuple, PostAlgorithm, Prediction, TestTuple
import numpy as np
from ranzen import implements

__all__ = ["FlipBase", "DPFlip", "EqOppFlip"]


class FlipBase(PostAlgorithm):
    """Common for flipping functions."""

    def __init__(self, name: str) -> None:
        super().__init__(name=name)

    @implements(PostAlgorithm)
    def run(
        self,
        train_predictions: Prediction,
        train: DataTuple,
        test_predictions: Prediction,
        test: TestTuple,
    ) -> Prediction:
        x, y = self._fit(test, test_predictions)
        _test_preds = self._flip(test_predictions, test, flip_0_to_1=True, num_to_flip=x, s_group=0)
        return self._flip(_test_preds, test, flip_0_to_1=False, num_to_flip=y, s_group=1)

    @abstractmethod
    def _fit(self, test: TestTuple, preds: Prediction) -> tuple[int, int]:
        pass

    @abstractmethod
    def _flip(
        self,
        preds: Prediction,
        test: TestTuple,
        flip_0_to_1: bool,
        num_to_flip: int,
        s_group: int,
    ) -> Prediction:
        pass


class DPFlip(FlipBase):
    """Randomly flip a number of decisions such that perfect demographic parity is achieved."""

    def __init__(self) -> None:
        super().__init__(name="DemPar. Post Process")

    def _flip(
        self,
        preds: Prediction,
        test: TestTuple,
        flip_0_to_1: bool,
        num_to_flip: int,
        s_group: int,
    ) -> Prediction:
        if num_to_flip >= 0:
            pre_y_val = 0 if flip_0_to_1 else 1
            post_y_val = 1 if flip_0_to_1 else 0
        else:
            pre_y_val = 1 if flip_0_to_1 else 0
            post_y_val = 0 if flip_0_to_1 else 1
            num_to_flip = abs(num_to_flip)

        _y = preds.hard[preds.hard == pre_y_val]
        _s = preds.hard[test.s[test.s.columns[0]] == s_group]
        idx_s_y = _y.index & _s.index
        rng = np.random.RandomState(888)
        idxs = list(rng.permutation(idx_s_y))
        preds.hard.update({idx: post_y_val for idx in idxs[:num_to_flip]})  # type: ignore[arg-type]
        return preds

    def _fit(self, test: TestTuple, preds: Prediction) -> tuple[int, int]:
        y_0 = preds.hard[preds.hard == 0]
        y_1 = preds.hard[preds.hard == 1]
        s_0 = test.s[test.s[test.s.columns[0]] == 0]
        s_1 = test.s[test.s[test.s.columns[0]] == 1]
        # Naming is nSY
        n00 = preds.hard[(s_0.index) & (y_0.index)].count()
        n01 = preds.hard[(s_0.index) & (y_1.index)].count()
        n10 = preds.hard[(s_1.index) & (y_0.index)].count()
        n11 = preds.hard[(s_1.index) & (y_1.index)].count()

        _a = (((n00 + n01) * n11) - ((n10 + n11) * n01)) / (n00 + n01)
        _b = (n10 + n11) / (n00 + n01)

        if _b > 1:
            x = _a / _b
            z = 0.0
        else:
            x = 0.0
            z = _a
        return int(round(x)), int(round(z))


class EqOppFlip(FlipBase):
    """Randomly flip a number of decisions such that perfect TPR parity is achieved.

    This Shouldn't be used. Use Hardt et al instead. This method requires access to the ground
    truth labels, which is very bad.
    """

    def __init__(self) -> None:
        super().__init__(name="EqOpp. Post Process")

    def _flip(
        self,
        preds: Prediction,
        test: TestTuple,
        flip_0_to_1: bool,
        num_to_flip: int,
        s_group: int,
    ) -> Prediction:
        if num_to_flip >= 0:
            pre_y_val = 0 if flip_0_to_1 else 1
            post_y_val = 1 if flip_0_to_1 else 0
        else:
            pre_y_val = 1 if flip_0_to_1 else 0
            post_y_val = 0 if flip_0_to_1 else 1
            num_to_flip = abs(num_to_flip)

        _pred = preds.hard[preds.hard == pre_y_val]
        _s = preds.hard[test.s[test.s.columns[0]] == s_group]
        _y = preds.hard[test.y[test.y.columns[0]] == 1]  # type: ignore[attr-defined]
        idx_s_y = _pred.index & _s.index & _y.index
        if len(idx_s_y) < num_to_flip:
            raise AssertionError("Not enough valid candidates to flip")

        rng = np.random.RandomState(888)
        idxs = list(rng.permutation(idx_s_y))
        preds.hard.update({idx: post_y_val for idx in idxs[:num_to_flip]})  # type: ignore[arg-type]
        return preds

    def _fit(self, test: TestTuple, preds: Prediction) -> tuple[int, int]:
        preds_1 = preds.hard[preds.hard == 1]
        s_0 = test.s[test.s[test.s.columns[0]] == 0]
        s_1 = test.s[test.s[test.s.columns[0]] == 1]
        y_1 = test.y[test.y[test.y.columns[0]] == 1]  # type: ignore[attr-defined]

        s0_y1_p1 = preds.hard[(s_0.index) & (y_1.index) & (preds_1.index)].count()
        s1_y1_p1 = preds.hard[(s_1.index) & (y_1.index) & (preds_1.index)].count()

        # Naming is nSY
        s0_y1 = preds.hard[(s_0.index) & (y_1.index)].count()
        s1_y1 = preds.hard[(s_1.index) & (y_1.index)].count()

        ratio_a = s1_y1_p1 - ((s1_y1 * s0_y1_p1) / s0_y1)
        ratio_b = s1_y1 / s0_y1

        if ratio_b > 1:
            x = ratio_a / ratio_b
            z = 0
        else:
            x = 0
            z = ratio_a
        return int(round(x)), int(round(z))
