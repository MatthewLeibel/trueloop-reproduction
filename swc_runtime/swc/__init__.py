from .client import (
    SWCOptimizer, Regime, swc_regulate,
    SWCError, SWCAuthError, SWCLicenseExpired,
    SWCSessionError, SWCServerError, SWCNetworkError, OutOfEnvelope,
)
__version__ = "0.2.0"
__all__ = [
    "SWCOptimizer", "Regime", "swc_regulate",
    "SWCError", "SWCAuthError", "SWCLicenseExpired",
    "SWCSessionError", "SWCServerError", "SWCNetworkError", "OutOfEnvelope",
]
