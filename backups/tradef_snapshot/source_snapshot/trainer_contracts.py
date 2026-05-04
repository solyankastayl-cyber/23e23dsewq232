"""
Step 11 — Model Trainer interface contracts (DESIGN-ONLY).

This module is paired with `/app/memory/STEP11_TRAINER_SPEC.md`. It defines
Pydantic data shells, enums, and abstract interfaces. **Every** method
raises `NotImplementedError` deliberately so that no part of the trainer
can be silently completed before:

    1. The live ML gate is green for at least one (symbol, tf) pair.
    2. The architect issues `BUILD STEP 11 v1`.

Do NOT add helpers, default implementations, or `pass` stubs here. If you
think you need one, the answer is "open a ticket for Step 11 v1".

Guarantees enforced by this file:
  * No imports of `lightgbm`, `joblib`, `boto3`, `numpy`, or any training
    machinery. The trainer contracts are pure type declarations.
  * No I/O. No Mongo. No filesystem.
  * No silent fall-throughs.

v1.1 patch (architect-required, 2026-04-29):
  * Label definition contract (ε threshold + neutral drop)
  * Class imbalance handling (1/freq weights, mandatory)
  * Baseline comparison (majority + random + δ floor)
  * Confidence buckets pinned to predict_proba + monotonicity test
  * Explicit deterministic model_id formula
  * dataset_snapshot_hash mandatory and surfaced
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

# ─── Versioning ────────────────────────────────────────────────────────────
STEP11_TRAINER_SPEC_VERSION = "v1.1.0-design"
TRAINER_VERSION = "v1"
TRAINER_BUILDER_VERSION = "1.0.0"
LABEL_DEFINITION_VERSION = "v1"
MODEL_ID_NAMESPACE = "step11"  # prefix used in the model_id sha256 input

# ─── Hard invariants (NOT parameters) ──────────────────────────────────────
# Purge gap between train and eval windows. Equal to h6 horizon. This is
# baked into the splitter; user config CANNOT override it. See SPEC §3.2.
PURGE_GAP_BARS_INVARIANT: int = 6

# Minimum sample threshold for the live ML gate, per (symbol, tf) pair.
# Mirrors `ml_readiness.types.MIN_TRAIN_SAMPLES`. Duplicated as a constant
# here ONLY to keep the gate check self-contained at read time.
LIVE_GATE_MIN_SAMPLES_PER_PAIR: int = 500

# Minimum class ratio. If smaller -> ImbalancedClassesError.
MIN_CLASS_RATIO_INVARIANT: float = 0.10

# Default seed. Configurable via TrainConfig but always logged.
DEFAULT_SEED: int = 42
# Independent seed for stochastic baselines (random_proportional). Pinned
# so two reports over the same dataset are bit-comparable.
BASELINE_SEED: int = 42

# v1 target lock. Only this target is trained; the rest live in TargetName
# but are explicitly disabled.
V1_PRIMARY_TARGET: str = "direction_h6"

# v1.1 — label definition (§2.4)
# Drop samples whose |return_h6| <= LABEL_NEUTRAL_EPSILON.
LABEL_NEUTRAL_EPSILON: float = 0.0005  # = 0.05% absolute return on h6

# v1.1 — baseline floor (§6.5)
# Model must beat majority baseline by at least this many points to be
# eligible for inference deployment.
BASELINE_DELTA_MIN: float = 0.02  # 2 percentage points

# v1.1 — confidence buckets (§6.4). Pinned, not configurable.
# Each bucket is (lo, hi) on `predict_proba(class=1)`.
# `None` denotes an open boundary.
CONFIDENCE_BUCKETS: Tuple[Tuple[str, Optional[float], Optional[float]], ...] = (
    ("low", None, 0.55),    # [0.00, 0.55)
    ("mid", 0.55, 0.70),    # [0.55, 0.70)
    ("high", 0.70, None),   # [0.70, 1.00]
)

# v1.1 — confidence monotonicity test threshold (§6.4)
# accuracy(high) > accuracy(low) + this delta to pass.
CONFIDENCE_MONOTONIC_DELTA: float = 0.05

# Temporal-drift warning threshold: if |first_half_acc - second_half_acc|
# exceeds this on the eval window we flip the warning bit.
TEMPORAL_DRIFT_WARNING_DELTA: float = 0.10


# ═══ ENUMS ═════════════════════════════════════════════════════════════════
class SplitStrategy(str, Enum):
    TIME_SPLIT = "time_split"
    WALK_FORWARD = "walk_forward"
    TIME_SPLIT_PURGE_GAP = "time_split_purge_gap"  # default


class TargetName(str, Enum):
    DIRECTION_H1 = "direction_h1"      # disabled in v1
    DIRECTION_H3 = "direction_h3"      # disabled in v1
    DIRECTION_H6 = "direction_h6"      # ENABLED — v1 primary
    WINNING_SCENARIO = "winning_scenario"  # disabled in v1
    RETURN_H6 = "return_h6"            # disabled in v1
    MAX_FAVOURABLE_H6 = "max_favourable_h6"  # disabled in v1
    MAX_ADVERSE_H6 = "max_adverse_h6"  # disabled in v1

    def is_enabled_in_v1(self) -> bool:
        """Whether this target is allowed to be trained in v1."""
        raise NotImplementedError("target gating is not implemented in design phase")


class ModelType(str, Enum):
    LIGHTGBM_BINARY = "lightgbm_binary"          # ENABLED — v1
    LIGHTGBM_MULTICLASS = "lightgbm_multiclass"  # disabled in v1
    LIGHTGBM_REGRESSION = "lightgbm_regression"  # disabled in v1


class GateStatusEnum(str, Enum):
    RED = "red"        # below 80% of threshold for every pair
    YELLOW = "yellow"  # at least one pair within 80%..100%
    GREEN = "green"    # at least one pair >= threshold


class ModelStatus(str, Enum):
    TRAINED = "trained"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class ConfidenceBucket(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


# ═══ DOMAIN ERRORS ═════════════════════════════════════════════════════════
class StepElevenError(Exception):
    """Base class for all Step 11 errors. Never caught generically."""


class MLGateNotSatisfiedError(StepElevenError):
    """Raised when /train is called but live_evaluated < threshold."""


class FeatureSchemaMismatch(StepElevenError):
    """Raised when a sample / model carries a different feature_schema_hash."""


class InsufficientSplitSamplesError(StepElevenError):
    """Post-split train_n<100 or eval_n<50."""


class ImbalancedClassesError(StepElevenError):
    """min_class_ratio < MIN_CLASS_RATIO_INVARIANT (0.10)."""


class LabelExtractionError(StepElevenError):
    """y-vector mismatch, NaN return, or other label-extraction problem."""


class UnsupportedConfidenceError(StepElevenError):
    """Model exposes no predict_proba; §6.4 cannot be computed."""


class ConcurrentTrainRunError(StepElevenError):
    """A run for the same model_id is already in progress."""


class ArtifactWriteError(StepElevenError):
    """Local FS write failed or directory is partial."""


class RegistryWriteError(StepElevenError):
    """Mongo registry upsert failed AFTER local artefact was written."""


class ModelLoadError(StepElevenError):
    """Registry / file / schema / snapshot mismatch when loading a model."""


# ═══ DATA SHELLS (Pydantic — declarations only) ═════════════════════════════
class TrainConfig(BaseModel):
    """User-facing training request body. The trainer NEVER mutates this."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(..., min_length=1)
    tf: str = Field(..., min_length=1)
    target: TargetName = Field(default=TargetName.DIRECTION_H6)
    model_type: ModelType = Field(default=ModelType.LIGHTGBM_BINARY)
    split_strategy: SplitStrategy = Field(default=SplitStrategy.TIME_SPLIT_PURGE_GAP)
    seed: int = Field(default=DEFAULT_SEED, ge=0)
    notes: Optional[str] = None


