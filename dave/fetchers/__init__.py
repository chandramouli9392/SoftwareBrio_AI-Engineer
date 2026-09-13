"""Fetcher backends for DAVE."""

from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult
from dave.fetchers.http import HttpFetcher
from dave.fetchers.playwright import PlaywrightFetcher

__all__ = ["BaseFetcher", "FetchRequest", "FetchResult", "HttpFetcher", "PlaywrightFetcher"]
