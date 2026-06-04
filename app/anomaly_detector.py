import os
import logging
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from app.config import settings

logger = logging.getLogger(__name__)
MODEL_PATH = "/app/models/isolation_forest.pkl"


class AnomalyDetector:
    def __init__(self):
        self.model: IsolationForest | None = None

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def train(self, values: list[float]):
        X = np.array(values).reshape(-1, 1)
        self.model = IsolationForest(
            contamination=settings.contamination,
            random_state=42,
            n_estimators=100,
        )
        self.model.fit(X)
        logger.info("Model trained on %d samples", len(values))

    def predict(self, value: float) -> tuple[float, bool]:
        if not self.is_loaded:
            raise RuntimeError("Model not trained")
        X = np.array([[value]])
        score = float(self.model.score_samples(X)[0])
        is_anomaly = self.model.predict(X)[0] == -1
        return score, is_anomaly

    def save(self):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(self.model, MODEL_PATH)
        logger.info("Model saved to %s", MODEL_PATH)

    def load(self):
        self.model = joblib.load(MODEL_PATH)
        logger.info("Model loaded from %s", MODEL_PATH)
