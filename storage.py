import json
import os
import time

# Se conservan los ids vistos como mucho 30 dias para no crecer sin fin
SEEN_TTL_SECONDS = 30 * 24 * 3600


class Storage:
    def __init__(self, path):
        self.path = path
        self.data = {"chats": [], "searches": [], "seen": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self.data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                self.data = {"chats": [], "searches": [], "seen": {}}

    def save(self):
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ---- chats ----
    def add_chat(self, chat_id):
        if chat_id not in self.data["chats"]:
            self.data["chats"].append(chat_id)
            self.save()

    def get_chats(self):
        return list(self.data["chats"])

    # ---- ofertas ya notificadas ----
    def is_seen(self, job_id):
        return job_id in self.data["seen"]

    def mark_seen(self, job_id):
        self.data["seen"][job_id] = time.time()
        cutoff = time.time() - SEEN_TTL_SECONDS
        stale = [k for k, v in self.data["seen"].items() if v < cutoff]
        for k in stale:
            del self.data["seen"][k]
        self.save()

    # ---- busquedas ----
    def add_search(self, search):
        for existing in self.data["searches"]:
            if (
                existing.get("keywords") == search.get("keywords")
                and existing.get("location") == search.get("location")
                and existing.get("remote") == search.get("remote")
            ):
                return False
        self.data["searches"].append(search)
        self.save()
        return True

    def remove_search(self, index):
        if 0 <= index < len(self.data["searches"]):
            removed = self.data["searches"].pop(index)
            self.save()
            return removed
        return None

    def get_searches(self):
        return list(self.data["searches"])
