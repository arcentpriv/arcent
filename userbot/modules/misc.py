# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
# You can find misc modules, which dont fit in anything xD
""" Userbot module for other small commands. """

import io
import sys
from os import environ, execle
from random import randint
from time import sleep

from userbot import BOTLOG, BOTLOG_CHATID, CMD_HELP, bot
from userbot.events import register
from userbot.utils import time_formatter


@register(outgoing=True, pattern=r"^\.random")
async def randomise(items):
    """ For .random command, get a random item from the list of items. """
    itemo = (items.text[8:]).split()
    if len(itemo) < 2:
        return await items.edit(
            "**2 ou mais itens são necessários!**\nConfira `.help random` para mais informações."
        )
    index = randint(1, len(itemo) - 1)
    await items.edit(
        "**Consulta: **\n`" + items.text[8:] + "`\n**Resultado: **\n`" + itemo[index] + "`"
    )


@register(outgoing=True, pattern=r"^\.sleep ([0-9]+)$")
async def sleepybot(time):
    """ For .sleep command, let the userbot snooze for a few second. """
    counter = int(time.pattern_match.group(1))
    await time.edit("**Estou de mau humor e cochilando...**")
    if BOTLOG:
        str_counter = time_formatter(counter)
        await time.client.send_message(
            BOTLOG_CHATID,
            f"Você colocou o bot para dormir por {str_counter}.",
        )
    sleep(counter)
    await time.edit("**OK, estou acordado agora.**")


@register(outgoing=True, pattern=r"^\.shutdown$")
async def killthebot(event):
    """ For .shutdown command, shut the bot down."""
    await event.edit("**Desligando...**")
    if BOTLOG:
        await event.client.send_message(BOTLOG_CHATID, "#SHUTDOWN \n" "Bot desligado")
    await bot.disconnect()


@register(outgoing=True, pattern=r"^\.restart$")
async def killdabot(event):
    await event.edit("**Reiniciando...**")
    if BOTLOG:
        await event.client.send_message(
            BOTLOG_CHATID, "#RESTART \n" "Reiniciando bot..."
        )
    # Spin a new instance of bot
    args = [sys.executable, "-m", "userbot"]
    execle(sys.executable, *args, environ)


@register(outgoing=True, pattern=r"^\.readme$")
async def reedme(e):
    await e.edit(
        "Aqui estão alguns tutoriais interessantes:\n"
        "\n[Arquivo Readme do PurpleBot](https://github.com/thewhiteharlot/PurpleBot/blob/master/README.md)"
        "\n[Guia de configuração - Bot](https://www.youtube.com/watch?v=SBYjQ25ugZY&feature=emb_title&ab_channel=TUDOSEMCORTE) - Créditos: @mandaloriam"
        "\n[Guia de configuração - Google Drive](https://www.youtube.com/watch?v=Z0WFtwDMnes&ab_channel=TUDOSEMCORTE) - Créditos: @ramonazvd"
        "\n[Guia de configuração - LastFM](https://telegra.ph/Tutorial-LastFM-02-04-2)"
        "\n[Replit para gerar a String Session](https://repl.it/@kenhv/sessiongen)"
        "\n__*Após entrar no Replit, clique no botão verde para executar__"
    )


# Copyright (c) Gegham Zakaryan | 2019
@register(outgoing=True, pattern=r"^\.repeat (.*)")
async def repeat(rep):
    cnt, txt = rep.pattern_match.group(1).split(" ", 1)
    replyCount = int(cnt)
    toBeRepeated = txt

    replyText = toBeRepeated + "\n"

    for _ in range(replyCount - 1):
        replyText += toBeRepeated + "\n"

    await rep.edit(replyText)


@register(outgoing=True, pattern=r"^\.repo$")
async def repo_is_here(wannasee):
    """ For .repo command, just returns the repo URL. """
    await wannasee.edit(
        "[Clique aqui](https://github.com/thewhiteharlot/PurpleBot) para abrir o repositório do PurpleBot."
    )


@register(outgoing=True, pattern=r"^\.raw$")
async def raw(event):
    the_real_message = None
    reply_to_id = None
    if event.reply_to_msg_id:
        previous_message = await event.get_reply_message()
        the_real_message = previous_message.stringify()
        reply_to_id = event.reply_to_msg_id
    else:
        the_real_message = event.stringify()
        reply_to_id = event.message.id
    with io.BytesIO(str.encode(the_real_message)) as out_file:
        out_file.name = "raw_message_data.txt"
        try:
            await event.client.send_file(
                BOTLOG_CHATID,
                out_file,
                force_document=True,
                allow_cache=False,
                reply_to=reply_to_id,
                caption="**Aqui estão os dados da mensagem decodificada!**",
            )
            await event.edit("**Verifique o grupo de botlog para os dados da mensagem decodificada.**")
        except:
            await event.edit("**Este recurso precisa do BOTLOG_CHATID definido.**")


@register(outgoing=True, pattern=r"^\.send (.*)")
async def send(event):
    await event.edit("**Processing...**")

    if not event.is_reply:
        return await event.edit("**Reply to a message!**")

    chat = event.pattern_match.group(1)
    try:
        chat = await event.client.get_entity(chat)
    except (TypeError, ValueError):
        return await event.edit("**Invalid link provided!**")

    message = await event.get_reply_message()

    await event.client.send_message(entity=chat, message=message)
    await event.edit(f"**Sent this message to** `{chat.title}`**!**")


@register(outgoing=True, pattern=r"^\.send (.*)")
async def send(event):
    await event.edit("**Processing...**")

    if not event.is_reply:
        return await event.edit("**Reply to a message!**")

    chat = event.pattern_match.group(1)
    try:
        chat = await event.client.get_entity(chat)
    except (TypeError, ValueError):
        return await event.edit("**Invalid link provided!**")

    message = await event.get_reply_message()

    await event.client.send_message(entity=chat, message=message)
    await event.edit(f"**Sent this message to** `{chat.title}`**!**")


CMD_HELP.update(
    {
        "random": ">`.random <item1> <item2> ... <itemN>`"
        "\n**Uso:** Pegue um item aleatório da lista de itens.",
        "sleep": ">`.sleep <segundos>`"
        "\n**Uso:** Deixa seu bot adormecer por alguns segundos.",
        "shutdown": ">`.shutdown`" "\n**Uso:** Encerra o bot.",
        "repo": ">`.repo`" "\n**Uso:** Repositório GitHub deste bot",
        "readme": ">`.readme`"
        "\n**Uso:** Fornece links para configurar o userbot e seus módulos.",
        "repeat": ">`.repeat <no> <text>`"
        "\n**Uso:** Repete o texto várias vezes. Não confunda isso com spam.",
        "restart": ">`.restart`" "\n**Uso:** Reinicia o bot.",
        "raw": ">`.raw`"
        "\n**Uso:** Obtenha dados detalhados em formato JSON sobre a mensagem respondida.",
        "send": ">`.send <username/id>` (as a reply)"
        '\nUsage: Forwards the replied message to given chat without the "Forwarded from" tag.',
    }
)
