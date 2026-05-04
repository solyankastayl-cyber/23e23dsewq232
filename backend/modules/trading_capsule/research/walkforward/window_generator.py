"""
Window Generator (S2.6A)
========================

Generates train/test windows for Walk Forward analysis.

Rules:
1. train_end < test_start (NO look-ahead bias)
2. Windows are deterministic
3. No overlapping train/test periods

Example:
- Dataset: 2019-2024 (2190 bars daily)
- Train: 730 bars (~2 years)
- Test: 365 bars (~1 year)
- Step: 365 bars

Generates:
- Window 0: train[0:730], test[730:1095]
- Window 1: train[365:1095], test[1095:1460]
- Window 2: train[730:1460], test[1460:1825]
- ...
"""

from typing import List, Optional
from datetime import datetime, timedelta
import threading

from .walkforward_types import WalkForwardWindow


class WindowGenerator:
    """
    Generates Walk Forward windows.
    
    Thread-safe singleton.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        print("[WindowGenerator] Initialized")
    
    def generate_windows(
        self,
        experiment_id: str,
        dataset_length_bars: int,
        train_window_bars: int,
        test_window_bars: int,
        step_bars: int,
        start_date: Optional[str] = None,
        timeframe: str = "1D"
    ) -> List[WalkForwardWindow]:
        """
        Generate Walk Forward windows.
        
        Args:
            experiment_id: Parent experiment ID
            dataset_length_bars: Total bars in dataset
            train_window_bars: Training window size
            test_window_bars: Test window size
            step_bars: Step size between windows
            start_date: Optional start date for date labeling
            timeframe: Timeframe for date calculation
            
        Returns:
            List of WalkForwardWindow
        """
        windows = []
        
        # Validate inputs
        min_required = train_window_bars + test_window_bars
        if dataset_length_bars < min_required:
            print(f"[WindowGenerator] Dataset too short: {dataset_length_bars} < {min_required}")
            return windows
        
        if train_window_bars <= 0 or test_window_bars <= 0 or step_bars <= 0:
            print("[WindowGenerator] Invalid window parameters")
            return windows
        
        # Parse start date if provided
        base_date = None
        if start_date:
            try:
                base_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                pass
        
        # Timeframe to days mapping
        tf_to_days = {
            "1D": 1,
            "4H": 1/6,
            "1H": 1/24
        }
        bars_per_day = 1 / tf_to_days.get(timeframe, 1)
        
        # Generate windows
        index = 0
        train_start = 0
        
        while True:
            train_end = train_start + train_window_bars
            test_start = train_end  # Test starts immediately after train
            test_end = test_start + test_window_bars
            
            # Check if we've exceeded dataset
            if test_end > dataset_length_bars:
                break
            
            # Create window
            window = WalkForwardWindow(
                experiment_id=experiment_id,
                index=index,
                train_start_bar=train_start,
                train_end_bar=train_end,
                test_start_bar=test_start,
                test_end_bar=test_end,
                train_bars=train_window_bars,
                test_bars=test_window_bars
            )
            
            # Add date labels if base_date provided
            if base_date:
                window.train_start_date = self._bar_to_date(
                    base_date, train_start, bars_per_day
                )
                window.train_end_date = self._bar_to_date(
                    base_date, train_end - 1, bars_per_day
                )
                window.test_start_date = self._bar_to_date(
                    base_date, test_start, bars_per_day
                )
                window.test_end_date = self._bar_to_date(
                    base_date, test_end - 1, bars_per_day
                )
            
            windows.append(window)
            
            # Move to next window
            train_start += step_bars
            index += 1
        
        print(f"[WindowGenerator] Generated {len(windows)} windows for experiment {experiment_id}")
        return windows
    
    def _bar_to_date(
        self,
        base_date: datetime,
        bar_index: int,
        bars_per_day: float
    ) -> str:
        """Convert bar index to date string"""
        days_offset = bar_index / bars_per_day
        target_date = base_date + timedelta(days=days_offset)
        return target_date.strftime("%Y-%m-%d")
    
    def validate_windows(
        self,
        windows: List[WalkForwardWindow]
    ) -> List[str]:
        """
        Validate windows for look-ahead bias and other issues.
        
        Returns list of validation errors.
        """
        errors = []
        
        for i, window in enumerate(windows):
            # Rule 1: train_end <= test_start (no overlap)
            if window.train_end_bar > window.test_start_bar:
                errors.append(
                    f"Window {i}: Train/test overlap detected "
                    f"(train_end={window.train_end_bar} > test_start={window.test_start_bar})"
                )
            
            # Check consecutive windows don't have test overlap with next train
            if i < len(windows) - 1:
                next_window = windows[i + 1]
                if window.test_end_bar > next_window.train_start_bar:
                    # This is actually allowed in standard walk-forward
                    # Only train/test within same window matters
                    pass
        
        return errors
    
    def calculate_windows_count(
        self,
        dataset_length_bars: int,
        train_window_bars: int,
        test_window_bars: int,
        step_bars: int
    ) -> int:
        """
        Calculate how many windows will be generated.
        
        Useful for preview before generation.
        """
        if dataset_length_bars < train_window_bars + test_window_bars:
            return 0
        
        count = 0
        train_start = 0
        
        while True:
            test_end = train_start + train_window_bars + test_window_bars
            if test_end > dataset_length_bars:
                break
            count += 1
            train_start += step_bars
        
        return count


# Global singleton
window_generator = WindowGenerator()