class TrainRequest(BaseModel):
    """Wire-level POST /train body."""
    model_config = ConfigDict(extra="forbid")

    symbol: str
    tf: str
    split_strategy: SplitStrategy = SplitStrategy.TIME_SPLIT_PURGE_GAP
    seed: int = DEFAULT_SEED


class DatasetSnapshot(BaseModel):
    """Frozen, hashable view of the live dataset used for one training run.
    Re-running with the same snapshot must produce the same model_id."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str  # alias of dataset_snapshot_hash; kept for compat
    dataset_snapshot_hash: str  # canonical 64-hex sha256 (v1.1)
    sample_ids: List[str]
    n_samples: int
    symbol: str
    tf: str
    feature_version: str
    feature_schema_hash: str
    created_at: str  # ISO8601


class LabelDefinition(BaseModel):
    """Pinned mapping from `return_h6` to binary label. Stored alongside
    the model so a future audit can replay the exact thresholding.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(default=LABEL_DEFINITION_VERSION)
    epsilon: float = Field(default=LABEL_NEUTRAL_EPSILON, ge=0.0)
    target: TargetName = Field(default=TargetName.DIRECTION_H6)
    rule: str = Field(
        default=(
            "y=1 if return_h6 > +epsilon; "
            "y=0 if return_h6 < -epsilon; "
            "DROP if |return_h6| <= epsilon"
        )
    )


