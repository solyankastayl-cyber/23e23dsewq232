"""
ta_prediction_intelligence.learning — Step 8+ (Feature System, Temporal
Buffer, Dataset Builder). Read-only w.r.t. existing Step 6/7 semantics.

Public surface (other modules SHOULD import only from here, never from
internal submodules — keeps refactor safe).
"""
from .feature_schema import (
    FEATURE_SCHEMA_V1,
    FEATURE_SCHEMA_HASH,
    FEATURE_VERSION,
    BUILDER_VERSION,
    DEFAULT_WINDOW,
    get_feature_schema,
    list_feature_names,
    coerce_to_schema,
)
from .feature_hash import (
    build_feature_hash,
    build_schema_hash,
    canonical_json,
)
from .state_machine import (
    classify_trend_state,
    classify_momentum_state,
    classify_volatility_state,
    detect_trend_transition,
    detect_momentum_transition,
    detect_volatility_transition,
)
from .price_action import compute_price_action
from .temporal_buffer import HybridTemporalBuffer, get_temporal_buffer
from .feature_builder import FeatureBuilder, get_feature_builder
from .dataset_builder import (
    DATASET_VERSION,
    DATASET_BUILDER_VERSION,
    build_sample,
    build_sample_id,
    build_dataset,
    compute_stats as compute_dataset_stats,
    compute_sample_weight,
    persist_samples as persist_dataset_samples,
    read_samples_from_mongo as read_dataset_samples,
    count_samples_in_mongo as count_dataset_samples,
)

__all__ = [
    "FEATURE_SCHEMA_V1",
    "FEATURE_SCHEMA_HASH",
    "FEATURE_VERSION",
    "BUILDER_VERSION",
    "DEFAULT_WINDOW",
    "get_feature_schema",
    "list_feature_names",
    "coerce_to_schema",
    "build_feature_hash",
    "build_schema_hash",
    "canonical_json",
    "classify_trend_state",
    "classify_momentum_state",
    "classify_volatility_state",
    "detect_trend_transition",
    "detect_momentum_transition",
    "detect_volatility_transition",
    "compute_price_action",
    "HybridTemporalBuffer",
    "get_temporal_buffer",
    "FeatureBuilder",
    "get_feature_builder",
    "DATASET_VERSION",
    "DATASET_BUILDER_VERSION",
    "build_sample",
    "build_sample_id",
    "build_dataset",
    "compute_dataset_stats",
    "compute_sample_weight",
    "persist_dataset_samples",
    "read_dataset_samples",
    "count_dataset_samples",
]
