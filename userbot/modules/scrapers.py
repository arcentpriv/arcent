# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module containing various scrapers. """

import asyncio
import json
import os
import re
import shutil
import time
from asyncio import sleep
from urllib.parse import quote_plus

import asyncurban
from bs4 import BeautifulSoup
from emoji import get_emoji_regexp
from google_trans_new import LANGUAGES, google_translator
from gtts import gTTS
from gtts.lang import tts_langs
from requests import get
from search_engine_parser import GoogleSearch
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo
from wikipedia import summary
from wikipedia.exceptions import DisambiguationError, PageError
from youtube_search import YoutubeSearch
from yt_dlp import YoutubeDL
from yt_dlp.utils import (
    ContentTooShortError,
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    MaxDownloadsReached,
    PostProcessingError,
    UnavailableVideoError,
    XAttrMetadataError,
)

from userbot import BOTLOG, BOTLOG_CHATID, CMD_HELP
from userbot.events import register
from userbot.modules.upload_download import get_video_thumb
from userbot.utils import chrome, googleimagesdownload, progress
from userbot.utils.FastTelethon import upload_file

CARBONLANG = "pt-br"


@register(outgoing=True, pattern=r"^\.crblang (.*)")
async def setlang(prog):
    global CARBONLANG
    CARBONLANG = prog.pattern_match.group(1)
    await prog.edit(f"Idioma para carbon.now.sh definido para {CARBONLANG}")


@register(outgoing=True, pattern=r"^\.carbon")
async def carbon_api(e):
    """ A Wrapper for carbon.now.sh """
    await e.edit("**Processando...**")
    CARBON = "https://carbon.now.sh/?l={lang}&code={code}"
    global CARBONLANG
    textx = await e.get_reply_message()
    pcode = e.text
    if pcode[8:]:
        pcode = str(pcode[8:])
    elif textx:
        pcode = str(textx.message)  # Importing message to module
    code = quote_plus(pcode)  # Converting to urlencoded
    await e.edit("**Processando...\n25%**")
    dl_path = "./.carbon/"
    file_path = dl_path + "carbon.png"
    if os.path.isfile(file_path):
        os.remove(file_path)
    url = CARBON.format(code=code, lang=CARBONLANG)
    driver = await chrome()
    driver.get(url)
    await e.edit("**Processando...\n50%**")
    driver.command_executor._commands["send_command"] = (
        "POST",
        "/session/$sessionId/chromium/send_command",
    )
    params = {
        "cmd": "Page.setDownloadBehavior",
        "params": {"behavior": "allow", "downloadPath": dl_path},
    }
    driver.execute("send_command", params)
    driver.find_element_by_css_selector('[data-cy="quick-export-button"]').click()
    await e.edit("**Processando...\n75%**")
    # Waiting for downloading
    while not os.path.isfile(file_path):
        await sleep(0.5)
    await e.edit("**Processando...\n100%**")
    await e.edit("**Enviando...**")
    await e.client.send_file(
        e.chat_id,
        file_path,
        caption=(
            "Feito usando [Carbon](https://carbon.now.sh/about/),"
            "\num projeto de [Dawn Labs](https://dawnlabs.io/)"
        ),
        force_document=True,
        reply_to=e.message.reply_to_msg_id,
    )

    os.remove(file_path)
    driver.quit()
    # Removing carbon.png after uploading
    await e.delete()  # Deleting msg


