from tutubo.models import Channel, Playlist, Video
from youtube_archivist.exceptions import VideoUnavailable
from youtube_archivist.base import JsonArchivist, LOG
from queue import Queue
from threading import Thread, Event
import time
import requests


class YoutubeMonitor(Thread):
    queue = Queue()

    def __init__(self, db_name=None, required_kwords=None, blacklisted_kwords=None, min_duration=-1, logger=LOG):
        super().__init__()
        self.archive = YoutubeArchivist(db_name, required_kwords, blacklisted_kwords, min_duration)
        self.monitoring = Event()
        self.repeat_list = {}
        self.log = logger

    @property
    def db(self):
        return self.archive.db

    def sorted_entries(self):
        return sorted([e for e in self.db.values()],
                      key=lambda k: k.get("upload_ts"),
                      reverse=True)

    def bootstrap_from_url(self, url):
        if not self.archive.db:
            self.log.info(f"Bootstrapping database from: {url}")
            cache = requests.get(url).json()
            self.archive.db.update(cache)
            self.archive.db.store()

    def _index_url(self, url):
        # index url contents
        try:
            if url in self.repeat_list:
                # handle repeating checks
                if time.time() - self.repeat_list[url] < 30:
                    # exception caught below
                    # its basically an interrupt
                    raise RuntimeError("Wait before syncing again")
                self.repeat_list[url] = time.time()
            self.archive.archive(url)
        except RuntimeError:
            pass

    def run(self):
        self.monitoring.set()
        self.log.info(f"Started monitoring: {self.archive.db.name}")

        # remove any deleted videos
        try:
            self.archive.remove_unavailable()
        except Exception as e:
            self.log.exception(e)

        while self.monitoring.is_set():
            url = self.queue.get()

            # index url contents
            try:
                self._index_url(url)
            except Exception as e:
                self.log.exception(e)
                pass

            # sleep for a while
            time.sleep(120)

            # keep monitoring url
            if url in self.repeat_list:
                self.queue.put(url)  # sync this url again

    def sync(self, url):
        self.queue.put(url)

    def monitor(self, url):
        if url not in self.repeat_list:
            self.repeat_list[url] = 0
        self.sync(url)

    def stop(self):
        self.monitoring.clear()


class YoutubeArchivist(JsonArchivist):

    def archive(self, url):
        if "/channel/" in url or "/c/" in url:
            return self.archive_channel(url)
        if "/watch" in url:
            return self.archive_video(url)
        if "/playlist" in url:
            return self.archive_playlist(url)
        return self.archive_channel(url)

    def archive_video(self, url, extra_data=None):
        urls = self.video_urls
        if isinstance(url, str):
            video = Video(url)
        else:
            video = url
        if video.watch_url not in urls:
            self.log.debug(f"Archiving video: {url}")
            try:
                if any(k.lower() in video.title.lower() for k in
                       self.blacklisted_kwords):
                    return
                if any(k.lower() not in video.title.lower() for k in
                       self.required_kwords):
                    return
                if video.length < self.min_duration:
                    return
                self.log.info("Parsing video " + video.title)
                self._update_video(video, extra_data)
            except:
                # accessing the title property might cause a 404 if
                # video was removed
                raise
        del video

    def archive_playlist(self, url):
        self.log.debug(f"Archiving playlist: {url}")
        c = Playlist(url)
        try:
            meta = {"playlist": c.title}
        except:
            meta = {}
        for video in c.videos:
            self.archive_video(video, meta)

    def archive_channel(self, url):
        self.log.debug(f"Archiving channel: {url}")
        c = Channel(url)
        for video in c.videos:
            meta = {}
            self.archive_video(video, meta)

    def archive_channel_playlists(self, url):
        self.log.debug(f"Archiving  channel playlists: {url}")
        c = Channel(url)
        for pl in c.playlists:
            try:
                meta = {"playlist": pl.title}
            except:
                meta = {}
            for video in pl.videos:
                try:
                    self.archive_video(video, meta)
                except VideoUnavailable:
                    continue

    def _update_video(self, entry, extra_data=None):
        if not entry:
            return
        url = entry.watch_url
        # format data for saving
        entry = {
            "author": entry.author,
            "title": entry.title,
            "url": entry.watch_url,
            "duration": entry.length,
            "upload_ts": entry.publish_date.timestamp(),
            "tags": entry.keywords,
            'thumbnail': entry.thumbnail_url
        }
        if extra_data:
            entry.update(extra_data)
        self.db[url] = entry
        self.db.store()

    # DB interaction
    def remove_unavailable(self):
        to_remove = []
        for url, entry in self.db.items():
            vid = Video(url)
            try:
                vid_data = {
                    "videoId": vid.video_id,
                    "url": vid.watch_url,
                    "image": vid.thumbnail_url,
                    "title": vid.title
                }
            except VideoUnavailable:
                to_remove.append(url)
        for url in to_remove:
            self.db.pop(url)
            self.log.info("Removed entry: " + url)
        self.db.store()