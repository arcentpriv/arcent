# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module containing commands for keeping notes. """

from asyncio import sleep

from userbot import BOTLOG, BOTLOG_CHATID, CMD_HELP
from userbot.events import register


@register(outgoing=True, pattern=r"^\.notes$")
async def notes_active(svd):
    """For .notes command, list all of the notes saved in a chat."""
    try:
        from userbot.modules.sql_helper.notes_sql import get_notes
    except AttributeError:
        return await svd.edit("**Executando em modo não SQL!**")
    message = "**Não há notas salvas neste bate-papo**"
    notes = get_notes(svd.chat_id)
    for note in notes:
        if message == "**Não há notas salvas neste bate-papo**":
            message = "Notas salvas neste bate-papo:\n"
        message += f"`#{note.keyword}`\n"
    await svd.edit(message)


@register(outgoing=True, pattern=r"^\.clear (\w*)")
async def remove_notes(clr):
    """For .clear command, clear note with the given name."""
    try:
        from userbot.modules.sql_helper.notes_sql import rm_note
    except AttributeError:
        return await clr.edit("**Executando em modo não SQL!**")
    notename = clr.pattern_match.group(1)
    if rm_note(clr.chat_id, notename) is False:
        return await clr.edit(f"**Não foi possível encontrar a nota:** **{notename}**")
    else:
        return await clr.edit(f"**Nota excluída com sucesso:** **{notename}**")


@register(outgoing=True, pattern=r"^\.save (\w*)")
async def add_note(fltr):
    """For .save command, saves notes in a chat."""
    try:
        from userbot.modules.sql_helper.notes_sql import add_note
    except AttributeError:
        return await fltr.edit("**Executando em modo não SQL!**")
    keyword = fltr.pattern_match.group(1)
    string = fltr.text.partition(keyword)[2]
    msg = await fltr.get_reply_message()
    msg_id = None
    if msg and msg.media and not string:
        if BOTLOG_CHATID:
            await fltr.client.send_message(
                BOTLOG_CHATID,
                f"#NOTE\nCHAT ID: {fltr.chat_id}\nPALAVRA-CHAVE: {keyword}"
                "\n\nA mensagem a seguir é salva como os dados de resposta da nota para o bate-papo, NÃO a exclua !!",
            )
            msg_o = await fltr.client.forward_messages(
                entity=BOTLOG_CHATID, messages=msg, from_peer=fltr.chat_id, silent=True
            )
            msg_id = msg_o.id
        else:
            return await fltr.edit(
                "**Salvar mídia como dados para a nota requer que BOTLOG_CHATID seja definido.**"
            )
    elif fltr.reply_to_msg_id and not string:
        rep_msg = await fltr.get_reply_message()
        string = rep_msg.text
    success = "**Nota {} com sucesso. Use** `#{}` **para obtê-la.**"
    if add_note(str(fltr.chat_id), keyword, string, msg_id) is False:
        return await fltr.edit(success.format("atualizada", keyword))
    return await fltr.edit(success.format("adicionado", keyword))


@register(
    pattern=r"^#\w*", disable_edited=True, disable_errors=True, ignore_unsafe=True
)
async def incom_note(getnt):
    """Notes logic."""
    try:
        if not (await getnt.get_sender()).bot:
            try:
                from userbot.modules.sql_helper.notes_sql import get_note
            except AttributeError:
                return
            notename = getnt.text[1:]
            note = get_note(getnt.chat_id, notename)
            message_id_to_reply = getnt.message.reply_to_msg_id
            if not message_id_to_reply:
                message_id_to_reply = None
            if note:
                if note.f_mesg_id:
                    msg_o = await getnt.client.get_messages(
                        entity=BOTLOG_CHATID, ids=int(note.f_mesg_id)
                    )
                    await getnt.client.send_message(
                        getnt.chat_id,
                        msg_o.mesage,
                        reply_to=message_id_to_reply,
                        file=msg_o.media,
                    )
                elif note.reply:
                    await getnt.client.send_message(
                        getnt.chat_id, note.reply, reply_to=message_id_to_reply
                    )
    except AttributeError:
        pass


@register(outgoing=True, pattern=r"^\.rmbotnotes (.*)")
async def kick_marie_notes(kick):
    """ For .rmbotnotes command, allows you to kick all \
        Marie(or her clones) notes from a chat. """
    bot_type = kick.pattern_match.group(1).lower()
    if bot_type not in ["marie", "rose"]:
        return await kick.edit("**Esse bot ainda não é compatível!**")
    await kick.edit("**Estarei removendo todas as notas!**")
    await sleep(3)
    resp = await kick.get_reply_message()
    filters = resp.text.split("-")[1:]
    for i in filters:
        if bot_type == "marie":
            await kick.reply("/clear %s" % (i.strip()))
        if bot_type == "rose":
            i = i.replace("**", "")
            await kick.reply("/clear %s" % (i.strip()))
        await sleep(0.3)
    await kick.respond("**Notas de bots removidas com sucesso yaay!**\n Me dê biscoitos!")
    if BOTLOG:
        await kick.client.send_message(
            BOTLOG_CHATID, "Limpei todas as notas em " + str(kick.chat_id)
        )


CMD_HELP.update(
    {
        "notes": "`#<notename>`"
        "\n**Uso:** Obtém a nota especificada."
        "\n\n>`.save <notename> <notedata>` ou responda a uma mensagem com >`.save <notename>`"
        "\n**Uso:** Salva a mensagem respondida como uma nota com o notename. "
        "(Funciona com fotos, documentos e adesivos também!)"
        "\n\n>`.notes`"
        "\n**Uso:** Obtém todas as notas salvas em um bate-papo."
        "\n\n>`.clear <notename>`"
        "\n**Uso:** Exclui a nota especificada."
        "\n\n>`.rmbotnotes <marie/rose>`"
        "\n**Uso:** Remove todas as notas de bots de administração"
        " (Suportado atualmente: Marie, Rose e seus clones.) no bate papo."
    }
)
