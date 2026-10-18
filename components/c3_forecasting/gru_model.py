"""Standard GRU regression baseline for GeoNex C3."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence

from components.c3_forecasting.gru_dataset import INPUT_FEATURE_COUNT


class C3StandardGRU(nn.Module):
    """Predict a future sensor value from a variable-length sequence."""

    def __init__(
        self,
        input_size: int = INPUT_FEATURE_COUNT,
        hidden_size: int = 64,
        num_layers: int = 1,
    ) -> None:
        super().__init__()

        if input_size <= 0:
            raise ValueError("input_size must be positive")

        if hidden_size <= 0:
            raise ValueError("hidden_size must be positive")

        if num_layers <= 0:
            raise ValueError("num_layers must be positive")

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )

        self.regression_head = nn.Linear(
            hidden_size,
            1,
        )

    def forward(
        self,
        inputs: torch.Tensor,
        lengths: torch.Tensor,
    ) -> torch.Tensor:
        """Return one regression prediction per sequence."""

        if inputs.ndim != 3:
            raise ValueError(
                "GRU inputs must have shape [batch, steps, features]"
            )

        if inputs.shape[2] != self.input_size:
            raise ValueError(
                f"Expected {self.input_size} input features, "
                f"received {inputs.shape[2]}"
            )

        if lengths.ndim != 1:
            raise ValueError("lengths must be one-dimensional")

        if lengths.shape[0] != inputs.shape[0]:
            raise ValueError(
                "Sequence lengths must match batch size"
            )

        if torch.any(lengths <= 0).item():
            raise ValueError(
                "Sequence lengths must be positive"
            )

        if torch.any(lengths > inputs.shape[1]).item():
            raise ValueError(
                "Sequence length exceeds padded input size"
            )

        packed = pack_padded_sequence(
            inputs,
            lengths.detach().cpu(),
            batch_first=True,
            enforce_sorted=False,
        )

        _, hidden = self.gru(packed)

        final_hidden = hidden[-1]

        predictions = self.regression_head(
            final_hidden
        )

        return predictions.squeeze(-1)