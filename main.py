import discord
from discord import app_commands
import os
import asyncio
import json
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# Flask keep alive
app = Flask('')
@app.route('/')
def home():
    return "✅ Bot is alive!"
def run_flask():
    app.run(host='0.0.0.0', port=8080)
Thread(target=run_flask, daemon=True).start()

# Bot setup
TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    print("❌ Missing TOKEN")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Simple encryption (thay thế cryptography)
import base64
def simple_encrypt(text, password):
    """Mã hóa đơn giản base64 + XOR"""
    encoded = base64.b64encode(text.encode()).decode()
    encrypted = ''.join(chr(ord(c) ^ ord(password[i % len(password)])) for i, c in enumerate(encoded))
    return base64.b64encode(encrypted.encode()).decode()

def simple_decrypt(encrypted_text, password):
    """Giải mã"""
    try:
        decoded = base64.b64decode(encrypted_text).decode()
        decrypted = ''.join(chr(ord(c) ^ ord(password[i % len(password)])) for i, c in enumerate(decoded))
        return base64.b64decode(decrypted).decode()
    except:
        return None

# Session storage
sessions = {}

@client.event
async def on_ready():
    print(f'✅ {client.user} is ready!')
    await tree.sync()
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/mahoa"))

# Slash command
@tree.command(name="mahoa", description="Mã hóa source code")
async def mahoa_slash(interaction: discord.Interaction):
    user_id = interaction.user.id
    sessions[user_id] = {'step': 'waiting_source', 'time': datetime.now()}
    
    embed = discord.Embed(title="🔐 MÃ HÓA SOURCE CODE", description="**Vui lòng gửi source code của bạn để tiến hành mã hóa**", color=0x5865F2)
    embed.add_field(name="📤 Cách gửi:", value="• Gửi code trực tiếp\n• Hoặc attach file (.txt, .py, .js, ...)", inline=False)
    await interaction.response.send_message(embed=embed)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Command !mahoa
    if message.content == '!mahoa':
        user_id = message.author.id
        sessions[user_id] = {'step': 'waiting_source', 'time': datetime.now()}
        await message.reply("🔐 **Vui lòng gửi source code của bạn để tiến hành mã hóa**")

    # Xử lý session
    elif message.author.id in sessions:
        user_id = message.author.id
        session = sessions[user_id]
        
        # Check timeout
        if datetime.now() - session['time'] > timedelta(minutes=5):
            del sessions[user_id]
            await message.reply("❌ Session hết hạn!")
            return

        if session['step'] == 'waiting_source':
            # Get source code
            source = ""
            if message.attachments:
                for att in message.attachments:
                    if any(att.filename.endswith(ext) for ext in ['.txt', '.py', '.js', '.java', '.cpp']):
                        source = (await att.read()).decode('utf-8')
                        break
            else:
                source = message.content

            if source:
                session['source'] = source
                session['step'] = 'waiting_password'
                await message.reply("🔑 **Vui lòng nhập mật khẩu để mã hóa:**")
            else:
                await message.reply("❌ Không tìm thấy source code!")

        elif session['step'] == 'waiting_password':
            password = message.content.strip()
            if len(password) >= 4:
                # Mã hóa
                processing = await message.reply("🛡️ **Đang mã hóa...**")
                encrypted = simple_encrypt(session['source'], password)
                
                # Tạo file
                result = {
                    'encrypted_data': encrypted,
                    'timestamp': datetime.now().isoformat(),
                    'algorithm': 'Base64+XOR'
                }
                
                file_content = json.dumps(result, indent=2)
                file = discord.File(fp=discord.BytesIO(file_content.encode()), filename="encrypted_code.secure")
                
                # Gửi kết quả
                try:
                    await message.author.send(f"🔐 **Mã hóa thành công!**\nMật khẩu: ||{password}||", file=file)
                    await processing.edit(content="✅ **Đã gửi file mã hóa qua tin nhắn riêng!**")
                except:
                    await processing.edit(content="❌ Không thể gửi tin nhắn riêng!")
                
                del sessions[user_id]
            else:
                await message.reply("❌ Mật khẩu phải >= 4 ký tự!")

    # Lệnh giải mã
    elif message.content.startswith('!giaima'):
        await message.reply("🔓 **Vui lòng gửi file .secure và mật khẩu giải mã:**")

    # Lệnh status
    elif message.content == '!status':
        await message.reply("🟢 **Bot đang hoạt động bình thường!**")

# Chạy bot
print("🚀 Starting bot...")
client.run(TOKEN)
