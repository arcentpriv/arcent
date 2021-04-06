# Copyright (C) 2020 Adek Maulana
#
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ProjectBish Google Drive managers

import asyncio
import base64
import io
import json
import logging
import math
import os
import pickle
import re
import time
from mimetypes import guess_type
from os.path import getctime, isdir, isfile, join
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from telethon import events

import userbot.modules.sql_helper.google_drive_sql as helper
from userbot import (
    BOTLOG_CHATID,
    CMD_HELP,
    G_DRIVE_CLIENT_ID,
    G_DRIVE_CLIENT_SECRET,
    G_DRIVE_DATA,
    G_DRIVE_FOLDER_ID,
    G_DRIVE_INDEX_URL,
    LOGS,
    TEMP_DOWNLOAD_DIRECTORY,
)
from userbot.events import register
from userbot.modules.aria import aria2, check_metadata
from userbot.utils import human_to_bytes, humanbytes, progress, time_formatter
from userbot.utils.exceptions import CancelProcess

# =========================================================== #
#                          STATIC                             #
# =========================================================== #
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.metadata",
]
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
# =========================================================== #
#      STATIC CASE FOR G_DRIVE_FOLDER_ID IF VALUE IS URL      #
# =========================================================== #
__ = G_DRIVE_FOLDER_ID
if __ is not None:
    if "uc?id=" in G_DRIVE_FOLDER_ID:
        LOGS.info("G_DRIVE_FOLDER_ID não é uma pasta válida/URL...")
        G_DRIVE_FOLDER_ID = None
    try:
        G_DRIVE_FOLDER_ID = __.split("folders/")[1]
    except IndexError:
        try:
            G_DRIVE_FOLDER_ID = __.split("open?id=")[1]
        except IndexError:
            if "/view" in __:
                G_DRIVE_FOLDER_ID = __.split("/")[-2]
            else:
                try:
                    G_DRIVE_FOLDER_ID = __.split("folderview?id=")[1]
                except IndexError:
                    if "http://" not in __ or "https://" not in __:
                        _1 = any(map(str.isdigit, __))
                        _2 = bool("-" in __ or "_" in __)
                        if True not in [_1 or _2]:
                            LOGS.info("G_DRIVE_FOLDER_ID " "não é um ID válido...")
                            G_DRIVE_FOLDER_ID = None
                    else:
                        LOGS.info("G_DRIVE_FOLDER_ID " "não é um URL válido...")
                        G_DRIVE_FOLDER_ID = None
# =========================================================== #
#                           LOG                               #
# =========================================================== #
logger = logging.getLogger("googleapiclient.discovery")
logger.setLevel(logging.ERROR)
# =========================================================== #
#                                                             #
# =========================================================== #


