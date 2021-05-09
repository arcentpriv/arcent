# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module for getting information about the server. """

from asyncio import create_subprocess_exec as asyncrunapp
from asyncio.subprocess import PIPE as asyncPIPE
from os import remove
from platform import python_version, uname
from shutil import which

from telethon import version

from userbot import ALIVE_LOGO, ALIVE_NAME, CMD_HELP, PURPLEBOT_VERSION, bot
from userbot.events import register

# ================= CONSTANT =================
DEFAULTUSER = ALIVE_NAME or "Defina a ConfigVar `ALIVE_NAME` !"
# ============================================


@register(outgoing=True, pattern=r"^\.sysd$")
async def sysdetails(sysd):
    """For .sysd command, get system info using neofetch."""
    if not sysd.text[0].isalpha() and sysd.text[0] not in ("/", "#", "@", "!"):
        try:
            fetch = await asyncrunapp(
                "neofetch",
                "--stdout",
                stdout=asyncPIPE,
                stderr=asyncPIPE,
            )

            stdout, stderr = await fetch.communicate()
            result = str(stdout.decode().strip()) + str(stderr.decode().strip())

            await sysd.edit("`" + result + "`")
        except FileNotFoundError:
            await sysd.edit("**Instale o neofetch primeiro!**")


@register(outgoing=True, pattern=r"^\.botver$")
async def bot_ver(event):
    """For .botver command, get the bot version."""
    if event.text[0].isalpha() or event.text[0] in ("/", "#", "@", "!"):
        return
    if which("git") is not None:
        ver = await asyncrunapp(
            "git",
            "describe",
            "--all",
            "--long",
            stdout=asyncPIPE,
            stderr=asyncPIPE,
        )
        stdout, stderr = await ver.communicate()
        verout = str(stdout.decode().strip()) + str(stderr.decode().strip())

        rev = await asyncrunapp(
            "git",
            "rev-list",
            "--all",
            "--count",
            stdout=asyncPIPE,
            stderr=asyncPIPE,
        )
        stdout, stderr = await rev.communicate()
        revout = str(stdout.decode().strip()) + str(stderr.decode().strip())

        await event.edit(f"**Versão do Userbot:** `{verout}`\n" f"**Revisão:** `{revout}`\n")
    else:
        await event.edit("**Pena que você não tem git!**")


@register(outgoing=True, pattern=r"^\.pip(?: |$)(.*)")
async def pipcheck(pip):
    """For .pip command, do a pip search."""
    if pip.text[0].isalpha() or pip.text[0] in ("/", "#", "@", "!"):
        return
    pipmodule = pip.pattern_match.group(1)
    if pipmodule:
        await pip.edit("**Procurando...**")
        pipc = await asyncrunapp(
            "pip3",
            "search",
            pipmodule,
            stdout=asyncPIPE,
            stderr=asyncPIPE,
        )

        stdout, stderr = await pipc.communicate()
        pipout = str(stdout.decode().strip()) + str(stderr.decode().strip())

        if pipout:
            if len(pipout) > 4096:
                await pip.edit("**Resultado muito grande, enviando como arquivo...**")
                with open("output.txt", "w+") as file:
                    file.write(pipout)
                await pip.client.send_file(
                    pip.chat_id,
                    "output.txt",
                    reply_to=pip.id,
                )
                remove("output.txt")
                return
            await pip.edit(
                "**Consulta: **\n`"
                f"pip3 search {pipmodule}"
                "`\n**Resultado: **\n`"
                f"{pipout}"
                "`"
            )
        else:
            await pip.edit(
                "**Consulta: **\n`"
                f"pip3 search {pipmodule}"
                "`\n**Resultado: **\n`Nenhum resultado encontrado/falso`"
            )
    else:
        await pip.edit("**Use `.help pip` para ver um exemplo.**")


@register(outgoing=True, pattern=r"^.(alive|on)$")
async def amireallyalive(alive):
    """ For .alive command, check if the bot is running.  """
    output = (
        "`➖➖➖➖➖➖➖➖➖➖➖`\n"
        f"•  👾 PurpleBot   :   v{PURPLEBOT_VERSION} \n"
        f"•  ⚙️ Telethon     :   v{version.__version__} \n"
        f"•  🐍 Python         :   v{python_version()} \n"
        f"•  👤 Usuário        :   {DEFAULTUSER} \n"
        "`➖➖➖➖➖➖➖➖➖➖➖`"
    )
    if ALIVE_LOGO:
        try:
            logo = ALIVE_LOGO
            await bot.send_file(alive.chat_id, logo, caption=output)
            await alive.delete()
        except BaseException:
            await alive.edit(
                output + "\n\n **O logotipo fornecido é inválido**."
                "\n`Certifique-se de que o link seja direcionado para a imagem do logotipo`"
            )
    else:
        await alive.edit(output)


@register(outgoing=True, pattern=r"^\.aliveu")
async def amireallyaliveuser(username):
    """For .aliveu command, change the username in the .alive command."""
    message = username.text
    if message != ".aliveu" and message[7:8] == " ":
        newuser = message[8:]
        global DEFAULTUSER
        DEFAULTUSER = newuser
    await username.edit(f"**Usuário alterado com sucesso para** `{newuser}`**!**")


@register(outgoing=True, pattern=r"^\.resetalive$")
async def amireallyalivereset(ureset):
    """For .resetalive command, reset the username in the .alive command."""
    global DEFAULTUSER
    DEFAULTUSER = str(ALIVE_NAME) if ALIVE_NAME else uname().node
    await ureset.edit("**Usuário redefinido com sucesso para o alive!**")


CMD_HELP.update(
    {
        "sysd": ">`.sysd`" "\n**Uso:** Mostra informações do sistema usando neofetch.",
        "botver": ">`.botver`" "\n**Uso:** Mostra a versão do userbot.",
        "pip": ">`.pip <module(s)>`" "\n**Uso:** Faz uma pesquisa de módulos pip.",
        "alive": ">`.alive`"
        "\n**Uso:** Digite .alive para ver se seu bot está funcionando ou não."
        "\n\n>`.aliveu <texto>`"
        "\n**Uso:** Muda o 'Usuário' do alive para o texto que você deseja."
        "\n\n>`.resetalive`"
        "\n**Uso:** Redefine o Usuário para o padrão.",
    }
)
