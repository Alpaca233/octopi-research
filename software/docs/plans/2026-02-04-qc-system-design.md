# QC System Design

## Overview

This document describes the Quality Control (QC) system for the Squid microscope acquisition. The QC system:

1. **Collects metrics** per-FOV during acquisition (focus score, z-position, etc.)
2. **Stores metrics** for analysis and review
3. **Applies policies** to decide when to pause and which FOVs to flag for retake

## Design Goals

- QC runs in parallel with acquisition (as Jobs in subprocess)
- Clean separation: metrics collection vs. policy decisions
- Swappable QC methods for different applications
- Extensible for future automation
- Simple initial implementation focused on manual review

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MultiPointWorker                        │
│                                                              │
│  acquire_at_position()                                       │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐     dispatch      ┌─────────────────────┐  │
│  │ CameraFrame │ ─────────────────▶│ SaveImageJob        │  │
│  └─────────────┘        │          └─────────────────────┘  │
│                         │                                    │
│                         │          ┌─────────────────────┐  │
│                         └─────────▶│ QCJob               │  │
│                                    └──────────┬──────────┘  │
└───────────────────────────────────────────────│─────────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │     JobRunner         │
                                    │   (QC subprocess)     │
                                    │                       │
                                    │  ┌─────────────────┐  │
                                    │  │ QCMetricsCalc   │  │
                                    │  │ - focus_score() │  │
                                    │  │ - z_position()  │  │
                                    │  │ - ...           │  │
                                    │  └─────────────────┘  │
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │      QCResult         │
                                    │  (via output_queue)   │
                                    └───────────┬───────────┘
                                                │
                      ┌─────────────────────────┼─────────────────────────┐
                      │                         │                         │
                      ▼                         ▼                         ▼
           ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
           │ MetricsStore    │      │ QCPolicy        │      │ UI Display      │
           │ (per-timepoint) │◀────▶│ (check at end)  │      │ (live metrics)  │
           └─────────────────┘      └────────┬────────┘      └─────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ PolicyDecision  │
                                    │ - flagged_fovs  │
                                    │ - should_pause  │
                                    └─────────────────┘
```

## Components

### 1. QCJob

A Job subclass that runs in a subprocess, calculates metrics for a single FOV.

```python
@dataclass
class QCJob(Job[QCResult]):
    """Quality control job for a single FOV."""

    capture_info: CaptureInfo
    capture_image: JobImage
    qc_config: QCConfig
    previous_timepoint_z: Optional[float] = None  # For z-drift calculation

    def run(self) -> QCResult:
        image = self.capture_image.get_image()
        metrics = FOVMetrics(
            fov_id=FOVIdentifier(
                region_id=self.capture_info.region_id,
                fov_index=self.capture_info.fov,
            ),
            timestamp=self.capture_info.capture_time,
            z_position_um=self.capture_info.position.z_mm * 1000,
        )

        # Calculate enabled metrics
        if self.qc_config.calculate_focus_score:
            metrics.focus_score = calculate_focus_score(image)

        if self.qc_config.record_laser_af_displacement:
            metrics.laser_af_displacement_um = self.capture_info.z_piezo_um

        if self.previous_timepoint_z is not None:
            metrics.z_diff_from_last_timepoint_um = (
                metrics.z_position_um - self.previous_timepoint_z
            )

        return QCResult(metrics=metrics)
```

### 2. FOVMetrics

Data class holding all QC metrics for a single FOV.

```python
@dataclass
class FOVMetrics:
    """QC metrics for a single FOV."""

    fov_id: FOVIdentifier
    timestamp: float
    z_position_um: float

    # Optional metrics (calculated based on config)
    focus_score: Optional[float] = None
    laser_af_displacement_um: Optional[float] = None
    z_diff_from_last_timepoint_um: Optional[float] = None

    # Extensible: add more metrics as needed
    # e.g., saturation_percent, background_intensity, cell_count, etc.
```

### 3. QCResult

Result returned by QCJob.

```python
@dataclass
class QCResult:
    """Result from QC job."""

    metrics: FOVMetrics
    error: Optional[str] = None  # If QC calculation failed
