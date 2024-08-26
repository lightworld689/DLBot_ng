import asyncio
import websockets
import json
import os
import tkinter as tk
from tkinter import scrolledtext
import threading
import time

if not os.path.exists("log_status.txt"):
    with open("log_status.txt", "w", encoding="utf-8") as status_file:
        status_file.write("0")

with open("log_status.txt", "r+", encoding="utf-8") as status_file:
    status = status_file.read()
    status_file.seek(0)
    status_file.write("0")

async def join_channel(nick, password, channel):
    uri = "wss://hack.chat/chat-ws"
    full_nick = f"{nick}#{password}"

    def log_message(type, message):
        if not os.path.exists("log_status.txt"):
            with open("log_status.txt", "w", encoding="utf-8") as status_file:
                status_file.write("0")

        with open("log_status.txt", "r+", encoding="utf-8") as status_file:
            status = status_file.read()
            if status == "0":
                if not os.path.exists("log.log"):
                    open("log.log", "w", encoding="utf-8").close()
                if not os.path.exists("msg.log"):
                    open("msg.log", "w", encoding="utf-8").close()
                with open("log.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f"----------------- {time.strftime('%Y-%m-%d %H:%M:%S')} -----------------\n")
                with open("msg.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f"----------------- {time.strftime('%Y-%m-%d %H:%M:%S')} -----------------\n")
                status_file.seek(0)
                status_file.write("1")

        with open("log.log", "a", encoding="utf-8") as log_file:
            log_entry = f"{type}：{message}\n"
            log_file.write(log_entry)
            print(log_entry, end="")
        
        if type == "收到消息":
            message_json = json.loads(message)
            if message_json.get("cmd") == "chat":
                msg_entry = f"[{message_json.get('trip', '')}]{message_json.get('nick', '')}：{message_json.get('text', '')}\n"
            elif message_json.get("cmd") == "info":
                msg_entry = f"系统消息：{message_json.get('text', '')}\n"
            else:
                return
            
            with open("msg.log", "a", encoding="utf-8") as msg_file:
                msg_file.write(msg_entry)
    
    while True:
        async with websockets.connect(uri) as websocket:
            join_message = {"cmd": "join", "channel": channel, "nick": full_nick}
            await websocket.send(json.dumps(join_message))
            log_message("系统日志", f"Joined channel {channel} as {nick}")

            while True:
                response = await websocket.recv()
                log_message("收到消息", response)
                message = json.loads(response)
                
                if message.get("cmd") == "warn" and "You are joining channels too fast. Wait a moment and try again." in message.get("text", ""):
                    for i in range(60, 0, -1):
                        log_message("系统日志", f"Joining too fast, waiting for {i} seconds...")
                        await asyncio.sleep(1)
                    break
                
                if message.get("cmd") == "warn" and "Nickname taken" in message.get("text", ""):
                    log_message("系统日志", "Nickname taken, modifying nickname and retrying...")
                    if "#" in full_nick:
                        full_nick = full_nick.replace("#", "_#", 1)
                    else:
                        full_nick += "_"
                    break
                
                if message.get("cmd") == "onlineSet":
                    startup_message = {"cmd": "chat", "text": "DLBot，启动成功。", "customId": "0"}
                    await websocket.send(json.dumps(startup_message))
                    log_message("发送消息", json.dumps(startup_message))
                
                if message.get("cmd") == "info" and message.get("type") == "whisper":
                    trip = message.get("trip")
                    if trip in ["vuPizP", "7Ty7y9"]:
                        text = message.get("text")
                        if text and "whispered: /chat " in text:
                            msg = text.split("whispered: /chat ", 1)[1]
                            chat_message = {"cmd": "chat", "text": msg, "customId": "0"}
                            await websocket.send(json.dumps(chat_message))
                            log_message("发送消息", json.dumps(chat_message))
                


if os.path.exists("user.txt"):
    with open("user.txt", "r", encoding="utf-8") as user_file:
        lines = user_file.readlines()
        nick = lines[0].strip()
        password = lines[1].strip()
        channel = lines[2].strip()

    asyncio.run(join_channel(nick, password, channel))
else:
    print("Error: 'user.txt' file not found. Please ensure the file exists.")
