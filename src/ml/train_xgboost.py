"""XGBoost training script with ONNX export.

CLI tool for training an XGBoost classifier on OHLCV-derived features.
Exports to ONNX format for lightweight inference via onnxruntime.

Usage:
    python -m src.ml.train_xgboost --asset-type stock
    python -m src.ml.train_xgboost --asset-type crypto --epochs 200
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from sqlalchemy import create_engine, text

from src.config import settings
from src.ml.features import extract_features


def train_xgboost(
    asset_type: str = "stock",
    n_estimators: int = 100,
    output_dir: str | None = None,
) -> str:
    """Train XGBoost classifier and export to ONNX.

    Args:
        asset_type: "stock" or "crypto".
        n_estimators: Number of boosting rounds.
        output_dir: Directory to save ONNX model. Defaults to src/ml/models/.

    Returns:
        Path to the exported ONNX model file.

    Raises:
        ValueError: If insufficient training data is available.
    """
    import xgboost as xgb  # type: ignore[import-untyped]

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "models")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"xgboost_{asset_type}.onnx")

    print(f"Training XGBoost classifier for {asset_type} assets")
    print(f"Output: {output_path}")
    print(f"Estimators: {n_estimators}")
    print()

    # --- Load price data from DB ---
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        # Get assets of the specified type
        result = conn.execute(
            text("SELECT id, symbol FROM assets WHERE asset_type = :at"),
            {"at": asset_type},
        )
        assets = result.fetchall()

        if not assets:
            raise ValueError(f"No {asset_type} assets found in database")

        print(f"Found {len(assets)} {asset_type} assets")

        all_features: list[np.ndarray] = []
        all_targets: list[int] = []

        for asset_id, symbol in assets:
            # Load price history
            prices = conn.execute(
                text(
                    "SELECT date, open, high, low, close, volume "
                    "FROM prices WHERE asset_id = :aid ORDER BY date"
                ),
                {"aid": asset_id},
            )
            import pandas as pd

            df = pd.DataFrame(
                prices.fetchall(),
                columns=["date", "open", "high", "low", "close", "volume"],
            )

            if len(df) < 200:
                print(f"  Skipping {symbol}: only {len(df)} days (need 200+)")
                continue

            # Sliding window: extract features for each day from index 60 onward
            print(f"  Processing {symbol}: {len(df)} days")
            for i in range(60, len(df) - 1):
                window = df.iloc[: i + 1]
                feats = extract_features(window)
                if feats is not None:
                    # Target: next-day return direction (1 if positive, 0 if negative)
                    next_return = (
                        df["close"].iloc[i + 1] / df["close"].iloc[i]
                    ) - 1.0
                    target = 1 if next_return > 0 else 0
                    all_features.append(feats[0])
                    all_targets.append(target)

    if len(all_features) < 100:
        raise ValueError(
            f"Insufficient training data: only {len(all_features)} samples "
            f"(need at least 100). Add more assets or price history."
        )

    X = np.array(all_features, dtype=np.float32)
    y = np.array(all_targets, dtype=np.int32)
    n_features = X.shape[1]

    print(f"\nTotal samples: {len(X)} (positive: {sum(y)}, negative: {len(y) - sum(y)})")

    # --- Temporal train/test split (last 20% as test) ---
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # --- Train XGBoost ---
    model = xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=6,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="logloss",
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=True,
    )

    # --- Print metrics ---
    from sklearn.metrics import accuracy_score, precision_score, recall_score  # type: ignore[import-untyped]

    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)

    print(f"\nTraining accuracy: {accuracy_score(y_train, train_pred):.4f}")
    print(f"Test accuracy:     {accuracy_score(y_test, test_pred):.4f}")
    print(f"Test precision:    {precision_score(y_test, test_pred, zero_division=0):.4f}")
    print(f"Test recall:       {recall_score(y_test, test_pred, zero_division=0):.4f}")

    # --- Export to ONNX ---
    import onnxmltools  # type: ignore[import-untyped]
    from onnxconverter_common import FloatTensorType  # type: ignore[import-untyped]
    from onnxmltools.convert import convert_xgboost  # type: ignore[import-untyped]

    initial_type = [("input", FloatTensorType([None, n_features]))]
    onnx_model = convert_xgboost(
        model, initial_types=initial_type, target_opset=18
    )
    onnxmltools.utils.save_model(onnx_model, output_path)

    print(f"\nONNX model saved to: {output_path}")

    # --- Verify round-trip ---
    import onnxruntime as ort  # type: ignore[import-untyped]

    session = ort.InferenceSession(output_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    onnx_outputs = session.run(None, {input_name: X_test[:1]})
    xgb_pred_native = model.predict(X_test[:1])

    print(f"Round-trip check: XGBoost={xgb_pred_native[0]}, ONNX={onnx_outputs[0][0]}")
    if int(xgb_pred_native[0]) == int(onnx_outputs[0][0]):
        print("Round-trip verification: PASSED")
    else:
        print("WARNING: Round-trip verification: MISMATCH")

    del session
    return output_path


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Train XGBoost classifier and export to ONNX"
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
        default=100,
        help="Number of boosting rounds (default: 100)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for ONNX model (default: src/ml/models/)",
    )

    args = parser.parse_args()

    try:
        path = train_xgboost(
            asset_type=args.asset_type,
            n_estimators=args.epochs,
            output_dir=args.output_dir,
        )
        print(f"\nDone. Model saved to: {path}")
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