```

### 4. TimepointMetricsStore

Holds all QC metrics for the current timepoint.

```python
class TimepointMetricsStore:
    """Stores QC metrics for a single timepoint."""

    def __init__(self, timepoint_index: int):
        self._timepoint = timepoint_index
        self._metrics: Dict[FOVIdentifier, FOVMetrics] = {}
        self._lock = threading.Lock()

    def add(self, metrics: FOVMetrics) -> None:
        """Add metrics for an FOV."""
        with self._lock:
            self._metrics[metrics.fov_id] = metrics

    def get(self, fov_id: FOVIdentifier) -> Optional[FOVMetrics]:
        """Get metrics for a specific FOV."""
        with self._lock:
            return self._metrics.get(fov_id)

    def get_all(self) -> List[FOVMetrics]:
        """Get all metrics for this timepoint."""
        with self._lock:
            return list(self._metrics.values())

    def get_metric_values(self, metric_name: str) -> Dict[FOVIdentifier, float]:
        """Get a specific metric across all FOVs."""
        with self._lock:
            result = {}
            for fov_id, m in self._metrics.items():
                value = getattr(m, metric_name, None)
                if value is not None:
                    result[fov_id] = value
            return result

    def to_dataframe(self) -> pd.DataFrame:
        """Export metrics as DataFrame for analysis."""
        ...

    def save(self, path: str) -> None:
        """Persist metrics to disk (CSV or JSON)."""
        ...
```

### 5. QCConfig

Configuration for which metrics to calculate.

```python
@dataclass
class QCConfig:
    """Configuration for QC metrics collection."""

    enabled: bool = False

    # Which metrics to calculate
    calculate_focus_score: bool = True
    record_laser_af_displacement: bool = False
    calculate_z_diff_from_last_timepoint: bool = False

    # Focus score method
    focus_score_method: str = "laplacian_variance"  # or "normalized_variance", etc.
```

### 6. QCPolicy

Configurable rules for deciding when to pause and which FOVs to flag.

```python
@dataclass
class QCPolicyConfig:
    """Configuration for QC policy decisions."""

    enabled: bool = False

    # When to run policy checks
    check_after_timepoint: bool = True
    # Future: check_after_fov: bool = False

    # Threshold-based rules
    focus_score_min: Optional[float] = None  # Flag FOVs below this
    z_drift_max_um: Optional[float] = None   # Flag FOVs exceeding this

    # Outlier detection
    detect_outliers: bool = False
    outlier_metric: str = "focus_score"      # Which metric to check
    outlier_std_threshold: float = 2.0       # Flag if > N std from mean

    # Action when FOVs are flagged
    pause_if_any_flagged: bool = True


