#!/usr/bin/env python3
# -*- coding: utf-8-*-
#
# (c) https://t.me/TelethonChat/37677 and SpEcHiDe
#
# Licensed under the Raphielscape Public License, Version 1.d (the "License");
# you may not use this file except in compliance with the License.
#

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

print(
    """Vá para my.telegram.org
Faça login usando sua conta do Telegram
Clique em Ferramentas de Desenvolvimento de API
Crie um novo aplicativo, inserindo os detalhes necessários
Verifique a seção de mensagens salvas do Telegram para copiar STRING_SESSION"""
)
API_KEY = int(input("Insira a APP_ID (o mais curto): "))
API_HASH = input("Insira a API_HASH (o mais longo): ")

with TelegramClient(StringSession(), API_KEY, API_HASH) as client:
    print("Verifique suas mensagens salvas no telegram!")
    session_string = client.session.save()
    saved_messages_template = """Suporte: @rokansu

STRING_SESSION: <code>{}</code>

⚠️ <i>NÃO envie isso para mais ninguém!</i>""".format(
        session_string
    )
    client.send_message("me", saved_messages_template, parse_mode="html")
