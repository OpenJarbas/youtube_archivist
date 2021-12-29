import internetarchive as ia
import requests

from youtube_archivist.base import JsonArchivist, LOG


class IAArchivist(JsonArchivist):
    VALID_FORMATS = ['MPEG2', "Ogg Video", "512Kb MPEG4", 'h.264']

    def archive(self, url):
        try:
            self.archive_item(url)
        except:
            self.archive_collection(url)

    def archive_item(self, item_id):
        item = ia.get_item(item_id)
        meta = requests.get(item.urls.metadata).json()
        tags = []
        if meta["metadata"].get('subject'):
            if isinstance(meta["metadata"]["subject"], str):
                tags += meta["metadata"]["subject"].split(";")
            if isinstance(meta["metadata"]["subject"], list):
                tags += meta["metadata"]["subject"]
        title = meta["metadata"]["title"]
        if isinstance(title, list):
            title = title[0]
        movie = {
            "collection": meta["metadata"]["collection"],
            "tags": tags,
            "streams": [],
            "title": title,
            "duration": meta["metadata"].get('runtime'),
            "images": []
        }
        for f in meta["files"]:
            if f["format"] in self.VALID_FORMATS:
                stream = item.urls.download + "/" + f["name"]
                movie["streams"].append(stream)
            if f["format"] in ["PNG"]:
                movie["images"] += [item.urls.download + "/" + f["name"]]
        if not movie["streams"]:
            return
        if any(k.lower() in movie["title"].lower() for k in
               self.blacklisted_kwords):
            return
        if any(k.lower() not in movie["title"].lower() for k in
               self.required_kwords):
            return
        LOG.info("Parsing video " + movie["title"])
        self.db[item_id] = movie
        self.db.store()

    def archive_collection(self, collection_name):
        session = ia.ArchiveSession()
        entries = list(ia.Search(session, 'collection:' + collection_name))
        for idx, entry in enumerate(entries):
            item_id = entry['identifier']
            if item_id not in self.db:
                self.archive_item(item_id)