class QCPolicy:
    """Evaluates QC metrics and decides on actions."""

    def __init__(self, config: QCPolicyConfig):
        self._config = config

    def check_timepoint(self, metrics_store: TimepointMetricsStore) -> PolicyDecision:
        """
        Evaluate all FOVs in a timepoint.
        Called when timepoint reaches CAPTURED state.

        Returns:
            PolicyDecision with flagged FOVs and whether to pause
        """
        flagged: List[FOVIdentifier] = []
        reasons: Dict[FOVIdentifier, List[str]] = {}

        all_metrics = metrics_store.get_all()

        # Threshold checks
        if self._config.focus_score_min is not None:
            for m in all_metrics:
                if m.focus_score is not None and m.focus_score < self._config.focus_score_min:
                    flagged.append(m.fov_id)
                    reasons.setdefault(m.fov_id, []).append(
                        f"focus_score={m.focus_score:.2f} < {self._config.focus_score_min}"
                    )

        if self._config.z_drift_max_um is not None:
            for m in all_metrics:
                if m.z_diff_from_last_timepoint_um is not None:
                    if abs(m.z_diff_from_last_timepoint_um) > self._config.z_drift_max_um:
                        if m.fov_id not in flagged:
                            flagged.append(m.fov_id)
                        reasons.setdefault(m.fov_id, []).append(
                            f"z_drift={m.z_diff_from_last_timepoint_um:.2f}um > {self._config.z_drift_max_um}"
                        )

        # Outlier detection
        if self._config.detect_outliers:
            outliers = self._detect_outliers(
                metrics_store,
                self._config.outlier_metric,
                self._config.outlier_std_threshold,
            )
            for fov_id in outliers:
                if fov_id not in flagged:
                    flagged.append(fov_id)
                reasons.setdefault(fov_id, []).append(
                    f"outlier in {self._config.outlier_metric}"
                )

        should_pause = self._config.pause_if_any_flagged and len(flagged) > 0

        return PolicyDecision(
            flagged_fovs=flagged,
            flag_reasons=reasons,
            should_pause=should_pause,
        )

    def _detect_outliers(
        self,
        metrics_store: TimepointMetricsStore,
        metric_name: str,
        std_threshold: float,
    ) -> List[FOVIdentifier]:
        """Detect outliers using standard deviation method."""
        values = metrics_store.get_metric_values(metric_name)
        if len(values) < 3:
            return []

        arr = np.array(list(values.values()))
        mean, std = arr.mean(), arr.std()

        outliers = []
        for fov_id, value in values.items():
            if abs(value - mean) > std_threshold * std:
                outliers.append(fov_id)

        return outliers

    # Future: add check_fov() for immediate per-FOV decisions
    # def check_fov(self, metrics: FOVMetrics) -> QCAction:
    #     """Called immediately after FOV QC completes."""
    #     if self._config.focus_score_min and metrics.focus_score < self._config.focus_score_min:
    #         return QCAction.PAUSE
    #     return QCAction.CONTINUE


@dataclass
class PolicyDecision:
    """Result of QC policy evaluation."""

    flagged_fovs: List[FOVIdentifier]
    flag_reasons: Dict[FOVIdentifier, List[str]]
    should_pause: bool
```

## Integration with Acquisition

### Job Dispatch

QCJob is dispatched alongside other jobs in `MultiPointWorker._image_callback()`:

```python
def _image_callback(self, camera_frame: CameraFrame):
    # ... existing job dispatch ...

    # Add QC job if enabled
    if self._qc_config.enabled:
        qc_job = QCJob(
            capture_info=info,
            capture_image=JobImage(camera_frame.frame.copy()),
            qc_config=self._qc_config,
            previous_timepoint_z=self._get_previous_timepoint_z(info.fov_id),
        )
        self._qc_job_runner.dispatch(qc_job)
```

### Result Processing

QC results are handled in `_summarize_runner_outputs()`:

```python
def _summarize_job_result(self, result: JobResult):
    if isinstance(result.result, QCResult):
        qc_result = result.result

        # Store metrics
        self._metrics_store.add(qc_result.metrics)

        # Emit signal for UI update
        self.callbacks.signal_qc_metrics_updated(qc_result.metrics)

        # Future: immediate per-FOV policy check
        # if self._qc_policy.check_fov(qc_result.metrics) == QCAction.PAUSE:
        #     self._state_machine.request_pause()
```

### Timepoint End Policy Check

When timepoint reaches CAPTURED state:

```python
def _on_timepoint_captured(self):
    # Run QC policy check
    if self._qc_policy_config.enabled and self._qc_policy_config.check_after_timepoint:
        decision = self._qc_policy.check_timepoint(self._metrics_store)

        # Emit signal with flagged FOVs for UI
        self.callbacks.signal_qc_policy_decision(decision)

        if decision.should_pause:
            self._state_machine.request_pause()
            # UI will show flagged FOVs, user can select retakes
