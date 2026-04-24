"""Personal subscription commands — TG control plane part 1."""

from __future__ import annotations

from typing import Protocol

from aiogram.types import Message

from app.services.subscriptions import format_subscription_list, parse_keywords


class PersonalRepo(Protocol):
    async def upsert_user(self, tg_user_id: int, tg_username: str | None, display_name: str | None): ...
    async def create_subscription(self, user_id: int, keywords: list[str], targets: list[str]): ...
    async def list_subscriptions(self, user_id: int): ...
    async def delete_subscription(self, user_id: int, sub_id: int) -> bool: ...
    async def set_user_active(self, user_id: int, active: bool) -> None: ...
    async def set_subscription_active(self, user_id: int, sub_id: int, active: bool) -> bool: ...


_HELP = (
    "欢迎使用 TrendRadar。支持命令：\n"
    "/subscribe 关键词1, 关键词2   订阅\n"
    "/list                        查看订阅\n"
    "/unsubscribe <id>            取消订阅\n"
    "/pause  /resume              暂停 / 恢复整体推送\n"
)


async def handle_start(msg: Message, *, repo: PersonalRepo) -> None:
    u = msg.from_user
    await repo.upsert_user(u.id, u.username, u.full_name)
    await msg.answer(_HELP)


async def handle_subscribe(msg: Message, *, repo: PersonalRepo) -> None:
    u = msg.from_user
    text = (msg.text or "").partition(" ")[2].strip()
    if not text:
        await msg.answer("用法：/subscribe 关键词1, 关键词2")
        return
    try:
        kws = parse_keywords(text)
    except ValueError as e:
        await msg.answer(str(e))
        return
    await repo.upsert_user(u.id, u.username, u.full_name)
    sub = await repo.create_subscription(u.id, kws, ["telegram"])
    await msg.answer(f"✅ 已订阅 #{sub['id']}：{', '.join(kws)}")


async def handle_list(msg: Message, *, repo: PersonalRepo) -> None:
    subs = await repo.list_subscriptions(msg.from_user.id)
    await msg.answer(format_subscription_list(subs))


async def handle_unsubscribe(msg: Message, *, repo: PersonalRepo) -> None:
    arg = (msg.text or "").partition(" ")[2].strip()
    if not arg.isdigit():
        await msg.answer("用法：/unsubscribe <id>")
        return
    ok = await repo.delete_subscription(msg.from_user.id, int(arg))
    await msg.answer("✅ 已删除" if ok else "❌ 订阅不存在或不属于你")


async def handle_pause(msg: Message, *, repo: PersonalRepo) -> None:
    await repo.set_user_active(msg.from_user.id, False)
    await msg.answer("⏸ 已暂停所有推送。/resume 恢复。")


async def handle_resume(msg: Message, *, repo: PersonalRepo) -> None:
    await repo.set_user_active(msg.from_user.id, True)
    await msg.answer("▶️ 已恢复推送。")