@register(outgoing=True, pattern=r"^\.img(?: |$)(\d*)? ?(.*)")
async def img_sampler(event):
    """ For .img command, search and return images matching the query. """

    if event.is_reply and not event.pattern_match.group(2):
        query = await event.get_reply_message()
        query = str(query.message)
    else:
        query = str(event.pattern_match.group(2))

    if not query:
        return await event.edit("**Responda a uma mensagem ou passe uma consulta para pesquisar!**")

    await event.edit("**Processando...**")

    if event.pattern_match.group(1) != "":
        counter = int(event.pattern_match.group(1))
        if counter > 10:
            counter = int(10)
        if counter <= 0:
            counter = int(1)
    else:
        counter = int(3)

    response = googleimagesdownload()

    # creating list of arguments
    arguments = {
        "keywords": query,
        "limit": counter,
        "format": "png",
        "no_directory": "no_directory",
    }

    # if the query contains some special characters, googleimagesdownload errors out
    # this is a temporary workaround for it (maybe permanent)
    try:
        paths = response.download(arguments)
    except Exception as e:
        return await event.edit(f"**Erro:** `{e}`")

    lst = paths[0][query]
    await event.client.send_file(
        await event.client.get_input_entity(event.chat_id), lst
    )
    shutil.rmtree(os.path.dirname(os.path.abspath(lst[0])))
    await event.delete()


@register(outgoing=True, pattern=r"^\.currency ([\d\.]+) ([a-zA-Z]+) ([a-zA-Z]+)")
async def moni(event):
    c_from_val = float(event.pattern_match.group(1))
    c_from = (event.pattern_match.group(2)).upper()
    c_to = (event.pattern_match.group(3)).upper()
    try:
        response = get(
            "https://api.ratesapi.io/api/latest",
            params={"base": c_from, "symbols": c_to},
        ).json()
    except Exception:
        await event.edit("**Erro: API está offline.**")
        return
    if "error" in response:
        await event.edit(
            "**Esta parece ser uma moeda alienígena, que não posso converter agora.**"
        )
        return
    c_to_val = round(c_from_val * response["rates"][c_to], 2)
    await event.edit(f"**{c_from_val} {c_from} = {c_to_val} {c_to}**")


@register(outgoing=True, pattern=r"^\.google(?: |$)(\d*)? ?(.*)")
async def gsearch(event):
    """ For .google command, do a Google search. """

    if event.is_reply and not event.pattern_match.group(2):
        match = await event.get_reply_message()
        match = str(match.message)
    else:
        match = str(event.pattern_match.group(2))

    if not match:
        return await event.edit("**Responda a uma mensagem ou passe uma consulta para pesquisar!**")

    await event.edit("**Processando...**")

    if event.pattern_match.group(1) != "":
        counter = int(event.pattern_match.group(1))
        if counter > 10:
            counter = int(10)
        if counter <= 0:
            counter = int(1)
    else:
        counter = int(3)

    search_args = (str(match), int(1))
    gsearch = GoogleSearch()

    try:
        gresults = await gsearch.async_search(*search_args)
    except Exception:
        return await event.edit(
            "**Erro: sua consulta não foi encontrada ou foi sinalizada como tráfego incomum.**"
        )
    msg = ""

    for i in range(counter):
        try:
            title = gresults["titles"][i]
            link = gresults["links"][i]
            desc = gresults["descriptions"][i]
            msg += f"[{title}]({link})\n`{desc}`\n\n"
        except IndexError:
            break

    await event.edit(
        "**Consulta de pesquisa:**\n`" + match + "`\n\n**Resultados:**\n" + msg, link_preview=False
    )


@register(outgoing=True, pattern=r"^\.wiki(?: |$)(.*)")
async def wiki(wiki_q):
    """ For .wiki command, fetch content from Wikipedia. """

    if wiki_q.is_reply and not wiki_q.pattern_match.group(1):
        match = await wiki_q.get_reply_message()
        match = str(match.message)
    else:
        match = str(wiki_q.pattern_match.group(1))

    if not match:
        return await wiki_q.edit("**Responda a uma mensagem ou passe uma consulta para pesquisar!**")

    await wiki_q.edit("**Processando...**")

    try:
        summary(match)
    except DisambiguationError as error:
        return await wiki_q.edit(f"**Página desambigada encontrada.**\n\n`{error}`")
    except PageError as pageerror:
        return await wiki_q.edit(f"**página não encontrada.**\n\n`{pageerror}`")
    result = summary(match)
    if len(result) >= 4096:
        with open("output.txt", "w+") as file:
            file.write(result)
        await wiki_q.client.send_file(
            wiki_q.chat_id,
            "output.txt",
            reply_to=wiki_q.id,
            caption=r"**Resultado muito grande, enviando como arquivo**",
        )
        if os.path.exists("output.txt"):
            return os.remove("output.txt")
    await wiki_q.edit("**Pesquisa:**\n`" + match + "`\n\n**Resultado:**\n" + result)