class LabelExtractionResult(BaseModel):
    """Output of ILabelExtractor.apply: kept indices + binary y + counters."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    kept_indices: List[int]
    y: List[int]                       # 0/1, len == len(kept_indices)
    neutral_dropped_count: int
    positive_count: int
    negative_count: int
    label_definition: LabelDefinition


class SplitResult(BaseModel):
    """Indices, not full vectors. Implementations slice the snapshot."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: SplitStrategy
    purge_gap_bars: int = Field(default=PURGE_GAP_BARS_INVARIANT, ge=0)
    train_indices: List[int]
    eval_indices: List[int]
    cv_folds: Optional[List[Dict[str, List[int]]]] = None  # walk_forward only


class ClassWeights(BaseModel):
    """Output of IClassWeightCalculator. Logged in training_report.json."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    class_freq: Dict[str, float]       # {"0": 0.70, "1": 0.30}
    class_weights: Dict[str, float]    # {"0": 1.0,  "1": 2.33}
    strategy: str = Field(default="inverse_frequency")  # v1 only


class ClassBalance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    counts: Dict[str, int]                         # e.g. {"0": 1242, "1": 1318}
    ratios: Dict[str, float]
    min_class_ratio: float


class ConfusionMatrix(BaseModel):
    """Binary v1 layout. Multi-class v2 will subclass."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    tn: int
    fp: int
    fn: int
    tp: int


class MetricsByBucket(BaseModel):
    """Generic bucketed-metric container used by both confidence and
    signal_strength reports. Buckets are stable, deterministic strings."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    bucket_key: str  # e.g. "confidence" / "signal_strength"
    buckets: List[Dict[str, Any]]
    # each bucket: {label: str, lo: float|null, hi: float|null,
    #               n: int, accuracy: float|null}


class BaselineMetrics(BaseModel):
    """Mandatory comparison against trivial baselines (§6.5)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    majority_accuracy: float
    random_proportional_accuracy: float
    coin_flip_accuracy: float = Field(default=0.5)
    model_minus_majority_pp: float
    passes_baseline_floor: bool
    baseline_seed: int = Field(default=BASELINE_SEED)
    baseline_delta_min: float = Field(default=BASELINE_DELTA_MIN)


