# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
""" Userbot module containing userid, chatid and log commands"""

from asyncio import sleep

from userbot import BOTLOG, BOTLOG_CHATID, CMD_HELP, bot
from userbot.events import register
from userbot.modules.admin import get_user_from_event


@register(outgoing=True, pattern=r"^\.userid$")
async def useridgetter(target):
    """For .userid command, returns the ID of the target user."""
    message = await target.get_reply_message()
    if message:
        if not message.forward:
            user_id = message.sender.id
            if message.sender.username:
                name = "@" + message.sender.username
            else:
                name = "**" + message.sender.first_name + "**"
        else:
            user_id = message.forward.sender.id
            if message.forward.sender.username:
                name = "@" + message.forward.sender.username
            else:
                name = "*" + message.forward.sender.first_name + "*"
        await target.edit(f"**Nome:** {name} \n**ID:** `{user_id}`")


@register(outgoing=True, pattern=r"^\.link(?: |$)(.*)")
async def permalink(mention):
    """For .link command, generates a link to the user's PM with a custom text."""
    user, custom = await get_user_from_event(mention)
    if not user:
        return
    if custom:
        await mention.edit(f"[{custom}](tg://user?id={user.id})")
    else:
        tag = (
            user.first_name.replace("\u2060", "") if user.first_name else user.username
        )
        await mention.edit(f"[{tag}](tg://user?id={user.id})")


@register(outgoing=True, pattern=r"^\.chatid$")
async def chatidgetter(chat):
    """For .chatid, returns the ID of the chat you are in at that moment."""
    await chat.edit("Chat ID: `" + str(chat.chat_id) + "`")


@register(outgoing=True, pattern=r"^\.log(?: |$)([\s\S]*)")
async def log(log_text):
    """For .log command, forwards a message or the command argument to the bot logs group"""
    if BOTLOG:
        if log_text.reply_to_msg_id:
            reply_msg = await log_text.get_reply_message()
            await reply_msg.forward_to(BOTLOG_CHATID)
        elif log_text.pattern_match.group(1):
            user = f"#LOG / Chat ID: {log_text.chat_id}\n\n"
            textx = user + log_text.pattern_match.group(1)
            await bot.send_message(BOTLOG_CHATID, textx)
        else:
            return await log_text.edit("**O que devo registrar?**")
        await log_text.edit("**Registrado com sucesso!**")
    else:
        await log_text.edit("**Este recurso requer que o registro esteja ativado!**")
    await sleep(2)
    await log_text.delete()


@register(outgoing=True, pattern=r"^\.kickme$")
async def kickme(leave):
    """Basically it's .kickme command"""
    await leave.edit("**Nope, no, no, I go away**")
    await leave.client.kick_participant(leave.chat_id, "me")


@register(outgoing=True, pattern=r"^\.unmutechat$")
async def unmute_chat(unm_e):
    """For .unmutechat command, unmute a muted chat."""
    try:
        from userbot.modules.sql_helper.keep_read_sql import unkread
    except AttributeError:
        return await unm_e.edit("**Executando em modo não SQL!**")
    unkread(str(unm_e.chat_id))
    await unm_e.edit("**Chat desmutado com sucesso!**")
    await sleep(2)
    await unm_e.delete()


@register(outgoing=True, pattern=r"^\.mutechat$")
async def mute_chat(mute_e):
    """For .mutechat command, mute any chat."""
    try:
        from userbot.modules.sql_helper.keep_read_sql import kread
    except AttributeError:
        return await mute_e.edit("**Executando em modo não SQL!**")
    await mute_e.edit(str(mute_e.chat_id))
    kread(str(mute_e.chat_id))
    await mute_e.edit("**Shhh! Este chat será silenciado!**")
    await sleep(2)
    await mute_e.delete()
    if BOTLOG:
        await mute_e.client.send_message(
            BOTLOG_CHATID, str(mute_e.chat_id) + " foi silenciado."
        )


@register(incoming=True, disable_errors=True)
async def keep_read(message):
    """The mute logic."""
    try:
        from userbot.modules.sql_helper.keep_read_sql import is_kread
    except AttributeError:
        return
    kread = is_kread()
    if kread:
        for i in kread:
            if i.groupid == str(message.chat_id):
                await message.client.send_read_acknowledge(message.chat_id)


@register(outgoing=True, pattern=r"^s/")
async def sedNinja(event):
    """For regex-ninja module, auto delete command starting with s/"""
    try:
        from userbot.modules.sql_helper.globals import gvarstatus
    except AttributeError:
        return await event.edit("**Executando em modo não SQL!**")
    if gvarstatus("regexNinja"):
        await event.delete()


@register(outgoing=True, pattern=r"^\.regexninja (on|off)$")
async def sedNinjaToggle(event):
    """Enables or disables the regex ninja module."""
    if event.pattern_match.group(1) == "on":
        try:
            from userbot.modules.sql_helper.globals import addgvar
        except AttributeError:
            return await event.edit("**Executando em modo não SQL!**")
        addgvar("regexNinja", True)
        await event.edit("**Modo ninja ativado com sucesso para Regexbot.**")
        await sleep(1)
        await event.delete()
    elif event.pattern_match.group(1) == "off":
        try:
            from userbot.modules.sql_helper.globals import delgvar
        except AttributeError:
            return await event.edit("**Executando em modo não SQL!**")
        delgvar("regexNinja")
        await event.edit("**Modo ninja desativado com sucesso para Regexbot.**")
        await sleep(1)
        await event.delete()


CMD_HELP.update(
    {
        "chat": ">`.chatid`"
        "\n**Uso:** Busca o ID do bate-papo atual"
        "\n\n>`.userid`"
        "\n**Uso:** Busca o ID do usuário em resposta, se for uma mensagem encaminhada, encontra o ID da fonte."
        "\n\n>`.log`"
        "\n**Uso:** Encaminha a mensagem que você respondeu em seu grupo de logs de bot."
        "\n\n>`.kickme`"
        "\n**Uso:** Sair do grupo."
        "\n\n>`.unmutechat`"
        "\n**Uso:** Reativa as notificações de um bate-papo."
        "\n\n>`.mutechat`"
        "\n**Uso:** Permite silenciar qualquer bate-papo."
        "\n\n>`.link <nome de usuário/userid> : <texto opcional>` (ou) responder a mensagem de alguém com"
        "\n\n>`.link <texto opcional>`"
        "\n**Uso:** Gere um link permanente para o perfil do usuário com texto personalizado opcional."
        "\n\n>`.regexninja on/off`"
        "\n**Uso:** Ativa/desativa globalmente o módulo regex ninja."
        "\nO módulo Regex Ninja ajuda a excluir as mensagens de ativação do bot regex."
    }
)
