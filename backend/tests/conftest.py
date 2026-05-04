"""
Pytest Configuration
"""
import os
import pytest

# Set BASE_URL for API tests
def pytest_configure(config):
    """Set environment variables before tests run."""
    if not os.environ.get('REACT_APP_BACKEND_URL'):
        os.environ['REACT_APP_BACKEND_URL'] = 'https://tech-analysis-core-1.preview.emergentagent.com'