@register(outgoing=True, pattern=r"^\.ud(?: |$)(.*)")
async def urban_dict(event):
    """Output the definition of a word from Urban Dictionary"""

    if event.is_reply and not event.pattern_match.group(1):
        query = await event.get_reply_message()
        query = str(query.message)
    else:
        query = str(event.pattern_match.group(1))

    if not query:
        return await event.edit("**Responda a uma mensagem ou passe uma consulta para pesquisar!**")

    await event.edit("**Processando...**")
    ud = asyncurban.UrbanDictionary()
    template = "**Consulta:** `{}`\n\n**Definição:**\n{}\n\n**Exemplo:**\n__{}__"

    try:
        definition = await ud.get_word(query)
    except asyncurban.UrbanException as e:
        return await event.edit(f"**Erro:** `{e}`")

    result = template.format(definition.word, definition.definition, definition.example)

    if len(result) < 4096:
        return await event.edit(result)

    await event.edit("**Resultado muito grande, enviando como arquivo...**")
    with open("output.txt", "w+") as file:
        file.write(
            "Consulta: "
            + definition.word
            + "\n\nSignificado: "
            + definition.definition
            + "Exemplo: \n"
            + definition.example
        )
    await event.client.send_file(
        event.chat_id,
        "output.txt",
        caption=f"Urban Dictionary's definition of {query}",
    )
    if os.path.exists("output.txt"):
        os.remove("output.txt")
    return await event.delete()


@register(outgoing=True, pattern=r"^\.tts(?: |$)([\s\S]*)")
async def text_to_speech(query):
    """ For .tts command, a wrapper for Google Text-to-Speech. """

    if query.is_reply and not query.pattern_match.group(1):
        message = await query.get_reply_message()
        message = str(message.message)
    else:
        message = str(query.pattern_match.group(1))

    if not message:
        return await query.edit(
            "**Envie um texto ou responda a uma mensagem para conversão de texto em voz!**"
        )

    await query.edit("**Processando...**")

    try:
        from userbot.modules.sql_helper.globals import gvarstatus
    except AttributeError:
        return await query.edit("**Executando em modo não SQL!**")

    if gvarstatus("tts_lang") is not None:
        target_lang = str(gvarstatus("tts_lang"))
    else:
        target_lang = "pt"

    try:
        gTTS(message, lang=target_lang)
    except AssertionError:
        return await query.edit(
            "**O texto está vazio.**\n"
            "Não sobrou nada para falar após a pré-precessão, tokenização e limpeza."
        )
    except ValueError:
        return await query.edit("**O idioma não é suportado.**")
    except RuntimeError:
        return await query.edit("**Erro ao carregar o dicionário de idiomas.**")
    tts = gTTS(message, lang=target_lang)
    tts.save("k.mp3")
    with open("k.mp3", "rb") as audio:
        linelist = list(audio)
        linecount = len(linelist)
    if linecount == 1:
        tts = gTTS(message, lang=target_lang)
        tts.save("k.mp3")
    with open("k.mp3"):
        await query.client.send_file(query.chat_id, "k.mp3", voice_note=True)
        os.remove("k.mp3")
    await query.delete()


