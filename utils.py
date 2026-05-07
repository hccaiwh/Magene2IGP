import time
import os
import json

SYNC_RECORD_FILE = "sync_record.json"

def make_save_dir(dir_name="fit_files"):
    os.makedirs(dir_name, exist_ok=True)
    return dir_name

def safe_sleep(sec):
    time.sleep(sec)

def init_sync_record():
    if not os.path.exists(SYNC_RECORD_FILE):
        with open(SYNC_RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump({"synced_ids": []}, f, ensure_ascii=False, indent=2)

def get_synced_ids():
    init_sync_record()
    with open(SYNC_RECORD_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("synced_ids", []))

def save_synced_id(act_id):
    init_sync_record()
    with open(SYNC_RECORD_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if act_id not in data["synced_ids"]:
        data["synced_ids"].append(act_id)
        with open(SYNC_RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
