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


async def fetch_tasks(user_id):
    url = f"{SUPABASE_URL}/rest/v1/tasks?select=*,giver:users(id,alias)&receiver:users(id,alias)&receiver_id=eq.{user_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200:
            tasks = r.json()
            # Gabungkan alias pemberi
            for task in tasks:
                task["giver_alias"] = task["giver"]["alias"]
            return tasks
        else:
            logging.error(f"fetch_tasks error: {r.text}")
            return []


async def fetch_pending_users():
    url = f"{SUPABASE_URL}/rest/v1/pending_users?select=*"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
        else:
            logging.error(f"fetch_pending_users error: {r.text}")
            return []


async def register_pending_user(user):
    url = f"{SUPABASE_URL}/rest/v1/pending_users"
    payload = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "requested_by": user.id,
        "requested_at": datetime.utcnow().isoformat()
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=HEADERS)
        if r.status_code in (200, 201):
            return True
        else:
            logging.error(f"register_pending_user error: {r.text}")
            return False


async def approve_user(user_id, alias, division, can_assign):
    url = f"{SUPABASE_URL}/rest/v1/users"
    payload = {
        "id": user_id,
        "alias": alias,
        "division": division,
        "can_assign": can_assign
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=HEADERS)
        if r.status_code in (200, 201):
            # Hapus dari pending
            del_url = f"{SUPABASE_URL}/rest/v1/pending_users?id=eq.{user_id}"
            await client.delete(del_url, headers=HEADERS)
            return True
        else:
            logging.error(f"approve_user error: {r.text}")
            return False
