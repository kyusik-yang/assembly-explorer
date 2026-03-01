"""Async API client for 열린국회정보 (open.assembly.go.kr)."""

import os
from typing import Any, Optional

import httpx

BASE_URL = "https://open.assembly.go.kr/portal/openapi"

EP_BILLS        = "nzmimeepazxkubdpn"
EP_BILL_DETAIL  = "ALLBILL"
EP_BILL_REVIEW  = "nwbpacrgavhjryiph"
EP_MEMBER       = "nwvrqwxyaytdsfvhu"
EP_VOTE         = "ncocpgfiaoituanbr"
EP_BILL_PROPOSERS = "BILLINFOPPSR"

UNIT_CD_MAP = {"22": "100022", "21": "100021", "20": "100020", "19": "100019", "18": "100018"}


def _unit_cd(age: str) -> str:
    return UNIT_CD_MAP.get(age, f"1000{age}")


class AssemblyClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self._client.aclose()

    def _base(self) -> dict:
        return {"KEY": self.api_key, "Type": "json"}

    def _parse(self, data: dict, endpoint: str) -> list[dict]:
        body = data.get(endpoint, [])
        if not body:
            return []
        head = body[0].get("head", [])
        result = head[1].get("RESULT", {}) if len(head) > 1 else {}
        code = result.get("CODE", "")
        if code == "INFO-200":
            return []
        if code != "INFO-000":
            msg = result.get("MESSAGE", "Unknown error")
            raise ValueError(f"API error {code}: {msg}")
        rows = body[1].get("row", []) if len(body) > 1 else []
        return rows if isinstance(rows, list) else [rows]

    async def _get(self, endpoint: str, params: dict) -> list[dict]:
        merged = {**self._base(), **{k: v for k, v in params.items() if v is not None}}
        resp = await self._client.get(f"{BASE_URL}/{endpoint}", params=merged)
        resp.raise_for_status()
        return self._parse(resp.json(), endpoint)

    async def search_bills(self, age, bill_name=None, proposer=None,
                           proc_result=None, committee=None, page=1, page_size=20):
        return await self._get(EP_BILLS, {
            "AGE": age, "BILL_NAME": bill_name, "PROPOSER": proposer,
            "PROC_RESULT": proc_result, "COMMITTEE": committee,
            "pIndex": page, "pSize": page_size,
        })

    async def get_member_info(self, age="22", name=None, party=None,
                              district=None, committee=None, page=1, page_size=50):
        return await self._get(EP_MEMBER, {
            "UNIT_CD": _unit_cd(age), "HG_NM": name, "POLY_NM": party,
            "ORIG_NM": district, "CMIT_NM": committee,
            "pIndex": page, "pSize": page_size,
        })

    async def get_vote_results(self, age, bill_name=None, page=1, page_size=20):
        return await self._get(EP_VOTE, {
            "AGE": age, "BILL_NAME": bill_name,
            "pIndex": page, "pSize": page_size,
        })

    async def get_bill_proposers(self, bill_id: str):
        return await self._get(EP_BILL_PROPOSERS, {"BILL_ID": bill_id})
