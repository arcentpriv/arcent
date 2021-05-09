# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module for kanging stickers or making new ones. Thanks @rupansh"""

import io
import math
import random
import urllib.request
from os import remove

import requests
from bs4 import BeautifulSoup as bs
from PIL import Image
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import (
    DocumentAttributeFilename,
    DocumentAttributeSticker,
    InputStickerSetID,
    MessageMediaPhoto,
)

from userbot import CMD_HELP, bot
from userbot.events import register

KANGING_STR = [
    "Usando alquimia para clonar esse sticker...",
    "Pegando isso aqui emprestado...",
    "Convidando esse sticker pro meu pack...",
    "Hey, lindo sticker!\nSe importa se eu roubar?!..",
    "hehe achado não é roubado\nquem perdeu foi relaxado.",
    "Ay olha aquilo ali (☉｡☉)!→\nEnquanto eu pego isso aqui...",
    "Enviando sticker para meu banco de dados.",
    "Simsalabim, passe esse sticker para mim.",
    "Sticker capturado com sucesso...",
    "Sr. RoubaSticker roubando seu sticker... ",
    "Estamos a `0` dias sem roubar stickers, o recorde atual é: `0` dias."
]


@register(outgoing=True, pattern=r"^\.kang")
async def kang(args):
    """For .kang command, kangs stickers or creates new ones."""
    user = await bot.get_me()
    if not user.username:
        user.username = user.first_name
    message = await args.get_reply_message()
    photo = None
    emojibypass = False
    is_anim = False
    emoji = None

    if message and message.media:
        if isinstance(message.media, MessageMediaPhoto):
            await args.edit(f"**{random.choice(KANGING_STR)}**")
            photo = io.BytesIO()
            photo = await bot.download_media(message.photo, photo)
        elif "image" in message.media.document.mime_type.split("/"):
            await args.edit(f"**{random.choice(KANGING_STR)}**")
            photo = io.BytesIO()
            await bot.download_file(message.media.document, photo)
            if (
                DocumentAttributeFilename(file_name="sticker.webp")
                in message.media.document.attributes
            ):
                emoji = message.media.document.attributes[1].alt
                if emoji != "":
                    emojibypass = True
        elif "tgsticker" in message.media.document.mime_type:
            await args.edit(f"**{random.choice(KANGING_STR)}**")
            await bot.download_file(message.media.document, "AnimatedSticker.tgs")

            attributes = message.media.document.attributes
            for attribute in attributes:
                if isinstance(attribute, DocumentAttributeSticker):
                    emoji = attribute.alt

            emojibypass = True
            is_anim = True
            photo = 1
        else:
            return await args.edit("**Arquivo não suportado!**")
    else:
        return await args.edit("**Não posso roubar isso...**")

    if photo:
        splat = args.text.split()
        if not emojibypass:
            emoji = "🤔"
        pack = 1
        if len(splat) == 3:
            pack = splat[2]  # User sent both
            emoji = splat[1]
        elif len(splat) == 2:
            if splat[1].isnumeric():
                # User wants to push into different pack, but is okay with
                # thonk as emote.
                pack = int(splat[1])
            else:
                # User sent just custom emote, wants to push to default
                # pack
                emoji = splat[1]

        packname = f"a{user.id}_by_{user.username}_{pack}"
        packnick = f"@{user.username} kang library Book.{pack}"
        cmd = "/newpack"
        file = io.BytesIO()

        if not is_anim:
            image = await resize_photo(photo)
            file.name = "sticker.png"
            image.save(file, "PNG")
        else:
            packname += "_anim"
            packnick += " (Animated)"
            cmd = "/newanimated"

        response = urllib.request.urlopen(
            urllib.request.Request(f"http://t.me/addstickers/{packname}")
        )
        htmlstr = response.read().decode("utf8").split("\n")

        if (
            "  A <strong>Telegram</strong> user has created the <strong>Sticker&nbsp;Set</strong>."
            not in htmlstr
        ):
            async with bot.conversation("Stickers") as conv:
                await conv.send_message("/addsticker")
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.send_message(packname)
                x = await conv.get_response()
                while "120" in x.text:
                    pack += 1
                    packname = f"a{user.id}_by_{user.username}_{pack}"
                    packnick = f"@{user.username} kang library Book.{pack}"
                    await args.edit(
                        "**Mudando para o Pacote "
                        + str(pack)
                        + " devido a espaço insuficiente...**"
                    )
                    await conv.send_message(packname)
                    x = await conv.get_response()
                    if x.text == "Invalid pack selected.":
                        await conv.send_message(cmd)
                        await conv.get_response()
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.send_message(packnick)
                        await conv.get_response()
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        if is_anim:
                            await conv.send_file("AnimatedSticker.tgs")
                            remove("AnimatedSticker.tgs")
                        else:
                            file.seek(0)
                            await conv.send_file(file, force_document=True)
                        await conv.get_response()
                        await conv.send_message(emoji)
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.get_response()
                        await conv.send_message("/publish")
                        if is_anim:
                            await conv.get_response()
                            await conv.send_message(f"<{packnick}>")
                        # Ensure user doesn't get spamming notifications
                        await conv.get_response()
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.send_message("/skip")
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.get_response()
                        await conv.send_message(packname)
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        await conv.get_response()
                        # Ensure user doesn't get spamming notifications
                        await bot.send_read_acknowledge(conv.chat_id)
                        return await args.edit(
                            "**Sticker adicionado em um pacote diferente!**"
                            "\nEste pacote foi criado recentemente."
                            f"\nSeu pacote pode ser encontrado [aqui](t.me/addstickers/{packname})"
                        )
                if is_anim:
                    await conv.send_file("AnimatedSticker.tgs")
                    remove("AnimatedSticker.tgs")
                else:
                    file.seek(0)
                    await conv.send_file(file, force_document=True)
                rsp = await conv.get_response()
                if "Sorry, the file type is invalid." in rsp.text:
                    return await args.edit(
                        "**Falha ao adicionar sticker, use** @Stickers **bot para adicionar o sticker manualmente.**"
                    )
                await conv.send_message(emoji)
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                await conv.send_message("/done")
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
        else:
            await args.edit("**Preparando um novo pacote...**")
            async with bot.conversation("Stickers") as conv:
                await conv.send_message(cmd)
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.send_message(packnick)
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                if is_anim:
                    await conv.send_file("AnimatedSticker.tgs")
                    remove("AnimatedSticker.tgs")
                else:
                    file.seek(0)
                    await conv.send_file(file, force_document=True)
                rsp = await conv.get_response()
                if "Sorry, the file type is invalid." in rsp.text:
                    return await args.edit(
                        "**Falha ao adicionar sticker, use** @Stickers **bot para adicionar o sticker manualmente.**"
                    )
                await conv.send_message(emoji)
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                await conv.send_message("/publish")
                if is_anim:
                    await conv.get_response()
                    await conv.send_message(f"<{packnick}>")
                # Ensure user doesn't get spamming notifications
                await conv.get_response()
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.send_message("/skip")
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                await conv.send_message(packname)
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)
                await conv.get_response()
                # Ensure user doesn't get spamming notifications
                await bot.send_read_acknowledge(conv.chat_id)

        await args.edit(
            "**Sticker roubado com sucesso!**"
            f"\nPacote pode ser achado [aqui](t.me/addstickers/{packname})",
            parse_mode="md",
        )


