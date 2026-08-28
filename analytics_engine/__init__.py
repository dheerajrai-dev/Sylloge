"""SAT-SA Six-Engine Analytics Core Microservice Package."""

import os

_ae_dir = os.path.dirname(os.path.abspath(__file__))
_ae_app_dir = os.path.join(_ae_dir, "app")

__path__ = [_ae_app_dir, _ae_dir]

from analytics_engine.config import analytics_settings
from analytics_engine.engines.pipeline import AnalyticsPipeline
from analytics_engine.engines.execution_gap import (
    ExecutionGapEngine,
    ExecutionGapRuleRegistry,
    LogicInterpreter,
    RuleCondition,
    RuleDefinition,
    TemporalJoin,
)
from analytics_engine.engines.negative_space import (
    CheckDefinition,
    NegativeSpaceCheckRegistry,
    NegativeSpaceEngine,
)
from analytics_engine.engines.correlation import (
    CorrelationEngine,
    NoteSimilarityAnalyzer,
    SameAssetBurstClusterer,
)
from analytics_engine.engines.peer_benchmark import (
    PeerBenchmarkEngine,
    extract_entity_metrics,
)
from analytics_engine.engines.risk_scoring import RiskScoringEngine
from analytics_engine.engines.explainability import (
    ExplainabilityEngine,
    RationaleCardBuilder,
)
from analytics_engine.main import app

__all__ = [
    "app",
    "analytics_settings",
    "AnalyticsPipeline",
    "ExecutionGapEngine",
    "ExecutionGapRuleRegistry",
    "LogicInterpreter",
    "RuleDefinition",
    "RuleCondition",
    "TemporalJoin",
    "NegativeSpaceEngine",
    "NegativeSpaceCheckRegistry",
    "CheckDefinition",
    "CorrelationEngine",
    "SameAssetBurstClusterer",
    "NoteSimilarityAnalyzer",
    "PeerBenchmarkEngine",
    "extract_entity_metrics",
    "RiskScoringEngine",
    "ExplainabilityEngine",
    "RationaleCardBuilder",
]