@register(pattern=r"^\.gdauth(?: |$)", outgoing=True)
async def generate_credentials(gdrive):
    """ - Only generate once for long run - """
    if helper.get_credentials(str(gdrive.sender_id)) is not None:
        await gdrive.edit("**Você já autorizou o bot.**")
        await asyncio.sleep(1.5)
        await gdrive.delete()
        return False
    # Generate credentials
    if G_DRIVE_DATA is not None:
        try:
            configs = json.loads(G_DRIVE_DATA)
        except json.JSONDecodeError:
            await gdrive.edit("**Erro:** `G_DRIVE_DATA` **elemento inválido!**")
            return False
    else:
        # Only for old user
        if G_DRIVE_CLIENT_ID is None and G_DRIVE_CLIENT_SECRET is None:
            await gdrive.edit(
                "`G_DRIVE_DATA` **não encontrado.\nTutorial:** [Link](https://www.youtube.com/watch?v=Z0WFtwDMnes&ab_channel=TUDOSEMCORTE)"
            )
            return False
        configs = {
            "installed": {
                "client_id": G_DRIVE_CLIENT_ID,
                "client_secret": G_DRIVE_CLIENT_SECRET,
                "auth_uri": GOOGLE_AUTH_URI,
                "token_uri": GOOGLE_TOKEN_URI,
            }
        }
    await gdrive.edit("**Criando credenciais...**")
    flow = InstalledAppFlow.from_client_config(
        configs, SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    msg = await gdrive.respond("**Vá para o seu grupo BOTLOG para autenticar o token.**")
    async with gdrive.client.conversation(BOTLOG_CHATID) as conv:
        url_msg = await conv.send_message(
            "**Por favor, vá para este URL:**\n"
            f"{auth_url}\n"
            "**Autorize e envie o código em resposta a esta mensagem.**"
        )
        r = conv.wait_event(events.NewMessage(outgoing=True, chats=BOTLOG_CHATID))
        r = await r
        code = r.message.message.strip()
        flow.fetch_token(code=code)
        creds = flow.credentials
        await asyncio.sleep(3.5)
        await gdrive.client.delete_messages(gdrive.chat_id, msg.id)
        await gdrive.client.delete_messages(BOTLOG_CHATID, [url_msg.id, r.id])
        # Unpack credential objects into strings
        creds = base64.b64encode(pickle.dumps(creds)).decode()
        await gdrive.edit("**Credenciais criadas.**")
    helper.save_credentials(str(gdrive.sender_id), creds)
    await gdrive.delete()
    return


async def create_app(gdrive):
    """ - Create google drive service app - """
    creds = helper.get_credentials(str(gdrive.sender_id))
    if creds is not None:
        # Repack credential objects from strings
        creds = pickle.loads(base64.b64decode(creds.encode()))
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            await gdrive.edit("**Atualizando credenciais...**")
            # Refresh credentials
            creds.refresh(Request())
            helper.save_credentials(
                str(gdrive.sender_id), base64.b64encode(pickle.dumps(creds)).decode()
            )
        else:
            await gdrive.edit("**Credenciais não encontradas, gere-as.**")
            return False
    return build("drive", "v3", credentials=creds, cache_discovery=False)


@register(pattern=r"^\.gdreset(?: |$)", outgoing=True)
async def reset_credentials(gdrive):
    """ - Reset credentials or change account - """
    await gdrive.edit("**Redefinindo credenciais...**")
    helper.clear_credentials(str(gdrive.sender_id))
    await gdrive.edit("**As credenciais foram redefinidas.**")
    await asyncio.sleep(1)
    await gdrive.delete()
    return


async def get_raw_name(file_path):
    """ - Get file_name from file_path - """
    return file_path.split("/")[-1]


async def get_mimeType(name):
    """ - Check mimeType given file - """
    mimeType = guess_type(name)[0]
    if not mimeType:
        mimeType = "text/plain"
    return mimeType


async def download(gdrive, service, uri=None):
    global is_cancelled
    # Download files to local then upload
    if not isdir(TEMP_DOWNLOAD_DIRECTORY):
        os.makedirs(TEMP_DOWNLOAD_DIRECTORY)
        required_file_name = None
    if uri:
        full_path = os.getcwd() + TEMP_DOWNLOAD_DIRECTORY.strip(".")
        if isfile(uri) and uri.endswith(".torrent"):
            downloads = aria2.add_torrent(
                uri, uris=None, options={"dir": full_path}, position=None
            )
        else:
            uri = [uri]
            downloads = aria2.add_uris(uri, options={"dir": full_path}, position=None)
        gid = downloads.gid
        await check_progress_for_dl(gdrive, gid, previous=None)
        file = aria2.get_download(gid)
        filename = file.name
        if file.followed_by_ids:
            new_gid = await check_metadata(gid)
            await check_progress_for_dl(gdrive, new_gid, previous=None)
        try:
            required_file_name = TEMP_DOWNLOAD_DIRECTORY + filenames
        except Exception:
            required_file_name = TEMP_DOWNLOAD_DIRECTORY + filename
    else:
        try:
            current_time = time.time()
            is_cancelled = False
            downloaded_file_name = await gdrive.client.download_media(
                await gdrive.get_reply_message(),
                TEMP_DOWNLOAD_DIRECTORY,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(
                        d,
                        t,
                        gdrive,
                        current_time,
                        "**GDrive - Download**",
                        is_cancelled=is_cancelled,
                    )
                ),
            )
        except CancelProcess:
            names = [
                join(TEMP_DOWNLOAD_DIRECTORY, name)
                for name in os.listdir(TEMP_DOWNLOAD_DIRECTORY)
            ]
            # asumming newest files are the cancelled one
            newest = max(names, key=getctime)
            os.remove(newest)
            reply = "**GDrive - Download**\n\n" "**Status:** Cancelado."
            return reply
        else:
            required_file_name = downloaded_file_name
    try:
        file_name = await get_raw_name(required_file_name)
    except AttributeError:
        reply = "**Erro: arquivo inválido.**"
        return reply
    mimeType = await get_mimeType(required_file_name)
    try:
        if isfile(required_file_name):
            try:
                result = await upload(
                    gdrive, service, required_file_name, file_name, mimeType
                )
            except CancelProcess:
                reply = "**GDrive - Upload de arquivo**\n\n" "**Status:** Cancelado."
                return reply
            else:
                reply = f"**GDrive - Upload de arquivo**\n\n[{file_name}]({result[1]})"
                reply += f"\n**Tamanho:** {humanbytes(result[0])}"
                if G_DRIVE_INDEX_URL:
                    index_url = G_DRIVE_INDEX_URL.rstrip("/") + "/" + quote(file_name)
                    reply += f"\n**Índice:** [Link]({index_url})"
                return reply
        else:
            global parent_Id
            folder = await create_dir(service, file_name)
            parent_Id = folder.get("id")
            webViewURL = "https://drive.google.com/drive/folders/" + parent_Id
            try:
                await task_directory(gdrive, service, required_file_name)
            except CancelProcess:
                reply = "**GDrive - Upload de pasta**\n\n" "**Status:** Cancelado."
                await reset_parentId()
                return reply
            except Exception:
                await reset_parentId()
            else:
                folder_size = await count_dir_size(service, parent_Id)
                reply = f"**GDrive - Upload de pasta**\n\n[{file_name}]({webViewURL})"
                reply += f"\n**Tamanho:** {humanbytes(folder_size)}"
                if G_DRIVE_INDEX_URL:
                    index_url = (
                        G_DRIVE_INDEX_URL.rstrip("/") + "/" + quote(file_name) + "/"
                    )
                    reply += f"\n**Índice:** [Link]({index_url})"
                await reset_parentId()
                return reply
    except Exception as e:
        reply = f"**GDrive**\n\n" "**Status:** Falha.\n" f"**Motivo:** `{str(e)}`"
        return reply
    return