```

## Focus Score Methods

Swappable focus score algorithms:

```python
def calculate_focus_score(image: np.ndarray, method: str = "laplacian_variance") -> float:
    """Calculate focus score using specified method."""

    if method == "laplacian_variance":
        # Variance of Laplacian - higher = more in focus
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        return laplacian.var()

    elif method == "normalized_variance":
        # Normalized variance - robust to intensity variations
        mean = image.mean()
        if mean == 0:
            return 0.0
        return image.var() / mean

    elif method == "gradient_magnitude":
        # Sum of gradient magnitudes
        gx = cv2.Sobel(image, cv2.CV_64F, 1, 0)
        gy = cv2.Sobel(image, cv2.CV_64F, 0, 1)
        return np.sqrt(gx**2 + gy**2).mean()

    elif method == "fft_high_freq":
        # High-frequency content in FFT
        fft = np.fft.fft2(image)
        fft_shift = np.fft.fftshift(fft)
        # Mask out low frequencies
        h, w = image.shape[:2]
        cy, cx = h // 2, w // 2
        mask_size = min(h, w) // 8
        fft_shift[cy-mask_size:cy+mask_size, cx-mask_size:cx+mask_size] = 0
        return np.abs(fft_shift).mean()

    else:
        raise ValueError(f"Unknown focus method: {method}")
```

## Signals for UI

```python
@dataclass
class QCSignals:
    # Per-FOV metrics (for live display)
    signal_qc_metrics_updated: Callable[[FOVMetrics], None]

    # Policy decision (at timepoint end)
    signal_qc_policy_decision: Callable[[PolicyDecision], None]
```

## Data Persistence

Metrics are saved alongside acquisition data:

```
{experiment_path}/
├── 000/                          # Timepoint 0
│   ├── images/
│   └── qc_metrics.csv            # QC metrics for this timepoint
├── 001/                          # Timepoint 1
│   ├── images/
│   └── qc_metrics.csv
└── qc_summary.json               # Overall QC summary
```

## Configuration Example

```yaml
# In acquisition config or separate qc_config.yaml

qc:
  enabled: true

  metrics:
    calculate_focus_score: true
    focus_score_method: "laplacian_variance"
    record_laser_af_displacement: true
    calculate_z_diff_from_last_timepoint: true

  policy:
    enabled: true
    check_after_timepoint: true

    # Threshold rules
    focus_score_min: 100.0
    z_drift_max_um: 5.0

    # Outlier detection
    detect_outliers: true
    outlier_metric: "focus_score"
    outlier_std_threshold: 2.0

    # Action
    pause_if_any_flagged: true
```

## Future Extensions

### 1. Immediate Per-FOV Pause

Add `check_fov()` to QCPolicy:

```python
def check_fov(self, metrics: FOVMetrics) -> QCAction:
    if self._config.focus_score_min and metrics.focus_score < self._config.focus_score_min:
        return QCAction.PAUSE
    return QCAction.CONTINUE
```

Call from `_summarize_job_result()` after storing metrics.

### 2. Custom QC Methods

Plugin system for custom QC calculations:

```python
class QCMethod(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def calculate(self, image: np.ndarray, capture_info: CaptureInfo) -> Dict[str, float]: ...

# Register custom methods
qc_registry.register(MyCustomQCMethod())
```

### 3. Cross-Timepoint Analysis

Compare metrics across timepoints:

```python
class AcquisitionMetricsStore:
    """Holds metrics for all timepoints."""

    def get_fov_history(self, fov_id: FOVIdentifier) -> List[FOVMetrics]:
        """Get metrics for an FOV across all timepoints."""
        ...

    def detect_drift_trend(self, fov_id: FOVIdentifier) -> DriftTrend:
        """Analyze z-drift trend over time."""
        ...
```

### 4. Automated Retake Strategies

Different retry behaviors per QC failure type:

```python
@dataclass
class RetakeStrategy:
    re_autofocus: bool = True
    adjust_exposure: bool = False
    max_attempts: int = 2
```

## Summary

| Component | Responsibility |
|-----------|----------------|
| `QCJob` | Calculates metrics per-FOV in subprocess |
| `FOVMetrics` | Data class for QC measurements |
| `TimepointMetricsStore` | Holds all metrics for current timepoint |
| `QCPolicy` | Evaluates metrics, decides when to pause |
| `PolicyDecision` | Result with flagged FOVs and actions |

The design prioritizes:
- **Parallel execution**: QC runs as Job, doesn't slow acquisition
- **Separation of concerns**: Metrics vs. policy decisions
- **Flexibility**: Swappable focus methods, configurable policies
- **Extensibility**: Easy to add immediate per-FOV checks later
