from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests


RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"


@dataclass
class RxNormResult:
    original: str
    rxcui: Optional[str]
    generic_rxcui: Optional[str]
    generic_name: Optional[str]


class RxNormClient:
    def __init__(self, base_url: str = RXNAV_BASE, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cache: Dict[str, RxNormResult] = {}

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}.json"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def find_rxcui_by_name(self, name: str) -> Optional[str]:
        data = self._get("rxcui", {"name": name})
        idg = data.get("idGroup", {})
        ids = idg.get("rxnormId") or idg.get("conceptGroup")
        if isinstance(ids, list) and ids:
            return str(ids[0])
        if isinstance(ids, str):
            return ids
        return None

    def approximate_term(self, term: str, max_entries: int = 5) -> Optional[str]:
        data = self._get("approximateTerm", {"term": term, "maxEntries": max_entries})
        candidates = data.get("approximateGroup", {}).get("candidate") or []
        if not candidates:
            return None
        # pick the top candidate
        top = candidates[0]
        return top.get("rxcui")

    def get_generic_rxcui(self, rxcui: str) -> Optional[str]:
        data = self._get(f"rxcui/{rxcui}/generic")
        idg = data.get("idGroup", {})
        ids = idg.get("rxnormId")
        if ids:
            return str(ids[0])
        return None

    def get_properties(self, rxcui: str) -> Optional[Dict[str, Any]]:
        data = self._get(f"rxcui/{rxcui}/properties")
        return data.get("properties")

    def normalize_name(self, name: str) -> RxNormResult:
        if name in self._cache:
            return self._cache[name]

        rxcui = self.find_rxcui_by_name(name)
        if not rxcui:
            rxcui = self.approximate_term(name)

        generic_rxcui = None
        generic_name = None
        if rxcui:
            try:
                generic_rxcui = self.get_generic_rxcui(rxcui)
            except Exception:
                generic_rxcui = None

            target = generic_rxcui or rxcui
            try:
                props = self.get_properties(target)
                if props:
                    generic_name = props.get("name")
            except Exception:
                generic_name = None

        res = RxNormResult(original=name, rxcui=rxcui, generic_rxcui=generic_rxcui, generic_name=generic_name)
        self._cache[name] = res
        return res