async def download_gdrive(gdrive, service, uri):
    global is_cancelled
    # remove drivesdk and export=download from link
    if not isdir(TEMP_DOWNLOAD_DIRECTORY):
        os.mkdir(TEMP_DOWNLOAD_DIRECTORY)
    if "&export=download" in uri:
        uri = uri.split("&export=download")[0]
    elif "file/d/" in uri and "/view" in uri:
        uri = uri.split("?usp=drivesdk")[0]
    try:
        file_Id = uri.split("uc?id=")[1]
    except IndexError:
        try:
            file_Id = uri.split("open?id=")[1]
        except IndexError:
            if "/view" in uri:
                file_Id = uri.split("/")[-2]
            else:
                try:
                    file_Id = uri.split("uc?export=download&confirm=")[1].split("id=")[
                        1
                    ]
                except IndexError:
                    # if error parse in url, assume given value is Id
                    file_Id = uri
    try:
        file = await get_information(service, file_Id)
        await gdrive.edit("**Baixando do GDrive...**")
    except HttpError as e:
        if "404" in str(e):
            drive = "https://drive.google.com"
            url = f"{drive}/uc?export=download&id={file_Id}"

            session = requests.session()
            download = session.get(url, stream=True)

            try:
                download.headers["Content-Disposition"]
            except KeyError:
                page = BeautifulSoup(download.content, "lxml")
                try:
                    export = drive + page.find("a", {"id": "uc-download-link"}).get(
                        "href"
                    )
                except AttributeError:
                    try:
                        error = (
                            page.find("p", {"class": "uc-error-caption"}).text
                            + "\n"
                            + page.find("p", {"class": "uc-error-subcaption"}).text
                        )
                    except Exception:
                        reply = (
                            "**GDrive - Download**\n\n"
                            "**Status:** Falha.\n"
                            "**Motivo:** Erro desconhecido."
                        )
                    else:
                        reply = (
                            "**GDrive - Download**\n\n"
                            "**Status:** Falha.\n"
                            f"**Motivo:** `{error}`."
                        )
                    return reply
                download = session.get(export, stream=True)
                file_size = human_to_bytes(
                    page.find("span", {"class": "uc-name-size"})
                    .text.split()[-1]
                    .strip("()")
                )
            else:
                file_size = int(download.headers["Content-Length"])

            file_name = re.search(
                'filename="(.*)"', download.headers["Content-Disposition"]
            ).group(1)
            file_path = TEMP_DOWNLOAD_DIRECTORY + file_name
            with io.FileIO(file_path, "wb") as files:
                CHUNK_SIZE = None
                current_time = time.time()
                display_message = None
                first = True
                is_cancelled = False
                for chunk in download.iter_content(CHUNK_SIZE):
                    if is_cancelled:
                        raise CancelProcess

                    if not chunk:
                        break

                    diff = time.time() - current_time
                    if first:
                        downloaded = len(chunk)
                        first = False
                    else:
                        downloaded += len(chunk)
                    percentage = downloaded / file_size * 100
                    speed = round(downloaded / diff, 2)
                    eta = round((file_size - downloaded) / speed)
                    prog_str = "**Baixando:** `[{}{}]` **{}%**".format(
                        "".join(["●" for _ in range(math.floor(percentage / 10))]),
                        "".join(["○" for _ in range(10 - math.floor(percentage / 10))]),
                        round(percentage, 2),
                    )
                    current_message = (
                        "**GDrive - Download**\n\n"
                        f"**{file_name}**\n"
                        f"{prog_str}\n"
                        f"{humanbytes(downloaded)} de {humanbytes(file_size)}"
                        f" @ {humanbytes(speed)}\n"
                        f"**Tempo estimado:** {time_formatter(eta)}"
                    )
                    if (
                        round(diff % 15.00) == 0
                        and (display_message != current_message)
                        or (downloaded == file_size)
                    ):
                        await gdrive.edit(current_message)
                        display_message = current_message
                    files.write(chunk)
    else:
        file_name = file.get("name")
        mimeType = file.get("mimeType")
        if mimeType == "application/vnd.google-apps.folder":
            await gdrive.edit("**Erro: Não é possível baixar pastas.**")
            return False
        file_path = TEMP_DOWNLOAD_DIRECTORY + file_name
        request = service.files().get_media(fileId=file_Id, supportsAllDrives=True)
        with io.FileIO(file_path, "wb") as df:
            downloader = MediaIoBaseDownload(df, request)
            complete = False
            is_cancelled = False
            current_time = time.time()
            display_message = None
            while not complete:
                if is_cancelled:
                    raise CancelProcess

                status, complete = downloader.next_chunk()
                if status:
                    file_size = status.total_size or 0
                    diff = time.time() - current_time
                    downloaded = status.resumable_progress
                    percentage = downloaded / file_size * 100
                    speed = round(downloaded / diff, 2)
                    eta = round((file_size - downloaded) / speed)
                    prog_str = "**Baixando:** `[{}{}]` **{}%**".format(
                        "".join("●" for _ in range(math.floor(percentage / 10))),
                        "".join("○" for _ in range(10 - math.floor(percentage / 10))),
                        round(percentage, 2),
                    )

                    current_message = (
                        "**GDrive - Download**\n\n"
                        f"**{file_name}**\n"
                        f"{prog_str}\n"
                        f"{humanbytes(downloaded)} de {humanbytes(file_size)}"
                        f" @ {humanbytes(speed)}\n"
                        f"**Tempo estimado:** {time_formatter(eta)}"
                    )
                    if (
                        round(diff % 15.00) == 0
                        and (display_message != current_message)
                        or (downloaded == file_size)
                    ):
                        await gdrive.edit(current_message)
                        display_message = current_message
    await gdrive.edit(
        "**GDrive - Download**\n\n"
        f"**Nome:** `{file_name}`\n"
        f"**Tamanho:** `{humanbytes(file_size)}`\n"
        f"**Local:** `{file_path}`\n"
        "**Status:** Download com sucesso."
    )
    msg = await gdrive.respond("**Responda à pergunta em seu grupo do BOTLOG.**")
    async with gdrive.client.conversation(BOTLOG_CHATID) as conv:
        ask = await conv.send_message("**Prosseguir com o espelhamento? [S/N]**")
        try:
            r = conv.wait_event(events.NewMessage(outgoing=True, chats=BOTLOG_CHATID))
            r = await r
        except Exception:
            ans = "N"
        else:
            ans = r.message.message.strip()
            await gdrive.client.delete_messages(BOTLOG_CHATID, r.id)
        await gdrive.client.delete_messages(gdrive.chat_id, msg.id)
        await gdrive.client.delete_messages(BOTLOG_CHATID, ask.id)
    if ans.capitalize() == "N":
        return None
    if ans.capitalize() == "S":
        try:
            result = await upload(gdrive, service, file_path, file_name, mimeType)
        except CancelProcess:
            reply = "**GDrive - Upload**\n\n" "**Status:** Cancelado."
        else:
            reply = (
                "**GDrive - Upload**\n\n"
                f"**Nome:** `{file_name}`\n"
                f"**Tamanho:** `{humanbytes(result[0])}`\n"
                f"**Link:** [{file_name}]({result[1]})\n"
                "**Status:** Enviado com sucesso."
            )
        return reply
    await gdrive.client.send_message(BOTLOG_CHATID, "**Erro: escolha inválida.**")
    return None


