#!/usr/bin/env python3
"""Dump raw gridX /live API response for debugging."""

import asyncio
import json
import sys

import aiohttp

sys.path.insert(0, "custom_components/gridx")
from const import (
    API_LIVE_URL,
    API_GATEWAYS_URL,
    AUTH0_AUDIENCE,
    AUTH0_CLIENT_ID,
    AUTH0_GRANT_TYPE,
    AUTH0_REALM,
    AUTH0_SCOPE,
    AUTH0_TOKEN_URL,
)


async def main():
    # Read credentials from HA config
    with open("/Volumes/config/.storage/core.config_entries") as f:
        data = json.load(f)
    for entry in data["data"]["entries"]:
        if entry.get("domain") == "gridx":
            email = entry["data"]["email"]
            password = entry["data"]["password"]
            system_ids = entry["data"]["system_ids"]
            break
    else:
        print("No gridx config entry found")
        return

    async with aiohttp.ClientSession() as session:
        # Authenticate
        payload = {
            "grant_type": AUTH0_GRANT_TYPE,
            "username": email,
            "password": password,
            "client_id": AUTH0_CLIENT_ID,
            "audience": AUTH0_AUDIENCE,
            "realm": AUTH0_REALM,
            "scope": AUTH0_SCOPE,
        }
        async with session.post(AUTH0_TOKEN_URL, json=payload) as resp:
            if resp.status != 200:
                print(f"Auth failed: {resp.status} {await resp.text()}")
                return
            token_data = await resp.json()

        id_token = token_data["id_token"]
        headers = {"Authorization": f"Bearer {id_token}"}

        # Dump gateways
        async with session.get(API_GATEWAYS_URL, headers=headers) as resp:
            gw_data = await resp.json()
            print("=== GATEWAYS ===")
            print(json.dumps(gw_data, indent=2, default=str)[:2000])
            print()

        # Dump live data for each system
        for sid in system_ids:
            url = API_LIVE_URL.format(sid)
            async with session.get(url, headers=headers) as resp:
                live_data = await resp.json()
                print(f"=== LIVE DATA (system {sid}) ===")
                print(json.dumps(live_data, indent=2, default=str))


asyncio.run(main())
