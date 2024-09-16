import os
import json
import time
import asyncio
import websockets
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiohttp import web
import urllib.parse

# 全局变量用于存储WebSocket连接
websocket = None

if not os.path.exists("log_status.txt"):
    with open("log_status.txt", "w", encoding="utf-8") as status_file:
        status_file.write("0")

with open("log_status.txt", "r+", encoding="utf-8") as status_file:
    status = status_file.read()
    status_file.seek(0)
    status_file.write("0")

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

async def join_channel(nick, password, channel, ws_link):
    global websocket
    uri = ws_link
    full_nick = f"{nick}#{password}"
    
    async def send_color_message(websocket):
        while True:
            color = f"{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
            color_message = {"cmd": "chat", "text": f"/color #{color}", "customId": "0"}
            await websocket.send(json.dumps(color_message))
            log_message("发送消息", json.dumps(color_message))
            await asyncio.sleep(15)

    async def handle_messages(websocket):
        global send_color_task
        send_color_task = asyncio.create_task(send_color_message(websocket))
        initial_join_time = time.time()
        while True:
            try:
                response = await websocket.recv()
                log_message("收到消息", response)
                message = json.loads(response)
                
                if message.get("cmd") == "warn" and "You are joining channels too fast. Wait a moment and try again." in message.get("text", ""):
                    break

                if message.get("cmd") == "warn" and "You are being rate-limited or blocked." in message.get("text", ""):
                    break
                
                if message.get("cmd") == "warn" and "Nickname taken" in message.get("text", ""):
                    log_message("系统日志", "Nickname taken, modifying nickname and retrying...")
                    if "#" in full_nick:
                        full_nick = full_nick.replace("#", "_#", 1)
                    else:
                        full_nick += "_"
                    break
                
                if message.get("cmd") == "onlineSet":
                    startup_message = {"cmd": "chat", "text": "DLBot detected abnormal exit and successfully restarted", "customId": "0"}
                    await websocket.send(json.dumps(startup_message))
                    log_message("发送消息", json.dumps(startup_message))
                
                if message.get("cmd") == "info" and message.get("type") == "whisper":
                    trip = message.get("trip")
                    if trip in trustedusers:
                        text = message.get("text")
                        if text and "whispered: $chat " in text:
                            msg = text.split("whispered: $chat ", 1)[1]
                            chat_message = {"cmd": "chat", "text": msg, "customId": "0"}
                            await websocket.send(json.dumps(chat_message))
                            log_message("发送消息", json.dumps(chat_message))
                #if message.get("channel") not in [channel, "lounge"] and time.time() - initial_join_time > 10:
                if message.get("channel") in[channel]and message.get("channel")not in [channel] and time.time() - initial_join_time > 10:
                    log_message("系统日志", "Detected kick, attempting to rejoin...")
                    break

                if message.get("cmd") == "chat" and message.get("text", "").startswith("$chat "):
                    trip = message.get("trip")
                    if trip in trustedusers:
                        msg = message.get("text").split("$chat ", 1)[1]
                        whisper_message = {"cmd": "chat", "text": msg, "customId": "0"}
                        await websocket.send(json.dumps(whisper_message))
                        log_message("发送消息", json.dumps(whisper_message))
                
                if message.get("cmd") == "chat" and message.get("text") == "$help":
                    help_message = {
                        "cmd": "chat",
                        "text": """| 指令 | 用途 | 用法 | 需要的权限 |
| --- | --- | --- | --- |
| \\$help | 显示本页面 | \\$help | 无 |""",
                        "customId": "0"
                    }
                    await websocket.send(json.dumps(help_message))
                    log_message("发送消息", json.dumps(help_message))

                if message.get("cmd") == "chat" and message.get("text") == "$reload":
                    trip = message.get("trip")
                    if trip in trustedusers:
                        log_message("系统日志", "Trusted user initiated reload, reloading...")
                        try:
                            with open("main.py", "r", encoding="utf-8") as file:
                                code = file.read()
                            exec(code, globals())
                            success_message = {"cmd": "chat", "text": f"@{message.get('nick', 'Unknown')} 代码重载成功。", "customId": "0"}
                            await websocket.send(json.dumps(success_message))
                            log_message("发送消息", json.dumps(success_message))
                        except Exception as e:
                            error_message = {"cmd": "chat", "text": f"@{message.get('nick', 'Unknown')} 代码重载失败: {str(e)}", "customId": "0"}
                            await websocket.send(json.dumps(error_message))
                            log_message("发送消息", json.dumps(error_message))
                    else:
                        error_message = {"cmd": "chat", "text": f"@{message.get('nick', 'Unknown')} 你在干什么？你好像不是一个被信任的用户。", "customId": "0"}
                        await websocket.send(json.dumps(error_message))
                        log_message("发送消息", json.dumps(error_message))
            except websockets.ConnectionClosed:
                log_message("系统日志", "Connection lost, attempting to reconnect...")
                send_color_task.cancel()
                try:
                    await send_color_task
                except asyncio.CancelledError:
                    break

            if message.get("cmd") == "onlineAdd":
                log_message("系统日志", f"{message.get('nick', 'Unknown')}加入了聊天室")
                msg_entry = f"[{message.get('trip', '')}]{message.get('nick', 'Unknown')} 加入了聊天室\n"
                with open("msg.log", "a", encoding="utf-8") as msg_file:
                    msg_file.write(msg_entry)
            elif message.get("cmd") == "onlineRemove":
                log_message("系统日志", f"{message.get('nick', 'Unknown')}退出了聊天室")
                msg_entry = f"[{message.get('trip', '')}]{message.get('nick', 'Unknown')} 退出了聊天室\n"
                with open("msg.log", "a", encoding="utf-8") as msg_file:
                    msg_file.write(msg_entry)

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                join_message = {"cmd": "join", "channel": channel, "nick": full_nick}
                await websocket.send(json.dumps(join_message))
                log_message("系统日志", f"Joined channel {channel} as {nick}")
                await handle_messages(websocket)
        except (websockets.ConnectionClosed, websockets.InvalidHandshake, websockets.InvalidURI, OSError) as e:
            log_message("系统日志", f"Connection error: {e}, retrying in 5 seconds...")
            await asyncio.sleep(5)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/chat/'):
            message = self.path.split('/chat/')[1]
            global websocket
            if websocket:
                chat_message = {"cmd": "chat", "text": message, "customId": "0"}
                asyncio.run(websocket.send(json.dumps(chat_message)))
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Message sent"}).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "WebSocket connection not established"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Not found"}).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        global websocket
        if websocket:
            asyncio.run(websocket.send(json.dumps(data)))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "JSON message sent"}).encode('utf-8'))
        else:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "WebSocket connection not established"}).encode('utf-8'))

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_post('/send_message', handle_send_message)
    app.router.add_post('/send_json', handle_send_json)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 18896)
    await site.start()
    print(f"Starting server on http://0.0.0.0:18896")