async def resize_photo(photo):
    """Resize the given photo to 512x512"""
    image = Image.open(photo)
    if (image.width and image.height) < 512:
        size1 = image.width
        size2 = image.height
        if size1 > size2:
            scale = 512 / size1
            size1new = 512
            size2new = size2 * scale
        else:
            scale = 512 / size2
            size1new = size1 * scale
            size2new = 512
        size1new = math.floor(size1new)
        size2new = math.floor(size2new)
        sizenew = (size1new, size2new)
        image = image.resize(sizenew)
    else:
        maxsize = (512, 512)
        image.thumbnail(maxsize)

    return image


@register(outgoing=True, pattern=r"^\.stkrinfo$")
async def get_pack_info(event):
    if not event.is_reply:
        return await event.edit("**Não consigo obter informações do nada, posso?**")

    rep_msg = await event.get_reply_message()
    if not rep_msg.document:
        return await event.edit("**Responda a um sticker para obter os detalhes do pacote.**")

    try:
        stickerset_attr = rep_msg.document.attributes[1]
        await event.edit("**Buscando detalhes do pacote de stickers, aguarde...**")
    except BaseException:
        return await event.edit("**Este não é um sticker. Responda a um sticker.**")

    if not isinstance(stickerset_attr, DocumentAttributeSticker):
        return await event.edit("**Isto não é um sticker. Responda a um sticker.**")

    get_stickerset = await bot(
        GetStickerSetRequest(
            InputStickerSetID(
                id=stickerset_attr.stickerset.id,
                access_hash=stickerset_attr.stickerset.access_hash,
            )
        )
    )
    pack_emojis = []
    for document_sticker in get_stickerset.packs:
        if document_sticker.emoticon not in pack_emojis:
            pack_emojis.append(document_sticker.emoticon)

    OUTPUT = (
        f"**Título do sticker:** `{get_stickerset.set.title}\n`"
        f"**Nome curto do sticker:** `{get_stickerset.set.short_name}`\n"
        f"**Oficial:** `{get_stickerset.set.official}`\n"
        f"**Arquivado:** `{get_stickerset.set.archived}`\n"
        f"**Stickers no pacote:** `{len(get_stickerset.packs)}`\n"
        f"**Emojis no pacote:**\n{' '.join(pack_emojis)}"
    )

    await event.edit(OUTPUT)