# kanged from Blank-x ;---;
@register(outgoing=True, pattern=r"^\.imdb (.*)")
async def imdb(e):
    try:
        movie_name = e.pattern_match.group(1)
        remove_space = movie_name.split(" ")
        final_name = "+".join(remove_space)
        page = get(
            "https://www.imdb.com/find?ref_=nv_sr_fn&q=r" + final_name + "&s=all"
        )
        soup = BeautifulSoup(page.content, "lxml")
        odds = soup.findAll("tr", "odd")
        mov_title = odds[0].findNext("td").findNext("td").text
        mov_link = (
            "http://www.imdb.com/" + odds[0].findNext("td").findNext("td").a["href"]
        )
        page1 = get(mov_link)
        soup = BeautifulSoup(page1.content, "lxml")
        if soup.find("div", "poster"):
            poster = soup.find("div", "poster").img["src"]
        else:
            poster = ""
        if soup.find("div", "title_wrapper"):
            pg = soup.find("div", "title_wrapper").findNext("div").text
            mov_details = re.sub(r"\s+", " ", pg)
        else:
            mov_details = ""
        credits = soup.findAll("div", "credit_summary_item")
        director = credits[0].a.text
        if len(credits) == 1:
            writer = "Not available"
            stars = "Not available"
        elif len(credits) > 2:
            writer = credits[1].a.text
            actors = [x.text for x in credits[2].findAll("a")]
            actors.pop()
            stars = actors[0] + "," + actors[1] + "," + actors[2]
        else:
            writer = "Not available"
            actors = [x.text for x in credits[1].findAll("a")]
            actors.pop()
            stars = actors[0] + "," + actors[1] + "," + actors[2]
        if soup.find("div", "inline canwrap"):
            story_line = soup.find("div", "inline canwrap").findAll("p")[0].text
        else:
            story_line = "Not available"
        info = soup.findAll("div", "txt-block")
        if info:
            mov_country = []
            mov_language = []
            for node in info:
                a = node.findAll("a")
                for i in a:
                    if "country_of_origin" in i["href"]:
                        mov_country.append(i.text)
                    elif "primary_language" in i["href"]:
                        mov_language.append(i.text)
        if soup.findAll("div", "ratingValue"):
            for r in soup.findAll("div", "ratingValue"):
                mov_rating = r.strong["title"]
        else:
            mov_rating = "Not available"
        await e.edit(
            "<a href=" + poster + ">&#8203;</a>"
            "<b>Title : </b><code>"
            + mov_title
            + "</code>\n<code>"
            + mov_details
            + "</code>\n<b>Rating : </b><code>"
            + mov_rating
            + "</code>\n<b>Country : </b><code>"
            + mov_country[0]
            + "</code>\n<b>Language : </b><code>"
            + mov_language[0]
            + "</code>\n<b>Director : </b><code>"
            + director
            + "</code>\n<b>Writer : </b><code>"
            + writer
            + "</code>\n<b>Stars : </b><code>"
            + stars
            + "</code>\n<b>IMDB Url : </b>"
            + mov_link
            + "\n<b>Story Line : </b>"
            + story_line,
            link_preview=True,
            parse_mode="HTML",
        )
    except IndexError:
        await e.edit("Por favor, insira um **nome válido de filme** kthx")


@register(outgoing=True, pattern=r"^\.trt(?: |$)([\s\S]*)")
async def translateme(trans):
    """ For .trt command, translate the given text using Google Translate. """

    if trans.is_reply and not trans.pattern_match.group(1):
        message = await trans.get_reply_message()
        message = str(message.message)
    else:
        message = str(trans.pattern_match.group(1))

    if not message:
        return await trans.edit(
            "**Escreva algum texto ou responda a uma mensagem para traduzir!**"
        )

    await trans.edit("**Processando...**")
    translator = google_translator()

    try:
        from userbot.modules.sql_helper.globals import gvarstatus
    except AttributeError:
        return await trans.edit("**Executando em modo não SQL!**")

    if gvarstatus("trt_lang") is not None:
        target_lang = str(gvarstatus("trt_lang"))
    else:
        target_lang = "pt"

    try:
        reply_text = translator.translate(deEmojify(message), lang_tgt=target_lang)
    except ValueError:
        return await trans.edit(
            "**Idioma inválido selecionado, use **`.lang trt <código da linguagem>`**.**"
        )

    try:
        source_lan = translator.detect(deEmojify(message))[1].title()
    except:
        source_lan = "(O Google não forneceu esta informação)"

    reply_text = f"De: **{source_lan}**\nPara: **{LANGUAGES.get(target_lang).title()}**\n\n{reply_text}"

    await trans.edit(reply_text)


