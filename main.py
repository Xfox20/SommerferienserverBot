import hashlib
import json
import os
from datetime import datetime

import requests
from mcstatus import JavaServer
from mcstatus.status_response import JavaStatusResponse, JavaStatusPlayer

jsonEncoder = json.encoder.JSONEncoder()
jsonDecoder = json.decoder.JSONDecoder()

currentTime = datetime.now()


def get_server_status(address: str) -> JavaStatusResponse:
    try:
        server_status = JavaServer.lookup(address).status()
        if server_status.players.sample:
            server_status.players.sample.sort(key=lambda p: p.name)
            server_status.players.sample = [p for p in server_status.players.sample
                                            if p.name != "Anonymous Player"]
    except TimeoutError:
        server_status = None
    return server_status


def sync_player_status_cache(player_list: list[JavaStatusPlayer]):
    player_statuses = get_player_status_cache()
    if player_list:
        player_list = [p.name for p in player_list]

        for player_name in list(player_statuses):
            if player_name not in player_list:
                del player_statuses[player_name]

        for player_name in player_list:
            if player_name not in player_statuses:
                player_statuses[player_name] = currentTime.isoformat()
    else:
        player_statuses.clear()

    with open("playerStatuses.json", "w") as player_statuses_file:
        player_statuses_file.write(jsonEncoder.encode(player_statuses))

    return player_statuses


def get_player_status_cache() -> dict:
    with open("playerStatuses.json", "a+") as player_statuses_file:
        player_statuses_file.seek(0)
        content = player_statuses_file.read()
        player_statuses = jsonDecoder.decode(content) if content else {}

    return player_statuses


def send_message(server_status: JavaStatusResponse, player_status_cache: dict):
    webhook_url = os.getenv("WEBHOOK_URL")
    webhook_message_id = os.getenv("WEBHOOK_MESSAGE_ID")
    webhook_method = "POST"

    if webhook_message_id:
        webhook_method = "PATCH"
        webhook_url += f"/messages/{webhook_message_id}"

    headers = {"Content-Type": "application/json"}

    message = compose_discord_message(server_status, player_status_cache)

    requests.request(webhook_method, webhook_url, data=jsonEncoder.encode(message), headers=headers)


def compose_discord_message(server_status: JavaStatusResponse, player_status_cache: dict) -> dict:
    server_is_online = bool(server_status)

    embeds = [create_overview_embed(server_status)]

    if server_is_online and server_status.players.sample:
        player_embeds = [create_player_embed(
            player, datetime.fromisoformat(player_status_cache[player.name]))
            for player in server_status.players.sample]
        embeds.extend(player_embeds)

    return {
        "embeds": embeds
    }


def create_overview_embed(server_status: JavaStatusResponse) -> dict:
    footer = {
        "text": f"Last updated at {datetime.now().strftime("%H:%M:%S")}"
    }

    if server_status:
        embed = {
            "title": "Server Status",
            "description": f"```{server_status.motd.to_plain()}```\n"
                           f"**{server_status.players.online} player"
                           f"{"s" if not server_status.players.online == 1 else ""} online**",
            "color": 3332471,
            "footer": footer
        }
    else:
        embed = {
            "title": "Server Status",
            "description": f"**offline**",
            "color": 14500915,
            "footer": footer
        }

    return embed


def create_player_embed(player: JavaStatusPlayer, online_since: datetime) -> dict:
    return {
        "title": player.name,
        "image": {
            "url": f"https://minotar.net/helm/{player.name}/30"
        },
        "color": int(hashlib.md5(player.name.encode()).hexdigest()[:6], 16),
        "footer": {
            "text": f"online since {online_since.strftime("%H:%M")}"
        }
    }


if __name__ == "__main__":
    status = get_server_status(os.getenv("SERVER_ADDRESS"))
    cache = sync_player_status_cache(status.players.sample)\
        if status else get_player_status_cache()
    send_message(status, cache)