async def change_permission(service, Id):
    permission = {"role": "reader", "type": "anyone"}
    try:
        service.permissions().create(fileId=Id, body=permission).execute()
    except HttpError as e:
        # it's not possible to change permission per file for teamdrive
        if f'"Arquivo não encontrado: {Id}."' in str(e) or (
            '"O compartilhamento de pastas dentro de um drive compartilhado não é compatível."'
            in str(e)
        ):
            return
        else:
            raise e
    return


async def get_information(service, Id):
    return (
        service.files()
        .get(
            fileId=Id,
            fields="name, id, size, mimeType, "
            "webViewLink, webContentLink,"
            "description",
            supportsAllDrives=True,
        )
        .execute()
    )


async def create_dir(service, folder_name):
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    try:
        len(parent_Id)
    except NameError:
        # Fallback to G_DRIVE_FOLDER_ID else root dir
        if G_DRIVE_FOLDER_ID is not None:
            metadata["parents"] = [G_DRIVE_FOLDER_ID]
    else:
        # Override G_DRIVE_FOLDER_ID because parent_Id not empty
        metadata["parents"] = [parent_Id]
    folder = (
        service.files()
        .create(body=metadata, fields="id, webViewLink", supportsAllDrives=True)
        .execute()
    )
    await change_permission(service, folder.get("id"))
    return folder


async def upload(gdrive, service, file_path, file_name, mimeType):
    try:
        await gdrive.edit("**Processando upload...**")
    except Exception:
        pass
    body = {
        "name": file_name,
        "description": "Carregado do Telegram usando PurpleBot.",
        "mimeType": mimeType,
    }
    try:
        len(parent_Id)
    except NameError:
        # Fallback to G_DRIVE_FOLDER_ID else root dir
        if G_DRIVE_FOLDER_ID is not None:
            body["parents"] = [G_DRIVE_FOLDER_ID]
    else:
        # Override G_DRIVE_FOLDER_ID because parent_Id not empty
        body["parents"] = [parent_Id]
    media_body = MediaFileUpload(file_path, mimetype=mimeType, resumable=True)
    # Start upload process
    file = service.files().create(
        body=body,
        media_body=media_body,
        fields="id, size, webContentLink",
        supportsAllDrives=True,
    )
    global is_cancelled
    current_time = time.time()
    response = None
    display_message = None
    is_cancelled = False
    while response is None:
        if is_cancelled:
            raise CancelProcess

        status, response = file.next_chunk()
        if status:
            file_size = status.total_size
            diff = time.time() - current_time
            uploaded = status.resumable_progress
            percentage = uploaded / file_size * 100
            speed = round(uploaded / diff, 2)
            eta = round((file_size - uploaded) / speed)
            prog_str = "**Enviando:** `[{}{}]` **{}%**".format(
                "".join("●" for _ in range(math.floor(percentage / 10))),
                "".join("○" for _ in range(10 - math.floor(percentage / 10))),
                round(percentage, 2),
            )

            current_message = (
                "**GDrive - Upload**\n\n"
                f"`{file_name}`\n"
                f"{prog_str}\n"
                f"{humanbytes(uploaded)} de {humanbytes(file_size)} "
                f"@ {humanbytes(speed)}\n"
                f"**Tempo estimado:** {time_formatter(eta)}"
            )
            if (
                round(diff % 15.00) == 0
                and (display_message != current_message)
                or (uploaded == file_size)
            ):
                await gdrive.edit(current_message)
                display_message = current_message
    file_id = response.get("id")
    file_size = response.get("size")
    downloadURL = response.get("webContentLink")
    # Change permission
    await change_permission(service, file_id)
    return int(file_size), downloadURL


async def task_directory(gdrive, service, folder_path):
    global parent_Id
    global is_cancelled
    is_cancelled = False
    lists = os.listdir(folder_path)
    if len(lists) == 0:
        return parent_Id
    root_parent_Id = None
    for f in lists:
        if is_cancelled:
            raise CancelProcess

        current_f_name = join(folder_path, f)
        if isdir(current_f_name):
            folder = await create_dir(service, f)
            parent_Id = folder.get("id")
            root_parent_Id = await task_directory(gdrive, service, current_f_name)
        else:
            file_name = await get_raw_name(current_f_name)
            mimeType = await get_mimeType(current_f_name)
            await upload(gdrive, service, current_f_name, file_name, mimeType)
            root_parent_Id = parent_Id
    return root_parent_Id


async def reset_parentId():
    global parent_Id
    try:
        len(parent_Id)
    except NameError:
        if G_DRIVE_FOLDER_ID is not None:
            parent_Id = G_DRIVE_FOLDER_ID
    else:
        del parent_Id
    return