@register(pattern=r"\.lang (trt|tts) (.*)", outgoing=True)
async def lang(value):
    """ For .lang command, change the default langauge of userbot scrapers. """
    util = value.pattern_match.group(1).lower()

    try:
        from userbot.modules.sql_helper.globals import addgvar, delgvar, gvarstatus
    except AttributeError:
        return await lang.edit("**Executando em modo não SQL!**")

    if util == "trt":
        scraper = "Translator"
        arg = value.pattern_match.group(2).lower()

        if arg not in LANGUAGES:
            return await value.edit(
                f"**Código de idioma inválido!**\nCódigos de idioma disponíveis:\n\n`{LANGUAGES}`"
            )

        if gvarstatus("trt_lang"):
            delgvar("trt_lang")
        addgvar("trt_lang", arg)
        LANG = LANGUAGES[arg]

    elif util == "tts":
        scraper = "Text to Speech"
        arg = value.pattern_match.group(2).lower()

        if arg not in tts_langs():
            return await value.edit(
                f"**Código de idioma inválido!**\nCódigos de idioma disponíveis:\n\n`{tts_langs()}`"
            )

        if gvarstatus("tts_lang"):
            delgvar("tts_lang")
        addgvar("tts_lang", arg)
        LANG = tts_langs()[arg]

    await value.edit(f"**Idioma de {scraper} mudou para {LANG.title()}.**")
    if BOTLOG:
        await value.client.send_message(
            BOTLOG_CHATID, f"`Idioma de {scraper} mudou para {LANG.title()}.`"
        )


@register(outgoing=True, pattern="^.sg(?: |$)(.*)")
async def lastname(steal):
    if steal.fwd_from:
        return
    if not steal.reply_to_msg_id:
        await steal.edit("**Responda a qualquer mensagem do usuário.**")
        return
    message = await steal.get_reply_message()
    chat = "@SangMataInfo_bot"
    user_id = message.sender.id
    id = f"/search_id {user_id}"
    if message.sender.bot:
        await steal.edit("**Responda a mensagem de usuários reais.**")
        return
    await steal.edit("**Espere enquanto eu roubo alguns dados da NASA**")
    async with bot.conversation(chat) as conv:
        try:
            msg = await conv.send_message(id)
            r = await conv.get_response()
            response = await conv.get_response()
        except YouBlockedUserError:
            await steal.reply("**Desbloqueie @sangmatainfo_bot e tente novamente**")
            return
        if response.text.startswith("No records"):
            await steal.edit("**Nenhum registro encontrado para este usuário**")
            await steal.client.delete_messages(
                conv.chat_id, [msg.id, r.id, response.id]
            )
            return
        else:
            respond = await conv.get_response()
            await steal.edit(f"{response.message}")
        await steal.client.delete_messages(
            conv.chat_id, [msg.id, r.id, response.id, respond.id]
        )


@register(outgoing=True, pattern=r"^\.yt(?: |$)(\d*)? ?(.*)")
async def yt_search(event):
    """ For .yt command, do a YouTube search from Telegram. """

    if event.is_reply and not event.pattern_match.group(2):
        query = await event.get_reply_message()
        query = str(query.message)
    else:
        query = str(event.pattern_match.group(2))

    if not query:
        return await event.edit("**Responda a uma mensagem ou passe uma consulta para pesquisar!**")

    await event.edit("**Processando...**")

    if event.pattern_match.group(1) != "":
        counter = int(event.pattern_match.group(1))
        if counter > 10:
            counter = int(10)
        if counter <= 0:
            counter = int(1)
    else:
        counter = int(3)

    try:
        results = json.loads(YoutubeSearch(query, max_results=counter).to_json())
    except KeyError:
        return await event.edit("**Youtube está louco!.\nNão é possível pesquisar esta consulta!**")

    output = f"**Consulta de pesquisa:**\n`{query}`\n\n**Resultados:**\n"

    for i in results["videos"]:
        try:
            title = i["title"]
            link = "https://youtube.com" + i["url_suffix"]
            channel = i["channel"]
            duration = i["duration"]
            views = i["views"]
            output += f"[{title}]({link})\nCanal: `{channel}`\nDuração: {duration} | {views}\n\n"
        except IndexError:
            break

    await event.edit(output, link_preview=False)