@register(outgoing=True, pattern=r"^\.getsticker$")
async def sticker_to_png(sticker):
    if not sticker.is_reply:
        await sticker.edit("**Responda a um sticker!**")
        return False

    img = await sticker.get_reply_message()
    if not img.document:
        await sticker.edit("**Responda a um sticker!**")
        return False

    try:
        img.document.attributes[1]
    except Exception:
        await sticker.edit("**Responda a um sticker!**")
        return

    await sticker.delete()
    with io.BytesIO() as image:
        await sticker.client.download_media(img, image)
        image.name = "sticker.png"
        image.seek(0)
        try:
            await img.reply(file=image, force_document=True)
        except Exception:
            await sticker.edit("**Erro: Não é possível enviar o arquivo.**")
    return


@register(outgoing=True, pattern=r"^\.findsticker (.*)")
async def cb_sticker(event):
    query = event.pattern_match.group(1)
    if not query:
        return await event.edit("**Passe uma consulta para pesquisar!**")
    await event.edit("**Procurando pacote de stickers...**")
    text = requests.get("https://combot.org/telegram/stickers?q=" + query).text
    soup = bs(text, "lxml")
    results = soup.find_all("div", {"class": "sticker-pack__header"})
    if not results:
        return await event.edit("**Nenhum resultado encontrado.**")
    reply = f"**Consulta de pesquisa:**\n {query}\n\n**Resultados:**\n"
    for pack in results:
        if pack.button:
            packtitle = (pack.find("div", "sticker-pack__title")).get_text()
            packlink = (pack.a).get("href")
            reply += f"- [{packtitle}]({packlink})\n\n"
    await event.edit(reply)


CMD_HELP.update(
    {
        "stickers": ">`.kang <emoji>[opcional] <número do pacote>[opcional]`"
        "\n**Uso:** Adiciona stickers ou imagem ao seu pacote de stickers."
        "\n\n>`.stkrinfo`"
        "\n**Uso:** Obtém informações sobre o pacote de stickers."
        "\n\n>`.getsticker`"
        "\n**Uso:** Responda a um sticker para obter o arquivo 'PNG' do sticker."
        "\n\n>`.findsticker <nome do usuário ou pacote>`"
        "\n**Uso:** Procura por pacotes de stickers."
    }
)