async def handle_index(request):
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    return web.Response(text=content, content_type='text/html')

async def handle_send_message(request):
    data = await request.post()
    message = data['message']
    log_message("系统日志", f"Attempting to send message: {message}")
    success = await send_message(message)
    log_message("系统日志", f"Message sent successfully: {success}")
    return web.json_response({"success": success})

async def handle_send_json(request):
    global websocket
    data = await request.json()
    if websocket:
        await websocket.send(json.dumps(data))
        return web.json_response({"success": True})
    else:
        return web.json_response({"success": False, "error": "WebSocket not connected"})
async def handle_chat(request):
    query_params = request.query_string
    if query_params:
        # URL 解码
        decoded_message = urllib.parse.unquote(query_params)
        # 处理换行符
        decoded_message = decoded_message.replace('\\n', '\n')
    else:
        decoded_message = ""
    
    global websocket
    if websocket:
        chat_message = {"cmd": "chat", "text": decoded_message, "customId": "0"}
        await websocket.send(json.dumps(chat_message))
        return web.json_response({"status": "success", "message": "Message sent"})
    else:
        return web.json_response({"status": "error", "message": "WebSocket connection not established"}, status=500)

async def handle_post(request):
    data = await request.json()
    global websocket
    if websocket:
        if "text" in data:
            # 处理换行符
            data["text"] = data["text"].replace('\\n', '\n')
        await websocket.send(json.dumps(data))
        return web.json_response({"status": "success", "message": "JSON message sent"})
    else:
        return web.json_response({"status": "error", "message": "WebSocket connection not established"}, status=500)

async def send_message(message):
    global websocket
    if websocket:
        # 处理换行符
        message = message.replace('\\n', '\n')
        chat_message = {"cmd": "chat", "text": message, "customId": "0"}
        await websocket.send(json.dumps(chat_message))
        return True
    return False

if __name__ == '__main__':
    if os.path.exists("user.txt"):
        with open("user.txt", "r", encoding="utf-8") as user_file:
            lines = user_file.readlines()
            for line in lines:
                if line.startswith("username:"):
                    nick = line.replace("username:", "").strip()
                elif line.startswith("password:"):
                    password = line.replace("password:", "").strip()
                elif line.startswith("channel:"):
                    channel = line.replace("channel:", "").strip()
                elif line.startswith("trustedusers:"):
                    trustedusers = json.loads(line.replace("trustedusers:", "").strip())
                elif line.startswith("ws_link:"):
                    ws_link = line.replace("ws_link:", "").strip()
                if "ws_link" not in locals():
                    ws_link = "wss://hack.chat/chat-ws" # still have bug

        async def main():
            server_task = asyncio.create_task(start_server())
            join_task = asyncio.create_task(join_channel(nick, password, channel, ws_link))
            await join_task

        asyncio.run(main())
    else:
        print("Error: 'user.txt' file not found. Please ensure the file exists.")
