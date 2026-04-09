from __future__ import annotations

from pathlib import Path
import json

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression

from app.core.config import get_settings
from app.ml.features import build_training_features
from app.utils.logger import get_logger


logger = get_logger(__name__)


def train_model(csv_path: Path | None = None) -> None:
    """
    Train a baseline logistic regression on pairwise pre-event features.

    Uses only pre-outcome columns from the training CSV (see ``build_training_features``).
    Artifacts are written to ``MODEL_PATH`` and ``MODEL_METADATA_PATH``.
    """
    settings = get_settings()
    data_path = csv_path or settings.training_data_path

    logger.info("Loading training data", extra={"path": str(data_path)})
    df = pd.read_csv(data_path)

    X, y = build_training_features(df)

    logger.info(
        "Fitting logistic regression",
        extra={"n_samples": int(len(X)), "n_features": int(X.shape[1])},
    )
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    artifacts_dir = settings.model_path.parent
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, settings.model_path)

    metadata = {
        "feature_names": list(X.columns),
        "version": settings.model_version,
    }
    settings.model_metadata_path.parent.mkdir(parents=True, exist_ok=True)
    settings.model_metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Model trained and saved",
        extra={
            "artifact": str(settings.model_path),
            "metadata": str(settings.model_metadata_path),
        },
    )


if __name__ == "__main__":
    train_model()

