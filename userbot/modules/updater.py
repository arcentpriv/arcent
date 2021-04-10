# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
# credits to @AvinashReddy3108
#
"""
This module updates the userbot based on upstream revision
"""

import asyncio
import sys
from os import environ, execle, remove

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from userbot import (
    CMD_HELP,
    HEROKU_API_KEY,
    HEROKU_APP_NAME,
    UPSTREAM_REPO_BRANCH,
    UPSTREAM_REPO_URL,
)
from userbot.events import register


async def gen_chlog(repo, diff):
    d_form = "%d/%m/%y"
    return "".join(
        f"- {c.summary} ({c.committed_datetime.strftime(d_form)}) <{c.author}>\n"
        for c in repo.iter_commits(diff)
    )


async def print_changelogs(event, ac_br, changelog):
    changelog_str = (
        f"**Atualizações disponíveis para o PurpleBot !\n\nMudanças:**\n`{changelog}`"
    )
    if len(changelog_str) > 4096:
        await event.edit("**O registro de alterações é muito grande, enviando como um arquivo.**")
        with open("output.txt", "w+") as file:
            file.write(changelog_str)
        await event.client.send_file(event.chat_id, "output.txt")
        remove("output.txt")
    else:
        await event.client.send_message(event.chat_id, changelog_str)
    return True


async def deploy(event, repo, ups_rem, ac_br, txt):
    if HEROKU_API_KEY is not None:
        import heroku3

        heroku = heroku3.from_key(HEROKU_API_KEY)
        heroku_app = None
        heroku_applications = heroku.apps()
        if HEROKU_APP_NAME is None:
            await event.edit(
                "**Por favor, configure a varíavel** `HEROKU_APP_NAME` "
                " **para ser capaz de atualizar seu userbot.**"
            )
            repo.__del__()
            return
        for app in heroku_applications:
            if app.name == HEROKU_APP_NAME:
                heroku_app = app
                break
        if heroku_app is None:
            await event.edit(
                f"{txt}\n" "**Credenciais do Heroku inválidas para atualizar os dynos do userbot.**"
            )
            return repo.__del__()
        ups_rem.fetch(ac_br)
        repo.git.reset("--hard", "FETCH_HEAD")
        heroku_git_url = heroku_app.git_url.replace(
            "https://", "https://api:" + HEROKU_API_KEY + "@"
        )
        if "heroku" in repo.remotes:
            remote = repo.remote("heroku")
            remote.set_url(heroku_git_url)
        else:
            remote = repo.create_remote("heroku", heroku_git_url)
        try:
            remote.push(refspec="HEAD:refs/heads/master", force=True)
        except Exception as error:
            await event.edit(f"{txt}\nHere is the error log:\n`{error}`")
            return repo.__del__()
        build = app.builds(order_by="created_at", sort="desc")[0]
        if build.status == "failed":
            await event.edit("**Erro na atualização!**\nCancelada ou ocorreram alguns erros.`")
            await asyncio.sleep(5)
            return await event.delete()
        await event.edit(
            "**Atualizado com sucesso!**\nO bot está reiniciando, estará de volta em alguns segundos."
        )

        with open(".restartmsg", "w") as f:
            f.truncate(0)
            f.write(f"{event.chat_id}\n{event.id}\n")
    else:
        await event.edit("**Por favor configure a variável** `HEROKU_API_KEY` ")
    return


async def update(event, repo, ups_rem, ac_br):
    try:
        ups_rem.pull(ac_br)
    except GitCommandError:
        repo.git.reset("--hard", "FETCH_HEAD")
    await event.edit(
        "**Atualizado com sucesso!**\nO bot está reiniciando, estará de volta em alguns segundos."
    )

    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{event.chat_id}\n{event.id}\n")

    # Spin a new instance of bot
    args = [sys.executable, "-m", "userbot"]
    execle(sys.executable, *args, environ)


@register(outgoing=True, pattern=r"^\.update( now| deploy|$)")
async def upstream(event):
    "For .update command, check if the bot is up to date, update if specified"
    await event.edit("**Verificando atualizações, por favor aguarde...**")
    conf = event.pattern_match.group(1).strip()
    off_repo = UPSTREAM_REPO_URL
    force_update = False
    try:
        txt = "**Ops .. O atualizador não pode continuar devido a "
        txt += "alguns problemas**\n`LOGTRACE:`\n"
        repo = Repo()
    except NoSuchPathError as error:
        await event.edit(f"{txt}\n**Diretório** `{error}` **não foi encontrado.**")
        return repo.__del__()
    except GitCommandError as error:
        await event.edit(f"{txt}\n**Falha no início!** `{error}`")
        return repo.__del__()
    except InvalidGitRepositoryError as error:
        if conf is None:
            return await event.edit(
                f"**Infelizmente, o diretório {error} "
                "não parece ser um repositório git.\n"
                "Mas podemos consertar isso forçando a atualização do userbot usando **"
                "`.update now.`"
            )
        repo = Repo.init()
        origin = repo.create_remote("upstream", off_repo)
        origin.fetch()
        force_update = True
        repo.create_head("master", origin.refs.master)
        repo.heads.master.set_tracking_branch(origin.refs.master)
        repo.heads.master.checkout(True)

    ac_br = repo.active_branch.name
    if ac_br != UPSTREAM_REPO_BRANCH:
        await event.edit(
            f"**Parece que você está usando seu próprio branch personalizado: ({ac_br}). \n"
            "Por favor mude para** `master` "
        )
        return repo.__del__()
    try:
        repo.create_remote("upstream", off_repo)
    except BaseException:
        pass

    ups_rem = repo.remote("upstream")
    ups_rem.fetch(ac_br)

    changelog = await gen_chlog(repo, f"HEAD..upstream/{ac_br}")
    """ - Special case for deploy - """
    if conf == "deploy":
        await event.edit(
            "**Fazendo uma atualização completa...**\n__Isso geralmente leva menos de 5 minutos, aguarde.__"
        )
        await deploy(event, repo, ups_rem, ac_br, txt)
        return

    if changelog == "" and not force_update:
        await event.edit(
            f"Seu userbot está **atualizado** !"
        )
        return repo.__del__()

    if conf == "" and not force_update:
        await print_changelogs(event, ac_br, changelog)
        await event.delete()
        return await event.respond("**Use** `.update deploy` **para atualizar.**")

    if force_update:
        await event.edit(
            "**Forçando a sincronização com o código do userbot estável mais recente, aguarde...**"
        )

    if conf == "now":
        if changelog != "":
            for commit in changelog.splitlines():
                if commit.startswith("- [NQ]"):
                    return await event.edit(
                        "**A atualização rápida foi desativada para esta atualização; "
                        "use** `.update deploy` **em vez disso.**"
                    )
        await event.edit("**Fazendo uma atualização rápida, por favor aguarde...**")
        await update(event, repo, ups_rem, ac_br)

    return


CMD_HELP.update(
    {
        "update": ">`.update`"
        "\n**Uso:** Verifica se o repositório principal do userbot tem alguma atualização "
        "e mostra uma lista de mudanças caso haja alterações."
        "\n\n>`.update now`"
        "\n**Uso:** Executa uma atualização rápida."
        "\nO Heroku redefine as atualizações realizadas usando este método após um tempo. Use `deploy` em vez disso."
        "\n\n>`.update deploy`"
        "\n**Uso:** Executa uma atualização completa (recomendado)."
    }
)
