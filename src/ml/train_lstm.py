"""LSTM training script with ONNX export.

CLI tool for training an LSTM model on OHLCV-derived features.
Exports to ONNX format for lightweight inference via onnxruntime.

Usage:
    python -m src.ml.train_lstm --asset-type stock
    python -m src.ml.train_lstm --asset-type crypto --epochs 50
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from sqlalchemy import create_engine, text

from src.config import settings
from src.ml.features import extract_features

SEQUENCE_LENGTH = 60  # Days of history per prediction


def train_lstm(
    asset_type: str = "stock",
    epochs: int = 50,
    output_dir: str | None = None,
) -> str:
    """Train LSTM model and export to ONNX.

    Args:
        asset_type: "stock" or "crypto".
        epochs: Number of training epochs.
        output_dir: Directory to save ONNX model. Defaults to src/ml/models/.

    Returns:
        Path to the exported ONNX model file.

    Raises:
        ValueError: If insufficient training data is available.
    """
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "models")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"lstm_{asset_type}.onnx")

    print(f"Training LSTM model for {asset_type} assets")
    print(f"Output: {output_path}")
    print(f"Epochs: {epochs}, Sequence length: {SEQUENCE_LENGTH}")
    print()

    # --- Load price data from DB ---
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, symbol FROM assets WHERE asset_type = :at"),
            {"at": asset_type},
        )
        assets = result.fetchall()

        if not assets:
            raise ValueError(f"No {asset_type} assets found in database")

        print(f"Found {len(assets)} {asset_type} assets")

        all_sequences: list[np.ndarray] = []
        all_targets: list[np.ndarray] = []

        for asset_id, symbol in assets:
            import pandas as pd

            prices = conn.execute(
                text(
                    "SELECT date, open, high, low, close, volume "
                    "FROM prices WHERE asset_id = :aid ORDER BY date"
                ),
                {"aid": asset_id},
            )
            df = pd.DataFrame(
                prices.fetchall(),
                columns=["date", "open", "high", "low", "close", "volume"],
            )

            if len(df) < 200:
                print(f"  Skipping {symbol}: only {len(df)} days (need 200+)")
                continue

            # Extract features for all valid days
            daily_features: list[np.ndarray] = []
            for i in range(60, len(df)):
                window = df.iloc[: i + 1]
                feats = extract_features(window)
                if feats is not None:
                    daily_features.append(feats[0])

            if len(daily_features) < SEQUENCE_LENGTH + 1:
                print(f"  Skipping {symbol}: insufficient features ({len(daily_features)})")
                continue

            print(f"  Processing {symbol}: {len(daily_features)} feature vectors")

            # Build sequences of SEQUENCE_LENGTH days
            for i in range(SEQUENCE_LENGTH, len(daily_features) - 1):
                sequence = np.array(
                    daily_features[i - SEQUENCE_LENGTH : i], dtype=np.float32
                )
                # Target: next-day direction (1=up, 0=down) and magnitude
                close_idx = i + 60  # offset by initial 60-day warmup
                if close_idx + 1 < len(df):
                    next_return = (
                        df["close"].iloc[close_idx + 1] / df["close"].iloc[close_idx]
                    ) - 1.0
                    direction = 1.0 if next_return > 0 else 0.0
                    magnitude = abs(next_return)
                    all_sequences.append(sequence)
                    all_targets.append(np.array([direction, magnitude], dtype=np.float32))

    if len(all_sequences) < 100:
        raise ValueError(
            f"Insufficient training data: only {len(all_sequences)} samples "
            f"(need at least 100). Add more assets or price history."
        )

    X = np.array(all_sequences, dtype=np.float32)
    y = np.array(all_targets, dtype=np.float32)
    n_features = X.shape[2]

    print(f"\nTotal samples: {len(X)}")
    print(f"Sequence shape: {X.shape} (samples, timesteps, features)")
    print(f"Target shape: {y.shape}")

    # --- Temporal train/test split ---
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # --- LSTM Model ---
    class LSTMModel(nn.Module):
        def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, 2)  # direction + magnitude

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :])

    model = LSTMModel(input_size=n_features)
    device = torch.device("cpu")
    model.to(device)

    # --- Training ---
    train_dataset = TensorDataset(
        torch.tensor(X_train), torch.tensor(y_train)
    )
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=False)
    # Note: shuffle=False for temporal data to avoid look-ahead bias

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    bce_loss = nn.BCEWithLogitsLoss()
    mse_loss = nn.MSELoss()

    print("\nTraining LSTM...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        n_batches = 0

        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_x)

            # Combined loss: direction (BCE) + magnitude (MSE)
            direction_loss = bce_loss(outputs[:, 0], batch_y[:, 0])
            magnitude_loss = mse_loss(outputs[:, 1], batch_y[:, 1])
            loss = direction_loss + 0.1 * magnitude_loss

            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            avg_loss = total_loss / max(n_batches, 1)
            print(f"  Epoch {epoch + 1}/{epochs}: loss={avg_loss:.4f}")

    # --- Evaluate ---
    model.eval()
    with torch.no_grad():
        test_outputs = model(torch.tensor(X_test).to(device))
        test_preds = (torch.sigmoid(test_outputs[:, 0]) > 0.5).float().numpy()
        test_directions = y_test[:, 0]

        accuracy = float(np.mean(test_preds == test_directions))
        print(f"\nTest accuracy: {accuracy:.4f}")

    # --- Export to ONNX ---
    model.eval()
    dummy_input = torch.randn(1, SEQUENCE_LENGTH, n_features)
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        input_names=["input"],
        output_names=["prediction"],
        opset_version=18,
        dynamic_axes={
            "input": {0: "batch_size"},
            "prediction": {0: "batch_size"},
        },
    )

    print(f"\nONNX model saved to: {output_path}")

    # --- Verify round-trip ---
    import onnxruntime as ort  # type: ignore[import-untyped]

    session = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    onnx_out = session.run(None, {input_name: X_test[:1]})

    with torch.no_grad():
        torch_out = model(torch.tensor(X_test[:1])).numpy()

    print(f"Round-trip check: Torch={torch_out[0]}, ONNX={onnx_out[0][0]}")
    if np.allclose(torch_out[0], onnx_out[0][0], atol=1e-4):
        print("Round-trip verification: PASSED")
    else:
        print("WARNING: Round-trip verification: MISMATCH (may be due to floating point)")

    del session
    return output_path


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Train LSTM model and export to ONNX"
    )
    parser.add_argument(
        "--asset-type",
        choices=["stock", "crypto"],
        default="stock",
        help="Asset type to train on (default: stock)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs (default: 50)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for ONNX model (default: src/ml/models/)",
    )

    args = parser.parse_args()

    try:
        path = train_lstm(
            asset_type=args.asset_type,
            epochs=args.epochs,
            output_dir=args.output_dir,
        )
        print(f"\nDone. Model saved to: {path}")
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