@register(pattern=r"^\.gdlist(?: |$)(-l \d+)?(?: |$)?(.*)?(?: |$)", outgoing=True)
async def lists(gdrive):
    await gdrive.edit("**Obtendo informações...**")
    checker = gdrive.pattern_match.group(1)
    if checker is not None:
        page_size = int(gdrive.pattern_match.group(1).strip("-l "))
        if page_size > 1000:
            await gdrive.edit("**Erro: a lista excede o limite máximo.**")
            return
    else:
        page_size = 25  # default page_size is 25
    checker = gdrive.pattern_match.group(2)
    if checker != "":
        if checker.startswith("-p"):
            parents = checker.split(None, 2)[1]
            try:
                name = checker.split(None, 2)[2]
            except IndexError:
                query = f"'{parents}' in parents and (name contains '*')"
            else:
                query = f"'{parents}' in parents and (name contains '{name}')"
        else:
            if re.search("-p (.*)", checker):
                parents = re.search("-p (.*)", checker).group(1)
                name = checker.split("-p")[0].strip()
                query = f"'{parents}' in parents and (name contains '{name}')"
            else:
                name = checker
                query = f"name contains '{name}'"
    else:
        query = ""
    service = await create_app(gdrive)
    if service is False:
        return False
    fields = (
        "nextPageToken, files(name, size, id, " "mimeType, webViewLink, webContentLink)"
    )
    page_token = None
    result = []
    while True:
        try:
            response = (
                service.files()
                .list(
                    supportsAllDrives=True,
                    includeTeamDriveItems=True,
                    q=query,
                    spaces="drive",
                    corpora="allDrives",
                    fields=fields,
                    pageSize=page_size,
                    orderBy="modifiedTime desc, folder",
                    pageToken=page_token,
                )
                .execute()
            )
        except HttpError as e:
            await gdrive.edit(f"Error: {str(e)}")
            return
        for files in response.get("files", []):
            if len(result) >= page_size:
                break

            file_name = files.get("name")
            file_size = files.get("size", 0)
            message_folders = ""
            message_files = ""

            if files.get("mimeType") == "application/vnd.google-apps.folder":
                link = files.get("webViewLink")
                message_folders += f"• [{file_name}]({link})\n"
            else:
                link = files.get("webContentLink")
                message_files += (
                    f"• [{file_name}]({link}) (__{humanbytes(int(file_size))}__)\n"
                )

            result.append(files)
        if len(result) >= page_size:
            break

        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break

    del result
    if query == "":
        query = "Not specified"

    message = ""
    if message_folders:
        message += f"**Pastas:**\n\n{message_folders}\n"
    if message_files:
        message += f"**Arquivos:**\n\n{files}"

    if len(message) > 4096:
        await gdrive.edit("**O resultado é muito grande, enviando como arquivo...**")
        with open("result.txt", "w") as r:
            r.write(f"Consulta do Google Drive:\n{query}\n\nResultados\n\n{message}")
        await gdrive.client.send_file(
            gdrive.chat_id, "result.txt", caption="Lista de consulta do Google Drive."
        )
    else:
        await gdrive.edit(
            "**Consulta do Google Drive**:\n" f"`{query}`\n\n**Resultados:**\n\n{message}"
        )
    return


