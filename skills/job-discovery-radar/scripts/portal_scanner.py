#!/usr/bin/env python3
"""Job Career Portal Scanner & SSRF Guard.

Validates target career URLs for SSRF safety and identifies enterprise ATS platform engines:
- Greenhouse
- Lever
- Ashby
- Workday
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import sys
from urllib.parse import urlparse

ATS_PLATFORMS = {
    "boards.greenhouse.io": "Greenhouse",
    "jobs.lever.co": "Lever",
    "jobs.ashbyhq.com": "Ashby",
}


def is_ssrf_safe(hostname: str) -> tuple[bool, str]:
    try:
        ip_strs = socket.gethostbyname_ex(hostname)[2]
        for ip_str in ip_strs:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"Resolved to non-public IP: {ip_str}"
        return True, "Safe public IP"
    except Exception as e:
        return False, f"DNS resolution failed: {e}"


def analyze_career_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return {
            "url": url,
            "status": "REJECTED",
            "error": "Non-HTTPS URLs are prohibited",
        }

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return {"url": url, "status": "REJECTED", "error": "Invalid URL hostname"}

    safe, reason = is_ssrf_safe(hostname)
    if not safe:
        return {
            "url": url,
            "hostname": hostname,
            "status": "SSRF_DENIED",
            "reason": reason,
        }

    # Identify platform
    platform = ATS_PLATFORMS.get(hostname)
    if not platform:
        if hostname.endswith(".myworkdayjobs.com"):
            platform = "Workday"
        else:
            platform = "Direct Company Career Portal"

    return {
        "url": url,
        "hostname": hostname,
        "platform": platform,
        "status": "VERIFIED_SAFE",
        "ssrf_verdict": reason,
    }


def main():
    parser = argparse.ArgumentParser(description="Job Career Portal SSRF & Platform Verifier")
    parser.add_argument("url", help="Job posting or career portal URL to analyze")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    result = analyze_career_url(args.url)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"URL: {result['url']}")
        print(f"Status: {result['status']}")
        if "platform" in result:
            print(f"Platform: {result['platform']}")
        if "reason" in result or "error" in result:
            print(f"Details: {result.get('reason') or result.get('error')}")


if __name__ == "__main__":
    main()
