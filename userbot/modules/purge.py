# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module for purging unneeded messages(usually spam or ot). """

from asyncio import sleep

from telethon.errors import rpcbaseerrors

from userbot import CMD_HELP
from userbot.events import register


@register(outgoing=True, pattern=r"^\.purge$")
async def fastpurger(purg):
    """For .purge command, purge all messages starting from the reply."""
    chat = await purg.get_input_chat()
    msgs = []
    itermsg = purg.client.iter_messages(chat, min_id=purg.reply_to_msg_id)
    count = 0

    if purg.reply_to_msg_id is not None:
        async for msg in itermsg:
            msgs.append(msg)
            count += 1
            msgs.append(purg.reply_to_msg_id)
            if len(msgs) == 100:
                await purg.client.delete_messages(chat, msgs)
                msgs = []
    else:
        return await purg.edit("**I need a mesasge to start purging from.**")

    if msgs:
        await purg.client.delete_messages(chat, msgs)
    done = await purg.client.send_message(
        purg.chat_id, "**Fast purge complete!**" f"\nPurged {str(count)} messages"
    )
    await sleep(2)
    await done.delete()


@register(outgoing=True, pattern=r"^\.purgeme")
async def purgeme(delme):
    """For .purgeme, delete x count of your latest message."""
    message = delme.text
    count = int(message[9:])
    i = 1

    async for message in delme.client.iter_messages(delme.chat_id, from_user="me"):
        if i > count + 1:
            break
        i += 1
        await message.delete()

    smsg = await delme.client.send_message(
        delme.chat_id,
        "**Limpeza completa!** Limpadas " + str(count) + " mensagens.",
    )
    await sleep(2)
    i = 1
    await smsg.delete()


@register(outgoing=True, pattern=r"^\.del$")
async def delete_it(delme):
    """For .del command, delete the replied message."""
    msg_src = await delme.get_reply_message()
    if delme.reply_to_msg_id:
        try:
            await msg_src.delete()
            await delme.delete()
        except rpcbaseerrors.BadRequestError:
            await delme.edit("**Bem, eu não posso deletar uma mensagem.**")


@register(outgoing=True, pattern=r"^\.edit")
async def editer(edit):
    """For .editme command, edit your last message."""
    message = edit.text
    chat = await edit.get_input_chat()
    self_id = await edit.client.get_peer_id("me")
    string = str(message[6:])
    i = 1
    async for message in edit.client.iter_messages(chat, self_id):
        if i == 2:
            await message.edit(string)
            await edit.delete()
            break
        i += 1


@register(outgoing=True, pattern=r"^\.sd")
async def selfdestruct(destroy):
    """For .sd command, make seflf-destructable messages."""
    message = destroy.text
    counter = int(message[4:6])
    text = str(destroy.text[6:])
    await destroy.edit(text)
    await sleep(counter)
    await destroy.delete()


CMD_HELP.update(
    {
        "purge": ">`.purge`" "\n**Uso:** Limpa todas as mensagens a partir da resposta.",
        "purgeme": ">`.purgeme <x>`"
        "\n**Uso:** Exclui x quantidade de suas mensagens mais recentes.",
        "del": ">`.del`" "\n**Uso:** Exclui a mensagem que você respondeu.",
        "edit": ">`.edit <newmessage>`"
        "\n**Uso:** Substitua sua última mensagem por <nova mensagem>.",
        "sd": ">`.sd <x> <mensagem>`"
        "\n**Uso:** Cria uma mensagem que se autodestrói em x segundos."
        "\n<x> deve ser um valor de dois dígitos, o terceiro dígito e outros dígitos serão considerados como <mensagem>.",
    }
)
