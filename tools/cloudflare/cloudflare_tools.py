"""tools/cloudflare/cloudflare_tools.py — Cloudflare DNS, cache, and WAF tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from integrations.cloudflare_client import CloudflareClient

# ── cloudflare_list_zones ─────────────────────────────────────────────────────

LIST_ZONES_TOOL_NAME = "cloudflare_list_zones"
LIST_ZONES_TOOL_DESCRIPTION = (
    "List all Cloudflare zones (domains) in the account with their IDs and status. "
    "Requires CLOUDFLARE_API_TOKEN."
)
LIST_ZONES_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def list_zones_handler() -> List[Dict]:
    return CloudflareClient().list_zones()


# ── cloudflare_list_dns_records ───────────────────────────────────────────────

LIST_DNS_TOOL_NAME = "cloudflare_list_dns_records"
LIST_DNS_TOOL_DESCRIPTION = "List DNS records for a Cloudflare zone. Optionally filter by record type (A, CNAME, MX, etc.)."
LIST_DNS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone_id": {"type": "string", "description": "Cloudflare zone ID."},
        "record_type": {"type": "string", "description": "DNS record type to filter (e.g. 'A', 'CNAME', 'MX'). Omit for all."},
    },
    "required": ["zone_id"],
    "additionalProperties": False,
}


def list_dns_handler(zone_id: str, record_type: Optional[str] = None) -> List[Dict]:
    return CloudflareClient().list_dns_records(zone_id, record_type=record_type)


# ── cloudflare_create_dns_record ──────────────────────────────────────────────

CREATE_DNS_TOOL_NAME = "cloudflare_create_dns_record"
CREATE_DNS_TOOL_DESCRIPTION = "Create a DNS record in a Cloudflare zone."
CREATE_DNS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone_id": {"type": "string", "description": "Cloudflare zone ID."},
        "record_type": {"type": "string", "description": "DNS record type (A, CNAME, MX, TXT, etc.)."},
        "name": {"type": "string", "description": "DNS record name (e.g. 'api.example.com')."},
        "content": {"type": "string", "description": "Record value (IP, hostname, text, etc.)."},
        "ttl": {"type": "integer", "description": "TTL in seconds (1 = auto, default: 1).", "default": 1},
        "proxied": {"type": "boolean", "description": "Proxy through Cloudflare (default: false).", "default": False},
    },
    "required": ["zone_id", "record_type", "name", "content"],
    "additionalProperties": False,
}


def create_dns_handler(zone_id: str, record_type: str, name: str, content: str, ttl: int = 1, proxied: bool = False) -> Dict:
    return CloudflareClient().create_dns_record(zone_id, record_type, name, content, ttl=ttl, proxied=proxied)


# ── cloudflare_delete_dns_record ──────────────────────────────────────────────

DELETE_DNS_TOOL_NAME = "cloudflare_delete_dns_record"
DELETE_DNS_TOOL_DESCRIPTION = "Delete a DNS record from a Cloudflare zone by record ID."
DELETE_DNS_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone_id": {"type": "string", "description": "Cloudflare zone ID."},
        "record_id": {"type": "string", "description": "DNS record ID to delete."},
    },
    "required": ["zone_id", "record_id"],
    "additionalProperties": False,
}


def delete_dns_handler(zone_id: str, record_id: str) -> Dict:
    return CloudflareClient().delete_dns_record(zone_id, record_id)


# ── cloudflare_purge_cache ────────────────────────────────────────────────────

PURGE_CACHE_TOOL_NAME = "cloudflare_purge_cache"
PURGE_CACHE_TOOL_DESCRIPTION = (
    "Purge Cloudflare cache for a zone. "
    "Provide specific URLs to purge, or leave empty to purge everything."
)
PURGE_CACHE_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone_id": {"type": "string", "description": "Cloudflare zone ID."},
        "urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific URLs to purge (omit to purge entire cache).",
        },
    },
    "required": ["zone_id"],
    "additionalProperties": False,
}


def purge_cache_handler(zone_id: str, urls: Optional[List[str]] = None) -> Dict:
    return CloudflareClient().purge_cache(zone_id, urls=urls)


# ── cloudflare_list_waf_rules ─────────────────────────────────────────────────

LIST_WAF_TOOL_NAME = "cloudflare_list_waf_rules"
LIST_WAF_TOOL_DESCRIPTION = "List WAF firewall rules for a Cloudflare zone."
LIST_WAF_TOOL_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone_id": {"type": "string", "description": "Cloudflare zone ID."},
    },
    "required": ["zone_id"],
    "additionalProperties": False,
}


def list_waf_handler(zone_id: str) -> List[Dict]:
    return CloudflareClient().list_waf_rules(zone_id)
