"""Margin SDK — Stripe-style client for MetricGraph ingest + KG."""

from margin.client import Client
from margin._config import configure

__all__ = ["configure", "Client"]