class EvaluationReport(BaseModel):
    """Pinned shape of the v1.1 metrics block. Stored in the registry doc
    and in `training_report.json` next to the model."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: TargetName
    label_definition: LabelDefinition
    n_train: int
    n_eval: int
    primary: Dict[str, float]                    # {"direction_accuracy": 0.x}
    secondary: Dict[str, Any]                    # precision/recall/f1/roc_auc...
    confusion_matrix: ConfusionMatrix
    class_balance: ClassBalance
    class_weights: ClassWeights
    accuracy_by_confidence_bucket: MetricsByBucket
    accuracy_by_signal_strength: MetricsByBucket
    confidence_calibrated_ok: bool               # §6.4 monotonicity test
    confidence_monotonic_delta: float = Field(default=CONFIDENCE_MONOTONIC_DELTA)
    baseline: BaselineMetrics                    # §6.5
    temporal_drift: Dict[str, Any]               # {first_half_acc, second_half_acc, delta, warning: bool}
    feature_importance: Optional[Dict[str, float]] = None  # decision pinned in §11.3
    neutral_dropped_count: int                   # echoed from LabelExtractionResult


class ModelMeta(BaseModel):
    """Full registry document shape (Mongo-backed)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str
    symbol: str
    tf: str
    target: TargetName
    label_definition: LabelDefinition           # v1.1
    model_type: ModelType
    feature_version: str
    feature_schema_hash: str
    dataset_snapshot_id: str                    # alias of dataset_snapshot_hash
    dataset_snapshot_hash: str                  # canonical (v1.1)
    train_config_hash: str                      # v1.1
    dataset_size: int
    split_strategy: SplitStrategy
    purge_gap: int
    seed: int
    trainer_version: str = TRAINER_VERSION
    trainer_builder_version: str = TRAINER_BUILDER_VERSION
    git_sha: Optional[str] = None
    created_at: str
    trained_in_ms: float
    metrics: EvaluationReport
    artifact_path: str
    s3_uri: Optional[str] = None
    status: ModelStatus = ModelStatus.TRAINED
    deprecated_at: Optional[str] = None
    deprecated_reason: Optional[str] = None
    failure_reason: Optional[str] = None        # set when status="failed"
    notes: Optional[str] = None


class TrainArtifact(BaseModel):
    """Result of a successful training run, returned by ITrainOrchestrator."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    model_id: str
    artifact_path: str
    meta: ModelMeta
    elapsed_ms: float


class GateCheckResult(BaseModel):
    """Output of ITrainGate.check_for_pair(symbol, tf)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool                                      # gate passes for THIS pair
    gate_status: GateStatusEnum                   # global red/yellow/green
    pair: str                                     # "BTCUSDT_1H"
    live_evaluated: int
    required: int = LIVE_GATE_MIN_SAMPLES_PER_PAIR
    by_pair: Dict[str, Dict[str, Any]]            # full snapshot for the response
    scoring_basis: str = "live_evaluated_only"
    sim_counts_observability_only: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


