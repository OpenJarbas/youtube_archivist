from logging import getLogger
from json_database import JsonStorageXDG


LOG = getLogger("youtube_archivist")
LOG.setLevel("DEBUG")


class JsonArchivist:
    def __init__(self, db_name=None, required_kwords=None, blacklisted_kwords=None):
        self.required_kwords = required_kwords or []
        self.blacklisted_kwords = blacklisted_kwords or []
        self.db = JsonStorageXDG(db_name, subfolder="youtube_archivist")

    @property
    def video_urls(self):
        return list(self.db.keys())

    def archive(self, url):
        raise NotImplementedError

    def sorted_entries(self):
        return sorted([e for e in self.db.values()],
                      key=lambda k: k.get("upload_ts"),
                      reverse=True)

    # DB interaction
    def remove_unavailable(self):
        pass

    def remove_keyword(self, kwords=None):
        kwords = kwords or self.blacklisted_kwords
        bad_urls = []
        for url, entry in self.db.items():
            name = entry["title"]
            if any([k.lower() in name.lower() for k in kwords]):
                bad_urls.append(url)
        for url in bad_urls:
            self.db.pop(url)
            LOG.info("Removed entry: " + url)
        self.db.store()

    def remove_missing(self, kwords):
        bad_urls = []
        for url, entry in self.db.items():
            if any([not entry.get(k) for k in kwords]):
                bad_urls.append(url)
        for url in bad_urls:
            self.db.pop(url)
            LOG.info("Removed entry: " + url)
        self.db.store()

    def remove_below_duration(self, minutes=30):
        bad_urls = []
        for url, entry in self.db.items():
            dur = entry.get("duration") or 0
            if dur <= minutes * 60:
                bad_urls.append(url)
        for url in bad_urls:
            self.db.pop(url)
            LOG.info("Removed entry: " + url)
        self.db.store()