@register(outgoing=True, pattern=r"^\.r(a|v)(?: |$)(.*)")
async def download_video(v_url):
    """ For media downloader command, download media from YouTube and many other sites. """

    if v_url.is_reply and not v_url.pattern_match.group(2):
        url = await v_url.get_reply_message()
        url = str(url.text)
    else:
        url = str(v_url.pattern_match.group(2))

    if not url:
        return await v_url.edit("**Responda a uma mensagem com um URL ou passe um URL!**")

    type = v_url.pattern_match.group(1).lower()
    await v_url.edit("**Preparando para baixar...**")

    if type == "a":
        opts = {
            "format": "bestaudio",
            "addmetadata": True,
            "key": "FFmpegMetadata",
            "writethumbnail": True,
            "prefer_ffmpeg": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ],
            "outtmpl": "%(id)s.mp3",
            "quiet": True,
            "logtostderr": False,
            "external_downloader": "aria2c",
        }
        video = False
        song = True

    elif type == "v":
        opts = {
            "format": "best",
            "addmetadata": True,
            "key": "FFmpegMetadata",
            "prefer_ffmpeg": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "postprocessors": [
                {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
            ],
            "outtmpl": "%(id)s.mp4",
            "logtostderr": False,
            "quiet": True,
            "external_downloader": "aria2c",
        }
        song = False
        video = True

    try:
        await v_url.edit("**Buscando dados, por favor aguarde..**")
        with YoutubeDL(opts) as rip:
            rip_data = rip.extract_info(url)
    except DownloadError as DE:
        return await v_url.edit(f"`{str(DE)}`")
    except ContentTooShortError:
        return await v_url.edit("**O conteúdo do download era muito curto.**")
    except GeoRestrictedError:
        return await v_url.edit(
            "**O vídeo não está disponível em sua localização geográfica "
            "devido a restrições geográficas impostas pelo site.**"
        )
    except MaxDownloadsReached:
        return await v_url.edit("**O limite máximo de downloads foi atingido.**")
    except PostProcessingError:
        return await v_url.edit("**Ocorreu um erro durante o pós-processamento.**")
    except UnavailableVideoError:
        return await v_url.edit("**A mídia não está disponível no formato solicitado.**")
    except XAttrMetadataError as XAME:
        return await v_url.edit(f"`{XAME.code}: {XAME.msg}\n{XAME.reason}`")
    except ExtractorError:
        return await v_url.edit("**Ocorreu um erro durante a extração de informações.**")
    except Exception as e:
        return await v_url.edit(f"{str(type(e)): {str(e)}}")
    c_time = time.time()
    if song:
        await v_url.edit(f"**Preparando para fazer upload da música:**\n**{rip_data['title']}**")
        with open(rip_data["id"] + ".mp3", "rb") as f:
            result = await upload_file(
                client=v_url.client,
                file=f,
                name=f"{rip_data['id']}.mp3",
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(
                        d,
                        t,
                        v_url,
                        c_time,
                        "YouTube-DL - Upload",
                        f"{rip_data['title']}.mp3",
                    )
                ),
            )
        img_extensions = ["jpg", "jpeg", "webp"]
        img_filenames = [
            fn_img
            for fn_img in os.listdir()
            if any(fn_img.endswith(ext_img) for ext_img in img_extensions)
        ]
        thumb_image = img_filenames[0]
        await v_url.client.send_file(
            v_url.chat_id,
            result,
            supports_streaming=True,
            attributes=[
                DocumentAttributeAudio(
                    duration=int(rip_data["duration"]),
                    title=str(rip_data["title"]),
                    performer=str(rip_data["uploader"]),
                )
            ],
            thumb=thumb_image,
        )
        os.remove(thumb_image)
        os.remove(f"{rip_data['id']}.mp3")
        await v_url.delete()
    elif video:
        await v_url.edit(f"**Preparando para enviar vídeo:**\n**{rip_data['title']}**")
        thumb_image = await get_video_thumb(rip_data["id"] + ".mp4", "thumb.png")
        with open(rip_data["id"] + ".mp4", "rb") as f:
            result = await upload_file(
                client=v_url.client,
                file=f,
                name=f"{rip_data['id']}.mp4",
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(
                        d,
                        t,
                        v_url,
                        c_time,
                        "YouTube-DL - Upload",
                        f"{rip_data['title']}.mp4",
                    )
                ),
            )
        await v_url.client.send_file(
            v_url.chat_id,
            result,
            thumb=thumb_image,
            attributes=[
                DocumentAttributeVideo(
                    duration=rip_data["duration"],
                    w=rip_data["width"],
                    h=rip_data["height"],
                    supports_streaming=True,
                )
            ],
            caption=rip_data["title"],
        )
        os.remove(f"{rip_data['id']}.mp4")
        os.remove(thumb_image)
        await v_url.delete()


