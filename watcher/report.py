import html
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from .posts import Post

NOT_SAVED = "(текст не сохранён - пост вышел до запуска мониторинга)"
CHUNK = 3500


@dataclass
class Report:
    head: str
    body: str
    tail: str

    def messages(self, limit: int) -> list[str]:
        body = f"\n\n{html.escape(self.body)}" if self.body else ""
        full = f"{self.head}{body}\n\n{self.tail}"
        if len(full) <= limit:
            return [full]
        parts = [html.escape(self.body[i:i + CHUNK]) for i in range(0, len(self.body), CHUNK)]
        return [f"{self.head}\n\n{parts[0]}", *parts[1:], self.tail]


def build(
    title: str,
    post: Post | None,
    media_saved: bool,
    seen: datetime,
    format_time: Callable[[datetime], str],
    signature: str,
) -> Report:
    head = f"с тгк {html.escape(title)} пропал пост"
    seen_line = f"Удаление замечено: {format_time(seen)}"
    footer = html.escape(signature)
    if post is None:
        return Report(head, NOT_SAVED, f"{seen_line}\n\n{footer}")

    body = post.text
    if post.media and not media_saved:
        body = f"{body}\n\n[{post.media} не сохранено]".strip()
    return Report(head, body, f"Опубликован: {format_time(post.date)}\n{seen_line}\n\n{footer}")
