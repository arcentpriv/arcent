# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module which contains afk-related commands """

from asyncio import sleep
from random import choice, randint

from telethon.events import StopPropagation

from userbot import (  # noqa
    AFKREASON,
    BOTLOG,
    BOTLOG_CHATID,
    CMD_HELP,
    COUNT_MSG,
    ISAFK,
    PM_AUTO_BAN,
    USERS,
)
from userbot.events import register

# ========================= CONSTANTS ============================
AFKSTR = [
    "Agora estou ocupado. Por favor, fale em uma bolsa e quando eu voltar você pode apenas me dar a bolsa!",
    "Estou fora agora. Se precisar de alguma coisa, deixe mensagem após o beep:\n`beeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeep`!",
    "Você me errou, da próxima vez mire melhor.",
    "Volto em alguns minutos e se não ..,\nespere mais um pouco.",
    "Não estou aqui agora, então provavelmente estou em outro lugar.",
    "Sei que quer falar comigo, mas estou ocupado salvando o mundo agora.",
    "Às vezes, vale a pena esperar pelas melhores coisas da vida…\nJá volto.",
    "Já volto,\nmas se não voltar agora,\nvolto mais tarde.",
    "Se você ainda não percebeu,\nnão estou aqui.",
    "Olá, seja bem-vindo à minha mensagem de ausência, como posso ignorá-lo hoje?",
    "Estou mais longe que 7 mares e 7 países,\n7 águas e 7 continentes,\n7 montanhas e 7 colinas,\n7 planícies e 7 montes,\n7 piscinas e 7 lagos,\n7 nascentes e 7 prados,\n7 cidades e 7 bairros,\n7 quadras e 7 casas...\n\nOnde nem mesmo suas mensagens podem me alcançar!",
    "Estou ausente no momento, mas se você gritar alto o suficiente na tela, talvez eu possa ouvir você.",
    "Eu fui pra lá\n---->",
    "Eu fui pra lá\n<----",
    "Por favor, deixe uma mensagem e me faça sentir ainda mais importante do que já sou.",
    "Eu não estou aqui então pare de escrever para mim,\nou então você se verá com uma tela cheia de suas próprias mensagens.",
    "Se eu estivesse aqui,\nEu te diria onde estou.\n\nMas eu não estou,\nentão me pergunte quando eu voltar...",
    "Estou ausente!\nNão sei quando voltarei!\nEspero que daqui a alguns minutos!",
    "Não estou disponível agora, por favor, deixe seu nome, número e endereço e eu irei persegui-lo mais tarde. ",
    "Desculpe, eu não estou aqui agora.\nSinta-se à vontade para falar com meu userbot pelo tempo que desejar.\nEu respondo mais tarde.",
    "Aposto que você estava esperando uma mensagem de ausência, mas era eu! Dio!",
    "A vida é tão curta, há tantas coisas para fazer ...\nEstou ausente fazendo uma delas ..",
    "Eu não estou aqui agora ...\nmas se estivesse...\n\nisso não seria incrível?",
]
# =================================================================


@register(incoming=True, disable_edited=True)
async def mention_afk(mention):
    """This function takes care of notifying the people who mention you that you are AFK."""
    global COUNT_MSG
    global USERS
    global ISAFK
    if mention.message.mentioned and ISAFK:
        is_bot = False
        if sender := await mention.get_sender():
            is_bot = sender.bot
        if not is_bot and mention.sender_id not in USERS:
            if AFKREASON:
                await mention.reply("Estou ausente agora." f"\nMotivo **{AFKREASON}**")
            else:
                await mention.reply(str(choice(AFKSTR)))
            USERS.update({mention.sender_id: 1})
        else:
            if not is_bot and sender:
                if USERS[mention.sender_id] % randint(2, 4) == 0:
                    if AFKREASON:
                        await mention.reply(
                            f"Ainda estou ausente.\
                                \nMotivo: **{AFKREASON}**"
                        )
                    else:
                        await mention.reply(str(choice(AFKSTR)))
                USERS[mention.sender_id] = USERS[mention.sender_id] + 1
        COUNT_MSG = COUNT_MSG + 1


@register(incoming=True, disable_errors=True)
async def afk_on_pm(sender):
    """Function which informs people that you are AFK in PM"""
    global ISAFK
    global USERS
    global COUNT_MSG
    if (
        sender.is_private
        and sender.sender_id != 777000
        and not (await sender.get_sender()).bot
    ):
        if PM_AUTO_BAN:
            try:
                from userbot.modules.sql_helper.pm_permit_sql import is_approved

                apprv = is_approved(sender.sender_id)
            except AttributeError:
                apprv = True
        else:
            apprv = True
        if apprv and ISAFK:
            if sender.sender_id not in USERS:
                if AFKREASON:
                    await sender.reply(
                        f"Estou ausente agora.\
                    \nMotivo: **{AFKREASON}**"
                    )
                else:
                    await sender.reply(str(choice(AFKSTR)))
                USERS.update({sender.sender_id: 1})
            else:
                if USERS[sender.sender_id] % randint(2, 4) == 0:
                    if AFKREASON:
                        await sender.reply(
                            f"Ainda estou ausente.\
                        \nMotivo: **{AFKREASON}**"
                        )
                    else:
                        await sender.reply(str(choice(AFKSTR)))
                USERS[sender.sender_id] = USERS[sender.sender_id] + 1
            COUNT_MSG = COUNT_MSG + 1


@register(outgoing=True, pattern=r"^\.afk(?: |$)(.*)", disable_errors=True)
async def set_afk(afk_e):
    """For .afk command, allows you to inform people that you are afk when they message you"""
    afk_e.text
    string = afk_e.pattern_match.group(1)
    global ISAFK
    global AFKREASON
    if string:
        AFKREASON = string
        await afk_e.edit("**Ficando ausente!**" f"\nMotivo: {string}")
    else:
        await afk_e.edit("**Ficando ausente!**")
    if BOTLOG:
        await afk_e.client.send_message(BOTLOG_CHATID, "#AFK\nVocê ficou AFK!")
    ISAFK = True
    raise StopPropagation


@register(outgoing=True)
async def type_afk_is_not_true(notafk):
    """This sets your status as not afk automatically when you write something while being afk"""
    global ISAFK
    global COUNT_MSG
    global USERS
    global AFKREASON
    if ISAFK:
        ISAFK = False
        msg = await notafk.respond("**Eu não estou mais ausente.**")
        await sleep(2)
        await msg.delete()
        if BOTLOG:
            await notafk.client.send_message(
                BOTLOG_CHATID,
                f"Você recebeu {str(COUNT_MSG)} mensagens de {str(len(USERS))} bate-papos enquanto você estava fora",
            )
            for i in USERS:
                if i is not None:
                    name = await notafk.client.get_entity(i)
                    name0 = str(name.first_name)
                    await notafk.client.send_message(
                        BOTLOG_CHATID,
                        f"[{name0}](tg://user?id={str(i)}) enviou a você `{str(USERS[i])} mensagens`",
                    )
        COUNT_MSG = 0
        USERS = {}
        AFKREASON = None


CMD_HELP.update(
    {
        "afk": ">`.afk [Motivo Opcional]`"
        "\n**Uso:** Define você como afk.\nResponde automaticamente quem te menciona ou envia mensagens privadas "
        "dizendo a eles que você está AFK(motivo)."
        "\n\nDesliga o AFK quando você digita qualquer coisa, em qualquer lugar."
    }
)
