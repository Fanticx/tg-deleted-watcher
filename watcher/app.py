import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon import TelegramClient, events, utils
from telethon.errors import RPCError
from telethon.tl.custom import Message
from telethon.tl.types import Channel

from . import posts, report
from .config import Config
from .db import Database
from .posts import Post

CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096
BATCH = 100

log = logging.getLogger(__name__)


class Watcher:
    def __init__(self, config: Config):
        self.config = config
        config.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = Database(config.data_dir / "posts.db")
        self.client = TelegramClient(str(config.data_dir / "session"), config.api_id, config.api_hash)
        self.channels: dict[int, Channel] = {}
        self.target = None

    async def run(self) -> None:
        await self.client.start()
        await self.client.get_dialogs()
        self.target = await self.client.get_entity(self.config.target)
        await self._resolve_channels()

        ids = list(self.channels)
        self.client.add_event_handler(self._on_message, events.NewMessage(chats=ids))
        self.client.add_event_handler(self._on_message, events.MessageEdited(chats=ids))
        self.client.add_event_handler(self._on_deleted, events.MessageDeleted())

        await self.verify()
        await self._backfill()
        watch = asyncio.create_task(self._watch())
        log.info("Мониторинг запущен")
        try:
            await self.client.run_until_disconnected()
        finally:
            watch.cancel()

    async def _resolve_channels(self) -> None:
        for ref in self.config.sources:
            try:
                entity = await self.client.get_entity(ref)
            except (ValueError, RPCError) as e:
                log.error("Канал %s не найден: %s", ref, e)
                continue
            if not isinstance(entity, Channel):
                log.error("%s не канал, пропускаю", ref)
                continue
            self.channels[utils.get_peer_id(entity)] = entity
            log.info("Слежу за %s", entity.title)
        if not self.channels:
            raise SystemExit("Не найден ни один канал из SOURCE_CHANNELS")

    async def _backfill(self) -> None:
        for channel in self.channels.values():
            async for msg in self.client.iter_messages(channel, limit=self.config.backfill):
                await self._save(msg)

    async def _watch(self) -> None:
        while True:
            await asyncio.sleep(self.config.check_interval_min * 60)
            try:
                await self.verify()
                self._cleanup_media()
            except Exception:
                log.exception("Периодическая проверка не удалась")

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        await self._save(event.message)

    async def _on_deleted(self, event: events.MessageDeleted.Event) -> None:
        if event.chat_id in self.channels:
            for post_id in event.deleted_ids:
                await self._report(event.chat_id, post_id)

    async def _save(self, msg: Message) -> None:
        post = posts.from_message(msg)
        if not post:
            return
        known = self.db.get(post.channel_id, post.id)
        post.media_path = known.media_path if known and known.media_path else await self._download(msg, post)
        self.db.save(post)

    async def _download(self, msg: Message, post: Post) -> str | None:
        cfg = self.config
        if not cfg.save_media or post.media in (None, "опрос"):
            return None
        if msg.file and (msg.file.size or 0) > cfg.max_media_mb * 2**20:
            return None
        folder = cfg.data_dir / "media" / str(abs(post.channel_id))
        folder.mkdir(parents=True, exist_ok=True)
        try:
            path = await msg.download_media(file=str(folder / str(post.id)))
        except RPCError as e:
            log.warning("Не удалось скачать медиа %s/%s: %s", post.channel_id, post.id, e)
            return None
        return str(Path(path).relative_to(cfg.data_dir)) if path else None

    async def verify(self) -> None:
        since = datetime.now(timezone.utc) - timedelta(days=self.config.check_days)
        for channel_id, channel in self.channels.items():
            ids = self.db.alive_ids(channel_id, since)
            for i in range(0, len(ids), BATCH):
                batch = ids[i:i + BATCH]
                found = await self.client.get_messages(channel, ids=batch)
                for post_id, msg in zip(batch, found, strict=True):
                    if msg is None:
                        await self._report(channel_id, post_id)

    async def _report(self, channel_id: int, post_id: int) -> None:
        post = self.db.get(channel_id, post_id)
        if (post and post.deleted) or (post is None and not self.config.report_unknown):
            return
        channel = self.channels[channel_id]
        media = self._media_file(post)
        rep = report.build(
            channel.title, post, media is not None,
            datetime.now(timezone.utc), self.config.format_time, self.config.signature,
        )
        await self._send(rep, media)
        if post:
            self.db.mark_deleted(channel_id, post_id)
        log.info("Пропал пост %s/%s", channel.title, post_id)

    async def _send(self, rep: report.Report, media: Path | None) -> None:
        if media:
            caption = rep.messages(CAPTION_LIMIT)
            if len(caption) == 1:
                await self.client.send_file(self.target, media, caption=caption[0], parse_mode="html")
                return
            await self.client.send_file(self.target, media)
        for text in rep.messages(MESSAGE_LIMIT):
            await self.client.send_message(self.target, text, parse_mode="html", link_preview=False)

    def _media_file(self, post: Post | None) -> Path | None:
        if not post or not post.media_path:
            return None
        path = self.config.data_dir / post.media_path
        return path if path.exists() else None

    def _cleanup_media(self) -> None:
        before = datetime.now(timezone.utc) - timedelta(days=self.config.media_keep_days)
        for post in self.db.stale_media(before):
            (self.config.data_dir / post.media_path).unlink(missing_ok=True)
            self.db.clear_media(post.channel_id, post.id)
