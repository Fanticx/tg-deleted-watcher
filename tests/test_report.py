from datetime import datetime, timedelta, timezone

from watcher.posts import Post
from watcher.report import build

SIGNATURE = "это автоматическое сообщение бота @my_channel"
SEEN = datetime(2026, 11, 21, 17, 52, 44, tzinfo=timezone.utc)


def msk(moment: datetime) -> str:
    return f"{moment.astimezone(timezone(timedelta(hours=3))):%d.%m.%Y %H:%M:%S} МСК"


def make_post(text: str, media: str | None = None) -> Post:
    return Post(-1001, 42, datetime(2026, 11, 3, 16, 36, 11, tzinfo=timezone.utc), text, media)


def make_report(title: str, post: Post, media_saved: bool = False):
    return build(title, post, media_saved, SEEN, msk, SIGNATURE)


def test_format():
    rep = make_report("Channel", make_post("Post text"))

    assert rep.messages(4096) == [
        "с тгк Channel пропал пост\n\n"
        "Post text\n\n"
        "Опубликован: 03.11.2026 19:36:11 МСК\n"
        "Удаление замечено: 21.11.2026 20:52:44 МСК\n\n"
        "это автоматическое сообщение бота @my_channel"
    ]


def test_text_is_escaped_and_lost_media_noted():
    text = make_report("A&B", make_post("<b>hi</b>", media="фото")).messages(4096)[0]

    assert "A&amp;B" in text
    assert "&lt;b&gt;hi&lt;/b&gt;" in text
    assert "[фото не сохранено]" in text


def test_long_post_is_split():
    messages = make_report("T", make_post("x" * 9000), media_saved=True).messages(4096)

    assert len(messages) == 4
    assert all(len(m) <= 4096 for m in messages)
    assert messages[-1].startswith("Опубликован:")
