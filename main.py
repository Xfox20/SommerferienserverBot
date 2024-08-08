from datetime import datetime
import requests
import json
import os
import hashlib
from mcstatus import JavaServer

jsonEncoder = json.encoder.JSONEncoder()
jsonDecoder = json.decoder.JSONDecoder()

# API request

serverAddress = os.getenv("SERVER_ADDRESS")
status = JavaServer.lookup(serverAddress).status()

playerList = status.players.sample
with open("playerStatuses.json", "a+") as playerStatusesFile:
    playerStatusesFile.seek(0)
    content = playerStatusesFile.read()
    playerStatuses = jsonDecoder.decode(content) if content else {}

    if not playerList:
        playerStatuses.clear()
    else:
        currentTime = datetime.now().isoformat()

        for playerName in list(playerStatuses.keys()):
            if playerName not in playerList:
                del playerStatuses[playerName]

        for player in playerList:
            if player.name not in playerStatuses:
                playerStatuses[player.name] = currentTime

with open("playerStatuses.json", "w") as playerStatusesFile:
    playerStatusesFile.write(jsonEncoder.encode(playerStatuses))

motd = status.motd.to_plain()
playerOnlineCount = status.players.online

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
    "title": playerName,
    "image": {
        "url": f"https://minotar.net/helm/{playerName}/30"
    },
    "color": int(hashlib.md5(playerName.encode()).hexdigest()[:6], 16),
    "footer": {
        "text": f"online since {datetime.fromisoformat(playerStatuses[playerName]).strftime("%H:%M")}"
    }
} for playerName in playerStatuses]

message["embeds"].extend(playerEmbeds)

headers = {
    "Content-Type": "application/json"
}

requests.request(webhookMethod, webhookUrl, data=jsonEncoder.encode(message), headers=headers)
