# === FILE: db.py ===
import os
import httpx
import logging
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


async def fetch_user(user_id):
    url = f"{SUPABASE_URL}/rest/v1/users?select=*&id=eq.{user_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200 and r.json():
            return r.json()[0]
        return None


async def fetch_user_by_alias(alias):
    url = f"{SUPABASE_URL}/rest/v1/users?select=*&alias=eq.{alias}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200 and r.json():
            return r.json()[0]
        return None


async def fetch_all_users():
    url = f"{SUPABASE_URL}/rest/v1/users?select=id"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
        else:
            logging.error(f"fetch_all_users error: {r.text}")
            return []


async def fetch_tasks_
