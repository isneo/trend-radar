"""Feishu group binding commands — TG control plane part 2."""

from __future__ import annotations

from typing import Protocol

from aiogram.types import Message

from app.services.feishu_groups import is_valid_feishu_webhook
from app.services.subscriptions import parse_keywords


class FeishuRepo(Protocol):
    async def upsert_user(self, tg_user_id: int, tg_username: str | None, display_name: str | None): ...
    async def create_feishu_group(self, owner_user_id: int, name: str | None, webhook_url: str, keywords: list[str]): ...
    async def list_feishu_groups(self, owner_user_id: int): ...
    async def remove_feishu_group(self, owner_user_id: int, group_id: int) -> bool: ...
    async def probe_webhook(self, url: str) -> bool: ...


async def handle_add_feishu_group(msg: Message, *, repo: FeishuRepo) -> None:
    u = msg.from_user
    parts = (msg.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("用法：/add_feishu_group &lt;webhook_url&gt; 关键词1, 关键词2")
        return
    _, url, kws_raw = parts
    if not is_valid_feishu_webhook(url):
        await msg.answer("❌ 不是合法的飞书 webhook URL（必须 https://open.feishu.cn/... 或 larksuite.com）")
        return
    try:
        kws = parse_keywords(kws_raw)
    except ValueError as e:
        await msg.answer(f"❌ {e}")
        return
    if not await repo.probe_webhook(url):
        await msg.answer("❌ webhook 不可达，请确认群里机器人仍存在")
        return
    await repo.upsert_user(u.id, u.username, u.full_name)
    group = await repo.create_feishu_group(u.id, None, url, kws)
    await msg.answer(
        f"✅ 已绑定飞书群 #{group['id']}，关键词：{', '.join(kws)}。群里应已收到欢迎卡片。"
    )


async def handle_my_feishu_groups(msg: Message, *, repo: FeishuRepo) -> None:
    groups = await repo.list_feishu_groups(msg.from_user.id)
    if not groups:
        await msg.answer("你还没有绑定任何飞书群。用 /add_feishu_group 开始。")
        return
    lines = ["<b>你的飞书群：</b>"]
    for g in groups:
        status = "✅" if g["status"] == "active" else "⚠️ 已断开"
        name = g.get("name") or "(未命名)"
        lines.append(f"#{g['id']}  {name}  {status}  keywords={','.join(g['keywords'])}")
    await msg.answer("\n".join(lines))


async def handle_remove_feishu_group(msg: Message, *, repo: FeishuRepo) -> None:
    arg = (msg.text or "").partition(" ")[2].strip()
    if not arg.isdigit():
        await msg.answer("用法：/remove_feishu_group &lt;id&gt;")
        return
    ok = await repo.remove_feishu_group(msg.from_user.id, int(arg))
    await msg.answer("✅ 已解绑" if ok else "❌ 群不存在或不属于你")
