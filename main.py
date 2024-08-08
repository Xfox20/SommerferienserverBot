from datetime import datetime
import requests
import json
import os
import hashlib

jsonEncoder = json.encoder.JSONEncoder()
jsonDecoder = json.decoder.JSONDecoder()

# API request

serverAddress = os.getenv("SERVER_ADDRESS")
statusFetchUrl = f"https://api.mcsrvstat.us/3/{serverAddress}"
statusJson = jsonDecoder.decode(requests.request("GET", statusFetchUrl).text)

playerList = statusJson["players"]["list"] if "list" in statusJson["players"] else None
with open("playerStatuses.json", "a+") as playerStatusesFile:
    playerStatusesFile.seek(0)
    content = playerStatusesFile.read()
    playerStatuses = jsonDecoder.decode(content) if content else {}

    if not playerList:
        playerStatuses.clear()
    else:
        currentTime = datetime.now().isoformat()
        currentPlayers = set()

        for player in playerList:
            name = player["name"]
            currentPlayers.add(name)
            if name not in playerStatuses:
                playerStatuses[name] = currentTime

        for playerName in list(playerStatuses.keys()):
            if playerName not in currentPlayers:
                del playerStatuses[playerName]

with open("playerStatuses.json", "w") as playerStatusesFile:
    playerStatusesFile.write(jsonEncoder.encode(playerStatuses))

motd = "\n".join(statusJson["motd"]["clean"])
playerOnlineCount = statusJson["players"]["online"]

# Send Discord message

webhookUrl = os.getenv("WEBHOOK_URL")
webhookMessageId = os.getenv("WEBHOOK_MESSAGE_ID")
webhookMethod = "POST"

if webhookMessageId:
    webhookMethod = "PATCH"
    webhookUrl += f"/messages/{webhookMessageId}"

message = {
    "embeds": [
        {
            "title": "Server Status",
            "description": f"```{motd}```\n**{playerOnlineCount} player{"s" if (playerOnlineCount or 2) > 1 else ""} online**",
            "color": 3332471,
            "footer": {
                "text": f"Last updated at {datetime.now().strftime("%H:%M:%S")}"
            }
        }
    ]
}

playerEmbeds = [{
    "title": name,
    "image": {
        "url": f"https://minotar.net/helm/{name}/30"
    },
    "color": int(hashlib.md5(name.encode()).hexdigest()[:6], 16),
    "footer": {
        "text": f"online since {datetime.fromisoformat(playerStatuses[name]).strftime("%H:%M")}"
    }
} for name in playerStatuses]

message["embeds"].extend(playerEmbeds)

headers = {
    "Content-Type": "application/json"
}

requests.request(webhookMethod, webhookUrl, data=jsonEncoder.encode(message), headers=headers)