def deEmojify(inputString):
    """ Remove emojis and other non-safe characters from string """
    return get_emoji_regexp().sub("", inputString)


CMD_HELP.update(
    {
        "img": ">`.img [número] <consulta> [ou responder]`"
        "\n**Uso:** Faz uma pesquisa de imagens no Google."
        "\nPode especificar o número de resultados necessários (o padrão é 3).",
        "currency": ">`.currency <quantia> <Moeda-origem> <Moeda-alvo>`"
        "\n**Uso:** Converte várias moedas para você.",
        "carbon": ">`.carbon <texto> [ou resposta]`"
        "\n**Uso:** Embeleze seu código usando carbon.now.sh\n"
        "Use .crblang <texto> para definir o idioma do seu código.",
        "google": ">`.google [número] <consulta> [ou resposta]`"
        "\n**Uso:** Faz uma pesquisa no Google."
        "\nPode especificar o número de resultados necessários (o padrão é 3).",
        "wiki": ">`.wiki <consulta> [ou resposta]`" "\n**Uso:** Faz uma pesquisa na Wikipedia.",
        "ud": ">`.ud <consulta> [ou resposta]`" "\n**Uso:** Faz uma pesquisa no Dicionário Urbano.",
        "tts": ">`.tts <text> [ou resposta]`"
        "\n**Uso:** Traduz texto em fala para o idioma definido."
        "\nUse >`.lang tts <código da linguagem>` para definir o idioma do tts. (Padrão é PT-BR.)",
        "trt": ">`.trt <texto> [ou resposta]`"
        "\n**Uso:** Traduz o texto para o idioma definido."
        "\nUse >`.lang trt <código da linguagem>` para definir o idioma para trt. (Padrão é PT-BR)",
        "yt": ">`.yt [número] <consulta> [ou resposta]`"
        "\n**Uso:** Faz uma pesquisa no YouTube."
        "\nPode especificar o número de resultados necessários (o padrão é 3).",
        "imdb": ">`.imdb <nome-do-filme>`" "\n**Uso:** Mostra informações do filme e outras coisas.",
        "rip": ">`.ra <url> [ou resposta] ou .rv <url> [ou resposta]`"
        "\n**Uso:** Baixe vídeos e músicas do YouTube "
        "(e [muitos outros sites](https://ytdl-org.github.io/youtube-dl/supportedsites.html)).",
    }
)
