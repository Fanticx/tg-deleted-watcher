from dataclasses import dataclass
from datetime import datetime

from telethon.tl.custom import Message
from telethon.tl.types import MessageMediaWebPage

MEDIA_KINDS = (
    ("photo", "фото"),
    ("gif", "GIF"),
    ("video_note", "кружок"),
    ("video", "видео"),
    ("voice", "голосовое"),
    ("audio", "аудио"),
    ("sticker", "стикер"),
    ("poll", "опрос"),
    ("document", "файл"),
)


@dataclass
class Post:
    channel_id: int
    id: int
    date: datetime
    text: str
    media: str | None = None
    media_path: str | None = None
    deleted: bool = False


def media_kind(msg: Message) -> str | None:
    if not msg.media or isinstance(msg.media, MessageMediaWebPage):
        return None
    return next((name for attr, name in MEDIA_KINDS if getattr(msg, attr)), "медиа")


def from_message(msg: Message) -> Post | None:
    if msg.action:
        return None
    text = msg.message or ""
    if msg.poll:
        poll = msg.poll.poll
        options = "\n".join(f"• {answer.text.text}" for answer in poll.answers)
        text = f"{text}\n\n📊 {poll.question.text}\n{options}".strip()
    media = media_kind(msg)
    if not text and not media:
        return None
    return Post(msg.chat_id, msg.id, msg.date, text, media)
