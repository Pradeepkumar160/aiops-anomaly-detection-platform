import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Anomaly(Base):
    __tablename__ = "anomalies"
    id          = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, nullable=False)
    value       = Column(Float,  nullable=False)
    score       = Column(Float,  nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")


def save_anomaly(metric: str, value: float, score: float):
    with SessionLocal() as session:
        session.add(Anomaly(metric_name=metric, value=value, score=score))
        session.commit()


def list_anomalies(limit: int = 50, offset: int = 0) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(Anomaly)
            .order_by(Anomaly.detected_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "metric_name": r.metric_name,
                "value": r.value,
                "score": r.score,
                "detected_at": r.detected_at.isoformat() if r.detected_at else None,
            }
            for r in rows
        ]