# ═══ INTERFACES (ABCs — every method NotImplementedError) ══════════════════
class IDatasetSnapshotProvider(ABC):
    """Turns the live, evaluated, schema-matching dataset rows into a frozen
    snapshot suitable for one deterministic training run."""

    @abstractmethod
    def build_snapshot(self, *, symbol: str, tf: str) -> DatasetSnapshot:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def load_features_and_targets(
        self, snapshot: DatasetSnapshot
    ) -> Tuple[List[Dict[str, Any]], List[Any]]:
        """Returns (X_records, raw_returns) preserving snapshot.sample_ids order.

        Note: this returns RAW `return_h6` values, not binary y. Binary
        labels are produced by `ILabelExtractor.apply` (§2.4).
        """
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def compute_dataset_snapshot_hash(self, sample_ids: List[str]) -> str:
        """sha256(\"\\n\".join(sorted(sample_ids))).

        The trainer relies on this exact formula to derive `model_id`. Do
        NOT introduce alternative orderings, separators, or salts.
        """
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class ILabelExtractor(ABC):
    """Applies the §2.4 ε contract to raw `return_h6` values.

    Implementations MUST:
      * use LABEL_NEUTRAL_EPSILON unless overridden by an architect-bumped
        LabelDefinition (and the bump must be reflected in the version);
      * drop |return| <= ε, NOT relabel as 0;
      * preserve the relative ordering of kept indices.
    """

    @abstractmethod
    def apply(
        self,
        *,
        raw_returns: List[float],
        definition: LabelDefinition = LabelDefinition(),
    ) -> LabelExtractionResult:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class ISplitter(ABC):
    """Strategy-driven train/eval splitter. purge_gap is INVARIANT — passing
    a different value MUST raise."""

    @abstractmethod
    def split(
        self,
        snapshot: DatasetSnapshot,
        *,
        kept_indices: List[int],
        strategy: SplitStrategy = SplitStrategy.TIME_SPLIT_PURGE_GAP,
        purge_gap_bars: int = PURGE_GAP_BARS_INVARIANT,
    ) -> SplitResult:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class IClassWeightCalculator(ABC):
    """§2.5 — produces inverse-frequency class weights."""

    @abstractmethod
    def compute(self, *, y_train: List[int]) -> ClassWeights:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class ITrainer(ABC):
    """Fits ONE model on the provided split. v1 = lightgbm_binary on direction_h6.
    Implementations must call _set_global_seeds(seed) before any randomness.
    Class weights MUST be passed through to the underlying estimator.
    """

    @abstractmethod
    def fit(
        self,
        *,
        config: TrainConfig,
        snapshot: DatasetSnapshot,
        split: SplitResult,
        X: List[Dict[str, Any]],
        y: List[int],
        class_weights: ClassWeights,
    ) -> Any:
        """Returns the fitted estimator object (opaque to callers)."""
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class IBaselineEvaluator(ABC):
    """§6.5 — computes majority / random_proportional / coin_flip baselines."""

    @abstractmethod
    def evaluate(
        self,
        *,
        y_train: List[int],
        y_eval: List[int],
        seed: int = BASELINE_SEED,
    ) -> BaselineMetrics:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class IEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        *,
        estimator: Any,
        config: TrainConfig,
        snapshot: DatasetSnapshot,
        split: SplitResult,
        X: List[Dict[str, Any]],
        y: List[int],
        class_weights: ClassWeights,
        baseline: BaselineMetrics,
        label_definition: LabelDefinition,
        neutral_dropped_count: int,
    ) -> EvaluationReport:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class IArtifactStore(ABC):
    """Local FS read/write. Atomic. Idempotent. No cleverness."""

    @abstractmethod
    def write(
        self,
        *,
        model_id: str,
        estimator: Any,
        meta: ModelMeta,
        report: EvaluationReport,
        config: TrainConfig,
        snapshot: DatasetSnapshot,
    ) -> str:
        """Returns the directory path under /app/backend/data/models/.

        Implementations MUST also drop `dataset_snapshot.txt` and
        `dataset_snapshot_hash.txt` next to the artefact (see SPEC §4.1).
        """
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def load(self, *, model_id: str) -> Any:
        """Returns the fitted estimator. Raises ModelLoadError on any drift,
        including dataset_snapshot_hash mismatch between meta.json and the
        re-hashed dataset_snapshot.txt."""
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def mirror_to_s3(self, *, model_id: str) -> Optional[str]:
        """Optional. No-op (returns None) when feature flag is OFF."""
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class IModelRegistry(ABC):
    """Mongo-backed registry. Stores metadata + pointer ONLY (NEVER bytes)."""

    @abstractmethod
    def upsert(self, meta: ModelMeta) -> None:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def get(self, *, model_id: str) -> Optional[ModelMeta]:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def list(
        self,
        *,
        symbol: Optional[str] = None,
        tf: Optional[str] = None,
        status: Optional[ModelStatus] = None,
        limit: int = 50,
    ) -> List[ModelMeta]:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def deprecate(self, *, model_id: str, reason: str) -> ModelMeta:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class ITrainGate(ABC):
    """The ONLY component allowed to decide whether training may proceed.
    Reads ml_readiness.samples_by_source.live_evaluated. Sim counts MUST
    NOT influence ok/gate_status; they appear only in
    sim_counts_observability_only for the response."""

    @abstractmethod
    def check_for_pair(self, *, symbol: str, tf: str) -> GateCheckResult:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def snapshot(self) -> GateCheckResult:
        """Full multi-pair snapshot, used by GET /gate."""
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


