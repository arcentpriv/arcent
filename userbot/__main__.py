# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot start point """

import sys
from importlib import import_module

from telethon.errors.rpcerrorlist import PhoneNumberInvalidError

from userbot import LOGS, bot
from userbot.modules import ALL_MODULES

INVALID_PH = (
    "\nErro: número de telefone inválido."
    "\nDica: número de prefixo com código do país"
    "\nou verifique o seu número de telefone e tente novamente."
)

try:
    bot.start()
except PhoneNumberInvalidError:
    print(INVALID_PH)
    sys.exit(1)

for module_name in ALL_MODULES:
    imported_module = import_module("userbot.modules." + module_name)

LOGS.info("Seu userbot está em execução!")

LOGS.info(
    "Parabéns, o bot está instalado e funcionando! Envie .help em qualquer chat para mais informações.\n"
    "Se precisar de ajuda, mande uma mensagem para @Kircheiss (cuidado, ela morde)"
)

bot.run_until_disconnected()
