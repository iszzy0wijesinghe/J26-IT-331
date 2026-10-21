"""
GeoNex C3 M5 Multivariate Mode-Conditioned GRU.

Predicts multiple environmental sensor values at
15, 30 and 60-minute horizons.

Research features:
- Multivariate sensor inputs
- Actual elapsed-time information
- Five operating modes
- Variable-length historical sequences
- Multi-horizon forecasting
- Shared temporal representation

This module defines the neural architecture.
It does not claim landslide-event prediction.
"""

from __future__ import annotations

import torch
from torch import nn


SENSOR_FEATURES = (
    "soil_moisture_pct",
    "rainfall_proxy_counts",
    "tilt_deg",
    "vibration_g",
    "fsr_adc",
    "air_temperature_c",
    "humidity_pct",
)

OPERATING_MODES = (
    "DEEP_SLEEP",
    "IDLE",
    "RISK",
    "WARNING",
    "EMERGENCY",
)

FORECAST_HORIZONS = (15, 30, 60)

SENSOR_COUNT = len(SENSOR_FEATURES)
MODE_COUNT = len(OPERATING_MODES)

# Sensor values + sensor validity masks
# + elapsed-time features + operating-mode encoding.
INPUT_SIZE = (
    SENSOR_COUNT * 2
    + 2
    + MODE_COUNT
)

OUTPUT_SIZE = (
    SENSOR_COUNT * len(FORECAST_HORIZONS)
)


class C3M5MultivariateGRU(nn.Module):
    """
    Shared GRU encoder with a multi-horizon
    multivariate regression head.

    Input:
        [batch, sequence_length, INPUT_SIZE]

    Output:
        [batch, horizon_count, sensor_count]
    """

    def __init__(
        self,
        input_size: int = INPUT_SIZE,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:

        super().__init__()

        if input_size <= 0:
            raise ValueError(
                "input_size must be positive"
            )

        if hidden_size <= 0:
            raise ValueError(
                "hidden_size must be positive"
            )

        if num_layers <= 0:
            raise ValueError(
                "num_layers must be positive"
            )

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        self.regression_head = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, OUTPUT_SIZE),
        )

    def forward(
        self,
        sequences: torch.Tensor,
        lengths: torch.Tensor | None = None,
    ) -> torch.Tensor:

        if sequences.ndim != 3:
            raise ValueError(
                "Expected [batch, time, features]"
            )

        if sequences.shape[-1] != self.input_size:
            raise ValueError(
                "Incorrect input feature dimension"
            )

        if lengths is not None:

            lengths = lengths.to(
                device=sequences.device,
                dtype=torch.long,
            )

            if lengths.ndim != 1:
                raise ValueError(
                    "lengths must be one-dimensional"
                )

            if lengths.shape[0] != sequences.shape[0]:
                raise ValueError(
                    "Batch size and lengths mismatch"
                )

            if torch.any(lengths < 1):
                raise ValueError(
                    "Sequence lengths must be positive"
                )

            if torch.any(lengths > sequences.shape[1]):
                raise ValueError(
                    "Sequence length exceeds input size"
                )

            packed = nn.utils.rnn.pack_padded_sequence(
                sequences,
                lengths.cpu(),
                batch_first=True,
                enforce_sorted=False,
            )

            _, hidden = self.gru(packed)

        else:
            _, hidden = self.gru(sequences)

        representation = hidden[-1]

        predictions = self.regression_head(
            representation
        )

        return predictions.reshape(
            sequences.shape[0],
            len(FORECAST_HORIZONS),
            SENSOR_COUNT,
        )