class ITrainOrchestrator(ABC):
    """Composes the eleven interfaces. Owns NO business logic of its own.

    Required execution order (must be enforced by the implementation):
        1. gate.check_for_pair() — raise MLGateNotSatisfiedError if not ok
        2. provider.build_snapshot()
        3. provider.load_features_and_targets()  (raw returns, not labels)
        4. label_extractor.apply()                (§2.4 ε + drop neutral)
        5. splitter.split(kept_indices=...)
        6. weights = class_weight_calc.compute(y_train)
        7. estimator = trainer.fit(..., class_weights=weights)
        8. baseline = baseline_evaluator.evaluate(y_train, y_eval)
        9. report = evaluator.evaluate(
               ..., class_weights=weights,
               baseline=baseline,
               label_definition=...,
               neutral_dropped_count=...,
           )
       10. compute model_id from (feature_schema_hash,
                                  dataset_snapshot_hash,
                                  train_config_hash)
       11. store.write(model_id=..., ...)
       12. registry.upsert(meta)
       13. store.mirror_to_s3()  (no-op when flag off)

    If `report.baseline.passes_baseline_floor` is False, the registry doc
    is upserted with `status=ModelStatus.FAILED` and
    `failure_reason="below_baseline_floor"`. Local artefact remains for
    forensics; loader will refuse to serve it.
    """

    @abstractmethod
    def run(self, request: TrainRequest) -> TrainArtifact:
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")

    @abstractmethod
    def compute_model_id(
        self,
        *,
        feature_schema_hash: str,
        dataset_snapshot_hash: str,
        train_config_hash: str,
    ) -> str:
        """Pinned formula (§1.6):

            sha256(
                f"{MODEL_ID_NAMESPACE}|"
                f"{feature_schema_hash}|"
                f"{dataset_snapshot_hash}|"
                f"{train_config_hash}"
            ).hexdigest()

        No salt, no timestamp, no per-process randomness. Implementations
        that deviate from this formula MUST be rejected at code review.
        """
        raise NotImplementedError("Step 11 v1 not implemented (design phase)")


# ═══ Determinism helper (signature-only; body forbidden until v1) ══════════
def _set_global_seeds(seed: int = DEFAULT_SEED) -> None:
    """Pin random / numpy / lightgbm seeds atomically.

    The body is deliberately not implemented in design phase: even this
    helper is forbidden to leak partial training behaviour.
    """
    raise NotImplementedError("seed helper is not implemented in design phase")


__all__ = [
    # Versioning
    "STEP11_TRAINER_SPEC_VERSION",
    "TRAINER_VERSION",
    "TRAINER_BUILDER_VERSION",
    "LABEL_DEFINITION_VERSION",
    "MODEL_ID_NAMESPACE",
    # Invariants
    "PURGE_GAP_BARS_INVARIANT",
    "LIVE_GATE_MIN_SAMPLES_PER_PAIR",
    "MIN_CLASS_RATIO_INVARIANT",
    "DEFAULT_SEED",
    "BASELINE_SEED",
    "V1_PRIMARY_TARGET",
    "LABEL_NEUTRAL_EPSILON",
    "BASELINE_DELTA_MIN",
    "CONFIDENCE_BUCKETS",
    "CONFIDENCE_MONOTONIC_DELTA",
    "TEMPORAL_DRIFT_WARNING_DELTA",
    # Enums
    "SplitStrategy",
    "TargetName",
    "ModelType",
    "GateStatusEnum",
    "ModelStatus",
    "ConfidenceBucket",
    # Errors
    "StepElevenError",
    "MLGateNotSatisfiedError",
    "FeatureSchemaMismatch",
    "InsufficientSplitSamplesError",
    "ImbalancedClassesError",
    "LabelExtractionError",
    "UnsupportedConfidenceError",
    "ConcurrentTrainRunError",
    "ArtifactWriteError",
    "RegistryWriteError",
    "ModelLoadError",
    # Data shells
    "TrainConfig",
    "TrainRequest",
    "DatasetSnapshot",
    "LabelDefinition",
    "LabelExtractionResult",
    "SplitResult",
    "ClassWeights",
    "ClassBalance",
    "ConfusionMatrix",
    "MetricsByBucket",
    "BaselineMetrics",
    "EvaluationReport",
    "ModelMeta",
    "TrainArtifact",
    "GateCheckResult",
    # Interfaces
    "IDatasetSnapshotProvider",
    "ILabelExtractor",
    "ISplitter",
    "IClassWeightCalculator",
    "ITrainer",
    "IBaselineEvaluator",
    "IEvaluator",
    "IArtifactStore",
    "IModelRegistry",
    "ITrainGate",
    "ITrainOrchestrator",
    # Determinism helper
    "_set_global_seeds",
]
