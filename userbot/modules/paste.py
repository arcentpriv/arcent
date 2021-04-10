# Copyright (C) 2021 KenHV

from requests import post
from telethon.tl.types import MessageMediaWebPage

from userbot import CMD_HELP
from userbot.events import register


@register(outgoing=True, pattern=r"^\.paste(?:\s|$)([\s\S]*)")
async def paste(event):
    """Pastes given text to Katb.in"""
    await event.edit("**Processando...**")

    if event.is_reply:
        reply = await event.get_reply_message()
        if reply.media and not isinstance(reply.media, MessageMediaWebPage):
            return await event.edit("**Responda a algum texto!**")
        message = reply.message

    elif event.pattern_match.group(1).strip():
        message = event.pattern_match.group(1).strip()

    else:
        return await event.edit("**Veja** `.help paste`**.**")

    response = post("https://api.katb.in/api/paste", json={"content": message}).json()

    if response["msg"] == "Mensagem copiada com sucesso":
        await event.edit(
            f"**Colagem:** [Katb.in](https://katb.in/{response['paste_id']})\n"
        )
    else:
        await event.edit("**Katb.in parece esta indisponível.**")


CMD_HELP.update(
    {"paste": ">`.paste` <texto/resposta>" "\n**Uso:** Cola o texto dado no Katb.in."}
)
