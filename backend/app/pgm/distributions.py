"""
Distribution sampling utilities for Monte Carlo simulation.

All samplers are deterministic given a numpy RandomState seed, enabling
reproducible simulations for testing and demo mode.
"""

from __future__ import annotations

import numpy as np
from numpy.random import RandomState

from app.pgm.graph import NodeDistribution


def sample_distribution(
    dist: NodeDistribution,
    n: int,
    rng: RandomState,
    clip_low: float | None = 0.0,
    clip_high: float | None = None,
) -> np.ndarray:
    """
    Sample n values from the given distribution.

    Supports: normal, beta, uniform, bernoulli, deterministic.
    Clips output to [clip_low, clip_high] when specified.
    """
    samples: np.ndarray

    if dist.type == "normal":
        mean = dist.mean if dist.mean is not None else 0.5
        std = dist.std if dist.std is not None else 0.1
        samples = rng.normal(loc=mean, scale=std, size=n)

    elif dist.type == "beta":
        alpha = dist.alpha if dist.alpha is not None else 2.0
        beta = dist.beta if dist.beta is not None else 2.0
        # Beta is inherently [0,1]
        samples = rng.beta(a=alpha, b=beta, size=n)
        clip_low = 0.0
        clip_high = 1.0

    elif dist.type == "uniform":
        low = dist.low if dist.low is not None else 0.0
        high = dist.high if dist.high is not None else 1.0
        samples = rng.uniform(low=low, high=high, size=n)

    elif dist.type == "bernoulli":
        p = dist.probability if dist.probability is not None else 0.5
        samples = rng.binomial(n=1, p=p, size=n).astype(float)
        clip_low = 0.0
        clip_high = 1.0

    elif dist.type == "deterministic":
        val = dist.mean if dist.mean is not None else 0.0
        samples = np.full(n, val)

    else:
        # Default fallback to uniform [0,1]
        samples = rng.uniform(0.0, 1.0, size=n)

    # Apply clipping
    lo = clip_low if clip_low is not None else -np.inf
    hi = clip_high if clip_high is not None else np.inf
    return np.clip(samples, lo, hi)


def beta_mean(alpha: float, beta: float) -> float:
    """Return the mean of a Beta(alpha, beta) distribution."""
    return alpha / (alpha + beta)


def beta_variance(alpha: float, beta: float) -> float:
    """Return the variance of a Beta(alpha, beta) distribution."""
    return (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))


def compute_outcome_distribution(samples: np.ndarray) -> dict:
    """Compute summary statistics from an array of Monte Carlo samples."""
    return {
        "mean": float(np.mean(samples)),
        "median": float(np.median(samples)),
        "std": float(np.std(samples)),
        "p10": float(np.percentile(samples, 10)),
        "p25": float(np.percentile(samples, 25)),
        "p75": float(np.percentile(samples, 75)),
        "p90": float(np.percentile(samples, 90)),
        "min": float(np.min(samples)),
        "max": float(np.max(samples)),
        "prob_target": 0.0,  # Filled by caller with target
    }
