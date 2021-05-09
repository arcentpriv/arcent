# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.d (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot help command """

from userbot import CMD_HELP
from userbot.events import register


@register(outgoing=True, pattern=r"^\.help(?: |$)(.*)")
async def help(event):
    """For .help command,"""
    args = event.pattern_match.group(1).lower()
    # Prevent Channel Bug to get any information and command from all modules
    if event.is_channel and not event.is_group:
        await event.edit("`O comando de ajuda não é permitido em canais`")
        return
    if args:
        if args in CMD_HELP:
            await event.edit(str(CMD_HELP[args]))
        else:
            await event.edit("Especifique um nome de módulo válido.")
    else:
        final = "**Lista de todos os módulos carregados**\n\
                 \nEspecifique para qual módulo você deseja ajuda! \
                 \n**Uso:** `.help` <nome do módulo>\n\n"

        temp = "".join(str(i) + " " for i in CMD_HELP)
        temp = sorted(temp.split())
        for i in temp:
            final += "`" + str(i)
            final += "`\t\t\t•\t\t\t "
        await event.edit(f"{final[:-5]}")
