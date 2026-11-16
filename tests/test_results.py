from __future__ import annotations

import pandas as pd
import pytest

import netbone as nb


def test_selection_rejects_duplicate_identifiers() -> None:
    with pytest.raises(nb.ValidationError, match="cannot contain duplicates"):
        nb.Selection(
            target="edge",
            selected_ids=(1, 1),
            rejected_ids=(),
            statistic="score",
            parameters={},
            mask=pd.Series([True, True]),
        )


def test_selection_rejects_non_integer_identifiers() -> None:
    with pytest.raises(nb.ValidationError, match="integer identifiers"):
        nb.Selection(
            target="edge",
            selected_ids=("edge-a",),
            rejected_ids=(),
            statistic="score",
            parameters={},
            mask=pd.Series([True]),
        )


def test_selection_rejects_inconsistent_mask_length() -> None:
    with pytest.raises(nb.ValidationError, match="mask length"):
        nb.Selection(
            target="edge",
            selected_ids=(1,),
            rejected_ids=(2,),
            statistic="score",
            parameters={},
            mask=pd.Series([True]),
        )