@register(pattern=r"^\.gdf (mkdir|rm|chck) (.*)", outgoing=True)
async def google_drive_managers(gdrive):
    """ - Google Drive folder/file management - """
    await gdrive.edit("**Enviando informações...**")
    service = await create_app(gdrive)
    if service is False:
        return None
    # Split name if contains spaces by using ;
    f_name = gdrive.pattern_match.group(2).split(";")
    exe = gdrive.pattern_match.group(1)
    for name_or_id in f_name:
        # in case given name has a space beetween ;
        name_or_id = name_or_id.strip()
        metadata = {
            "name": name_or_id,
            "mimeType": "application/vnd.google-apps.folder",
        }
        try:
            len(parent_Id)
        except NameError:
            # Fallback to G_DRIVE_FOLDER_ID else to root dir
            if G_DRIVE_FOLDER_ID is not None:
                metadata["parents"] = [G_DRIVE_FOLDER_ID]
        else:
            # Override G_DRIVE_FOLDER_ID because parent_Id not empty
            metadata["parents"] = [parent_Id]
        page_token = None
        result = (
            service.files()
            .list(
                q=f'name="{name_or_id}"',
                spaces="drive",
                fields=(
                    "nextPageToken, files(parents, name, id, size, "
                    "mimeType, webViewLink, webContentLink, description)"
                ),
                supportsAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        if exe == "mkdir":
            # Create a directory, abort if exist when parent not given
            status = "**Pasta já existe.**"
            try:
                folder = result.get("files", [])[0]
            except IndexError:
                folder = await create_dir(service, name_or_id)
                status = "**Pasta criada.**"
            folder_id = folder.get("id")
            webViewURL = folder.get("webViewLink")
            if "Created" in status:
                # Change permission
                await change_permission(service, folder_id)
            reply = (
                "**GDrive**\n\n"
                f"{status}\n"
                f"`{name_or_id}`\n"
                f"**ID:** `{folder_id}`\n"
                f"**Link:** [Aqui]({webViewURL})\n\n"
            )
        elif exe == "rm":
            # Permanently delete, skipping the trash
            try:
                # Try if given value is a name not a folderId/fileId
                f = result.get("files", [])[0]
                f_id = f.get("id")
            except IndexError:
                # If failed assumming value is folderId/fileId
                f_id = name_or_id
                if "http://" in name_or_id or "https://" in name_or_id:
                    if "id=" in name_or_id:
                        f_id = name_or_id.split("id=")[1]
                        f_id = re.split("[? &]", f_id)[0]
                    elif "folders/" in name_or_id:
                        f_id = name_or_id.split("folders/")[1]
                        f_id = re.split("[? &]", f_id)[0]
                    elif "/view" in name_or_id:
                        f_id = name_or_id.split("/")[-2]
                try:
                    f = await get_information(service, f_id)
                except Exception as e:
                    reply = f"**Erro:** `{str(e)}`\n"
                    continue
            name = f.get("name")
            mimeType = f.get("mimeType")
            if mimeType == "application/vnd.google-apps.folder":
                status = "**Pasta excluída.**"
            else:
                status = "**Arquivo excluído.**"
            try:
                service.files().delete(fileId=f_id, supportsAllDrives=True).execute()
            except HttpError as e:
                reply = f"**Erro:** {str(e)}\n"
                continue
            else:
                reply = "**GDrive**\n\n" f"{status}\n" f"`{name}`"
        elif exe == "chck":
            # Check file/folder if exists
            try:
                f = result.get("files", [])[0]
            except IndexError:
                # If failed assumming value is folderId/fileId
                f_id = name_or_id
                try:
                    f = await get_information(service, f_id)
                except Exception as e:
                    reply = f"**Erro:** `{str(e)}`"
                    continue
            # If exists parse file/folder information
            name_or_id = f.get("name")  # override input value
            f_id = f.get("id")
            f_size = f.get("size")
            mimeType = f.get("mimeType")
            webViewLink = f.get("webViewLink")
            downloadURL = f.get("webContentLink")
            description = f.get("description")
            if mimeType == "application/vnd.google-apps.folder":
                status = "**Pasta existe.**"
            else:
                status = "**o arquivo existe.**"
            reply = "**GDrive**\n\n" f"**Nome**: `{name_or_id}`\n" f"**ID:** `{f_id}`\n"
            if mimeType != "application/vnd.google-apps.folder":
                reply += f"**Tamanho:** `{humanbytes(f_size)}`\n"
                reply += f"**Link:** [{name_or_id}]({downloadURL})\n\n"
            else:
                reply += f"**URL:** [Aqui]({webViewLink})\n\n"
            if description:
                reply += f"**Sobre:**\n{description}\n\n"
        page_token = result.get("nextPageToken", None)
    await gdrive.edit(reply)
    return


@register(pattern=r"^\.gdabort(?: |$)", outgoing=True)
async def cancel_process(gdrive):
    """
    Abort process for download and upload
    """
    global is_cancelled
    downloads = aria2.get_downloads()
    await gdrive.edit("**Cancelando...**")
    if len(downloads) != 0:
        aria2.remove_all(force=True)
        aria2.autopurge()
    is_cancelled = True
    await asyncio.sleep(3.5)
    await gdrive.delete()


@register(pattern=r"^\.gd(?: |$)(.*)", outgoing=True)
async def google_drive(gdrive):
    # Parsing all google drive function
    value = gdrive.pattern_match.group(1)
    file_path = None
    uri = None
    if not value and not gdrive.reply_to_msg_id:
        return None
    if value and gdrive.reply_to_msg_id:
        await gdrive.edit(
            "**Erro: É para fazer o upload do arquivo ou a mensagem/mídia respondida?**"
        )
        return None
    service = await create_app(gdrive)
    if service is False:
        return None
    if isfile(value):
        file_path = value
        if file_path.endswith(".torrent"):
            uri = [file_path]
            file_path = None
    elif isdir(value):
        folder_path = value
        global parent_Id
        folder_name = await get_raw_name(folder_path)
        folder = await create_dir(service, folder_name)
        parent_Id = folder.get("id")
        webViewURL = "https://drive.google.com/drive/folders/" + parent_Id
        try:
            await task_directory(gdrive, service, folder_path)
        except CancelProcess:
            await gdrive.respond(
                "**GDrive - Upload de pasta**\n\n" "**Status:** Cancelado."
            )
            await reset_parentId()
            await gdrive.delete()
            return True
        except Exception as e:
            await gdrive.edit(f"**Erro:** `{str(e)}`")
            await reset_parentId()
            return False
        else:
            folder_size = await count_dir_size(service, parent_Id)
            msg = f"**GDrive - Upload de pasta**\n\n[{folder_name}]({webViewURL})"
            msg += f"\n**Tamanho:** {humanbytes(folder_size)}"
            if G_DRIVE_INDEX_URL:
                index_url = (
                    G_DRIVE_INDEX_URL.rstrip("/") + "/" + quote(folder_name) + "/"
                )
                msg += f"\n[URL da índice]({index_url})"
            await gdrive.edit(msg, link_preview=False)
            await reset_parentId()
            return True
    elif not value and gdrive.reply_to_msg_id:
        reply = str(await download(gdrive, service))
        await gdrive.respond(reply)
        await gdrive.delete()
        return None
    else:
        if re.findall(r"\bhttps?://drive\.google\.com\S+", value):
            # Link is google drive fallback to download
            value = re.findall(r"\bhttps?://drive\.google\.com\S+", value)
            for uri in value:
                try:
                    reply = await download_gdrive(gdrive, service, uri)
                except CancelProcess:
                    reply = "**GDrive - Baixar arquivo**\n\n" "**Status:** Cancelado."
                    break
                except Exception as e:
                    reply = f"**Erro:** `{str(e)}`"
                    continue
            if not reply:
                return None
            await gdrive.respond(reply, link_preview=False)
            await gdrive.delete()
            return True
        if re.findall(r"\bhttps?://.*\.\S+", value) or "magnet:?" in value:
            uri = value.split()
        else:
            for fileId in value.split():
                one = any(map(str.isdigit, fileId))
                two = bool("-" in fileId or "_" in fileId)
                if True in [one or two]:
                    try:
                        reply = await download_gdrive(gdrive, service, fileId)
                    except CancelProcess:
                        reply = "**GDrive - Baixar arquivo**\n\n**Status:** Cancelado."
                        break
                    except Exception as e:
                        reply = f"**Erro:** `{str(e)}`"
                        continue
            if not reply:
                return None
            await gdrive.respond(reply, link_preview=False)
            await gdrive.delete()
            return True
        if not uri and not gdrive.reply_to_msg_id:
            await gdrive.edit(
                "**Erro:** URL/caminho inválido.\n"
                "Se você acha que isso está errado, talvez você tenha usado .gd com múltiplos "
                "caminhos - ex: `.gd <nomedoarquivo1> <nomedoarquivo2>` que não é suportado."
            )
            return False
    if uri and not gdrive.reply_to_msg_id:
        for dl in uri:
            try:
                reply = await download(gdrive, service, dl)
            except Exception as e:
                if " not found" in str(e) or "'file'" in str(e):
                    reply = "**GDrive - Baixar arquivo**\n\n" "**Status:** Cancelado."
                    await asyncio.sleep(2.5)
                    break
                # if something bad happened, continue to next uri
                reply = f"**Erro:**\n`{str(e)}`\n`{dl}`"
                continue
        await gdrive.respond(reply, link_preview=False)
        await gdrive.delete()
        return None
    mimeType = await get_mimeType(file_path)
    file_name = await get_raw_name(file_path)
    try:
        result = await upload(gdrive, service, file_path, file_name, mimeType)
    except CancelProcess:
        gdrive.respond("**GDrive - Upload de arquivo**\n\n**Status:** Cancelado.")
    if result:
        msg = f"**GDrive - Upload de arquivo**\n\n[{file_name}]({result[1]})"
        msg += f"\n**Tamanho:** {humanbytes(result[0])}__"
        if G_DRIVE_INDEX_URL:
            index_url = G_DRIVE_INDEX_URL.rstrip("/") + "/" + quote(file_name)
            msg += f"\n[URL de índice]({index_url})"
        await gdrive.respond(msg, link_preview=False)
    await gdrive.delete()
    return


@register(pattern=r"^\.gdfset (put|rm)(?: |$)(.*)", outgoing=True)
async def set_upload_folder(gdrive):
    """ - Set parents dir for upload/check/makedir/remove - """
    await gdrive.edit("**Enviando informações...**")
    global parent_Id
    exe = gdrive.pattern_match.group(1)
    if exe == "rm":
        if G_DRIVE_FOLDER_ID is not None:
            parent_Id = G_DRIVE_FOLDER_ID
            await gdrive.edit("**G_DRIVE_FOLDER_ID será usado.**")
            return None
        try:
            del parent_Id
        except NameError:
            await gdrive.edit("**Erro: ID da raíz não configurado.**")
            return False
        else:
            await gdrive.edit("**Será usado o diretório padrão.**")
            return None
    inp = gdrive.pattern_match.group(2)
    if not inp:
        await gdrive.edit(">`.gdfset put <pastaURL/pastaID>`")
        return None
    # Value for .gdfset (put|rm) can be folderId or folder link
    try:
        ext_id = re.findall(r"\bhttps?://drive\.google\.com\S+", inp)[0]
    except IndexError:
        # if given value isn't folderURL assume it's an Id
        c1 = any(map(str.isdigit, inp))
        c2 = bool("-" in inp or "_" in inp)
        if True in [c1 or c2]:
            parent_Id = inp
            await gdrive.edit("**Alterado com sucesso.**")
            return None
        await gdrive.edit("**Alterando a força...**")
        parent_Id = inp
    else:
        if "uc?id=" in ext_id:
            await gdrive.edit("**Erro: Não é um URL válido.**")
            return None
        try:
            parent_Id = ext_id.split("folders/")[1]
        except IndexError:
            # Try catch again if URL open?id=
            try:
                parent_Id = ext_id.split("open?id=")[1]
            except IndexError:
                if "/view" in ext_id:
                    parent_Id = ext_id.split("/")[-2]
                else:
                    try:
                        parent_Id = ext_id.split("folderview?id=")[1]
                    except IndexError:
                        await gdrive.edit("**Erro: Não é um URL válido.**")
                        return None
        await gdrive.edit("**Alterado com sucesso.**")
    return


async def check_progress_for_dl(gdrive, gid, previous):
    complete = None
    global is_cancelled
    global filenames
    is_cancelled = False
    while not complete:
        if is_cancelled:
            raise CancelProcess

        file = aria2.get_download(gid)
        complete = file.is_complete
        try:
            filenames = file.name
        except IndexError:
            pass
        try:
            if not complete and not file.error_message:
                percentage = int(file.progress)
                downloaded = percentage * int(file.total_length) / 100
                prog_str = "**Baixando:** `[{}{}]` **{}**".format(
                    "".join("●" for _ in range(math.floor(percentage / 10))),
                    "".join("○" for _ in range(10 - math.floor(percentage / 10))),
                    file.progress_string(),
                )

                msg = (
                    "**URI - Download**\n\n"
                    f"`{file.name}`\n"
                    f"**Status:** {file.status.capitalize()}\n"
                    f"{prog_str}\n"
                    f"{humanbytes(downloaded)} de"
                    f" {file.total_length_string()}"
                    f" @ {file.download_speed_string()}\n"
                    f"**Tempo estimado:** {file.eta_string()}"
                )
                if msg != previous or downloaded == file.total_length_string():
                    await gdrive.edit(msg)
                    msg = previous
            else:
                await gdrive.edit(f"`{msg}`")
            await asyncio.sleep(15)
            await check_progress_for_dl(gdrive, gid, previous)
            file = aria2.get_download(gid)
            complete = file.is_complete
            if complete:
                await gdrive.edit(f"**Baixado com sucesso.**\n\n`{file.name}`")
                return True
        except Exception as e:
            if " depth exceeded" in str(e):
                file.remove(force=True)
                try:
                    await gdrive.edit(
                        "**URI - Download**\n\n"
                        f"`{file.name}`\n"
                        "**Status:** URI/Torrent não encontrado."
                    )
                except Exception:
                    pass


async def list_drive_dir(service, file_id: str) -> list:
    query = f"'{file_id}' in parents and (name contains '*')"
    fields = "nextPageToken, files(id, name, mimeType, size)"
    page_token = None
    page_size = 100
    files = []
    while True:
        response = (
            service.files()
            .list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                q=query,
                spaces="drive",
                fields=fields,
                pageToken=page_token,
                pageSize=page_size,
                corpora="allDrives",
                orderBy="folder, name",
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break
    return files


async def create_folder(service, folder_name: str, parent_id: str) -> str:
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id is not None:
        metadata["parents"] = [parent_id]
    folder = (
        service.files()
        .create(body=metadata, fields="id", supportsAllDrives=True)
        .execute()
    )
    return folder["id"]


async def copy_file(service, file_id: str, parent_id: str) -> str:
    body = {}
    if parent_id:
        body["parents"] = [parent_id]
    drive_file = (
        service.files()
        .copy(body=body, fileId=file_id, supportsTeamDrives=True)
        .execute()
    )
    return drive_file["id"]


async def copy_dir(service, file_id: str, parent_id: str) -> str:
    files = await list_drive_dir(service, file_id)
    if len(files) == 0:
        return parent_id
    new_id = None
    for file_ in files:
        if file_["mimeType"] == G_DRIVE_DIR_MIME_TYPE:
            dir_id = await create_folder(service, file_["name"], parent_id)
            new_id = await copy_dir(service, file_["id"], dir_id)
        else:
            await copy_file(service, file_["id"], parent_id)
            await asyncio.sleep(0.5)  # due to user rate limits
            new_id = parent_id
    return new_id


async def count_dir_size(service, file_id: str) -> int:
    _size = 0
    files = await list_drive_dir(service, file_id)
    for _file in files:
        try:
            if _file.get("mimeType") == G_DRIVE_DIR_MIME_TYPE:
                dir_id = _file.get("id")
                _size += int(await count_dir_size(service, dir_id))
            else:
                _size += int(_file.get("size"))
        except TypeError:
            pass
    return _size


@register(outgoing=True, pattern=r"^\.gcl(?: |$)(.*)")
async def gdrive_clone(event):
    service = await create_app(event)
    if service is False:
        return None
    input_str = event.pattern_match.group(1)
    if not input_str:
        return await event.edit("**O que devo clonar?**")
    _file_id = input_str
    await event.edit("**Processando...**")
    if "https://" or "http://" in input_str:
        if "id=" in input_str:
            _file_id = input_str.split("id=")[1]
            _file_id = re.split("[? &]", _file_id)[0]
        elif "folders/" in input_str:
            _file_id = input_str.split("folders/")[1]
            _file_id = re.split("[? &]", _file_id)[0]
        elif "/view" in input_str:
            _file_id = input_str.split("/")[-2]
    try:
        await get_information(service, _file_id)
    except BaseException as gd_e:
        return await event.edit(f"**Erro:** `{gd_e}`")
    _drive_file = await get_information(service, _file_id)
    if _drive_file["mimeType"] == G_DRIVE_DIR_MIME_TYPE:
        dir_id = await create_folder(service, _drive_file["name"], G_DRIVE_FOLDER_ID)
        await copy_dir(service, _file_id, dir_id)
        ret_id = dir_id
    else:
        ret_id = await copy_file(service, _file_id, G_DRIVE_FOLDER_ID)
    _drive_meta = await get_information(service, ret_id)
    _name = _drive_meta.get("name")
    if _drive_meta.get("mimeType") == G_DRIVE_DIR_MIME_TYPE:
        _link = _drive_meta.get("webViewLink")
        _size = await count_dir_size(service, _drive_meta.get("id"))
        _type = "folder"
    else:
        _link = _drive_meta.get("webContentLink")
        _size = _drive_meta.get("size", 0)
        _type = "file"
    msg = ""
    drive_link = f"[{_name}]({_link})"
    msg += f"**GDrive - Clone {_type}**\n\n{drive_link}"
    msg += f"\n**Tamanho:** {humanbytes(int(_size))}"
    if G_DRIVE_INDEX_URL:
        index_url = G_DRIVE_INDEX_URL.rstrip("/") + "/" + quote(_name)
        if _drive_meta.get("mimeType") == G_DRIVE_DIR_MIME_TYPE:
            index_url += "/"
        msg += f"\n[URL de índice]({index_url})"
    await event.edit(msg)


CMD_HELP.update(
    {
        "gdrive": ">`.gdauth`"
        "\n**Uso**: Gera o token de autenticação GDrive."
        "\nIsso precisa ser feito apenas uma vez."
        "\n\n>`.gdreset`"
        "\n**Uso**: Redefine seu token de autenticação."
        "\n\n>`.gd`"
        "\n**Uso**: Upload de arquivo local ou URI/URL/drivelink para o GDrive."
        "\npara drivelink, só faz o upload se você quiser."
        "\n\n>`.gdabort`"
        "\n**Uso**: Aborta processos GDrive em execução."
        "\n\n>`.gdlist`"
        "\n**Uso**: Obtém uma lista de pastas e arquivos. (o tamanho padrão é 50)"
        "\nUse as flags `-l range[1-1000]` para limitar os resultados."
        "\nUse as flags `-p parents-folder_id` para listas de pastas fornecidas no GDrive."
        "\n\n>`.gdf mkdir`"
        "\n**Uso**: Cria uma pasta GDrive."
        "\n\n>`.gdf chck`"
        "\n**Uso**: Verifique se o arquivo/pasta existe no GDrive."
        "\n\n>`.gdf rm`"
        "\n**Uso**: Exclua arquivos/pastas no GDrive."
        "\nNão pode ser desfeito, use com cuidado."
        "\n\n>`.gdfset put`"
        "\n**Uso**: Altera o diretório de upload no GDrive."
        "\n\n>`.gdfset rm`"
        "\n**Uso**: Reseta o ID da pasta de envio."
        "\n\n>`.gdfset put`"
        "\n**Uso**: Carrega arquivos/pastas para `G_DRIVE_FOLDER_ID`. Se estiver vazio, faz upload para o diretório raíz."
        "\n\n>`.gcl <Link público do GDrive/GDrive ID>`"
        "\n**Uso**: Copia o arquivo ou pasta em seu GDrive"
        "\n\n**NOTA:**"
        "\nPara >`.gdlist` você pode combinar -l e -p flags com ou sem nome "
        "ao mesmo tempo, `-l` flag deve ser primeiro seguido por `-p`."
        "\nPor padrão, lista os mais recentes 'modifiedTime' e depois pastas."
    }
)
