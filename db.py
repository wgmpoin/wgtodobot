import os
from supabase import create_client, Client
from datetime import date
import logging

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL atau SUPABASE_KEY belum diatur.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_user(user_id):
    response = supabase.from_("users").select("*").eq("id", user_id).execute()
    return response.data[0] if response.data else None

def fetch_user_by_alias(alias):
    response = supabase.from_("users").select("*").eq("alias", alias).execute()
    return response.data[0] if response.data else None

def fetch_all_users():
    response = supabase.from_("users").select("id, alias, division, role").order("alias").execute()
    return response.data if response.data else []

def add_pending_user(user):
    exists = supabase.from_("pending_users").select("id").eq("id", user.id).execute()
    if exists.data:
        return None
    supabase.from_("pending_users").insert({
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }).execute()
    return True

def fetch_pending_users():
    response = supabase.from_("pending_users").select("*").order("id").execute()
    return response.data if response.data else []

def approve_user(user_id, alias, division):
    supabase.from_("pending_users").delete().eq("id", user_id).execute()
    supabase.from_("users").insert({
        "id": user_id,
        "alias": alias,
        "division": division,
        "role": "user"
    }).execute()
    return True

def remove_user(user_id):
    supabase.from_("users").delete().eq("id", user_id).execute()

def add_task(giver_id, receiver_id, description, deadline):
    supabase.from_("tasks").insert({
        "giver_id": giver_id,
        "receiver_id": receiver_id,
        "description": description,
        "deadline": deadline
    }).execute()

def fetch_tasks(user_id):
    response = supabase.from_("tasks").select(
        "id, description, deadline, giver_id, receiver_id"
    ).execute()
    return response.data if response.data else []

def fetch_my_tasks(user_id):
    response = supabase.from_("tasks").select(
        "id, description, deadline, giver_id, receiver_id"
    ).eq("receiver_id", user_id).execute()
    return response.data if response.data else []

def delete_task(task_id):
    supabase.from_("tasks").delete().eq("id", task_id).execute()
