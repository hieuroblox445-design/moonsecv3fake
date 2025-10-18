from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import os
import random
import string
import base64
import asyncio

# Flask app for keeping bot alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Khởi chạy Flask trong thread riêng
flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

def generate_encryption_key():
    """Tạo key mã hóa ngẫu nhiên"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def xor_encrypt(data, key):
    """Mã hóa dữ liệu bằng XOR"""
    encrypted = bytearray()
    key_bytes = key.encode()
    for i, byte in enumerate(data):
        encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    return bytes(encrypted)

def encrypt_lua_code(code, key):
    """Mã hóa code Lua nhưng vẫn giữ code gốc bên trong"""
    # Mã hóa code
    encrypted_data = xor_encrypt(code.encode(), key)
    encrypted_b64 = base64.b64encode(encrypted_data).decode()
    
    # Tạo file .lua với code gốc được bảo vệ bên trong
    protected_code = f'''-- File đã được mã hóa bảo vệ
-- Decryptor tự động

local encrypted_data = "{encrypted_b64}"
local encryption_key = "{key}"

local function base64_decode(data)
    local b = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    data = string.gsub(data, '[^'..b..'=]', '')
    return (data:gsub('.', function(x)
        if (x == '=') then return '' end
        local r, f = '', (b:find(x) - 1)
        for i = 6, 1, -1 do
            r = r .. (f % 2 ^ i - f % 2 ^ (i - 1) > 0 and '1' or '0')
        end
        return r
    end):gsub('%d%d%d?%d?%d?%d?%d?%d?', function(x)
        if (#x ~= 8) then return '' end
        local c = 0
        for i = 1, 8 do
            c = c + (x:sub(i, i) == '1' and 2 ^ (8 - i) or 0)
        end
        return string.char(c)
    end))
end

local function xor_decrypt(data, key)
    local result = ""
    local key_bytes = {{}}
    for i = 1, #key do
        key_bytes[i] = key:byte(i)
    end
    
    for i = 1, #data do
        local data_byte = data:byte(i)
        local key_byte = key_bytes[((i - 1) % #key_bytes) + 1]
        result = result .. string.char(data_byte ~ key_byte)
    end
    return result
end

-- Giải mã và thực thi code gốc
local function execute_original_code()
    local decoded_data = base64_decode(encrypted_data)
    local original_code = xor_decrypt(decoded_data, encryption_key)
    
    -- Thực thi code gốc
    local loaded_function, error_msg = load(original_code)
    if loaded_function then
        loaded_function()
    else
        error("Lỗi khi thực thi code: " .. (error_msg or "unknown"))
    end
end

-- Chạy code gốc
execute_original_code()

-- Code gốc được bảo vệ bên dưới (đã mã hóa)
-- Không thể đọc trực tiếp mà phải thông qua giải mã
'''
    return protected_code

def create_protected_lua(code, key):
    """Tạo file Lua được bảo vệ với code gốc bên trong"""
    # Mã hóa code
    encrypted_data = xor_encrypt(code.encode(), key)
    encrypted_b64 = base64.b64encode(encrypted_data).decode()
    
    # Tạo file Lua với cấu trúc bảo vệ
    protected_code = f'''--[[
File được bảo vệ - Protected File
Mã hóa tự động bởi Discord Bot
]]

local _G = _G
local string = string
local table = table
local load = load

-- Dữ liệu mã hóa
local _E = "{encrypted_b64}"
local _K = "{key}"

-- Hàm giải mã
local function _D(d, k)
    local r = ""
    local kb = {{}}
    for i = 1, #k do kb[i] = k:byte(i) end
    for i = 1, #d do
        local b = d:byte(i)
        local kb = kb[((i-1) % #kb) + 1]
        r = r .. string.char(b ~ kb)
    end
    return r
end

-- Hàm decode base64
local function _B(d)
    local b = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    d = string.gsub(d, '[^'..b..'=]', '')
    return (d:gsub('.', function(x)
        if x == '=' then return '' end
        local r,f = '',(b:find(x)-1)
        for i=6,1,-1 do r=r..(f%2^i-f%2^(i-1)>0 and '1' or '0') end
        return r
    end):gsub('%d%d%d?%d?%d?%d?%d?%d?', function(x)
        if #x ~= 8 then return '' end
        local c=0
        for i=1,8 do c=c+(x:sub(i,i)=='1' and 2^(8-i) or 0) end
        return string.char(c)
    end))
end

-- Giải mã và thực thi
local decoded = _B(_E)
local original = _D(decoded, _K)
local fn, err = load(original)
if fn then fn() else error(err or "Execution error") end

-- Kết thúc file được bảo vệ
'''
    return protected_code

@bot.event
async def on_ready():
    print(f'{bot.user} đã kết nối thành công!')
    await bot.change_presence(activity=discord.Game(name="!mahoa để mã hóa code"))
    
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Lỗi đồng bộ slash commands: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"Có lỗi xảy ra: {str(error)}")

@bot.command(name='mahoa')
async def encrypt_code(ctx):
    """Lệnh mã hóa file code"""
    if not ctx.message.attachments:
        await ctx.send(" Vui lòng gửi file code đính kèm khi sử dụng lệnh `!mahoa`")
        return
    
    attachment = ctx.message.attachments[0]
    
    # Kiểm tra file type
    valid_extensions = ['.lua', '.txt', '.py', '.js', '.cpp', '.c', '.java', '.php', '.xml', '.json']
    if not any(attachment.filename.lower().endswith(ext) for ext in valid_extensions):
        await ctx.send(" File không hợp lệ. Chỉ chấp nhận file code")
        return
    
    try:
        wait_msg = await ctx.send(" Đang xử lý file...")
        
        # Tải file
        file_content = await attachment.read()
        original_code = file_content.decode('utf-8')
        
        # Tạo key mã hóa
        encryption_key = generate_encryption_key()
        
        # Tạo file được bảo vệ (giữ code gốc bên trong)
        protected_lua_code = create_protected_lua(original_code, encryption_key)
        
        # Tạo tên file mới
        original_name = os.path.splitext(attachment.filename)[0]
        encrypted_filename = f"{original_name}_protected.lua"
        
        # Lưu file tạm
        with open(encrypted_filename, 'w', encoding='utf-8') as f:
            f.write(protected_lua_code)
        
        # Gửi file đã mã hóa
        with open(encrypted_filename, 'rb') as f:
            file = discord.File(f, filename=encrypted_filename)
            embed = discord.Embed(
                title=" Mã Hóa Thành Công",
                description=f"File `{attachment.filename}` đã được bảo vệ",
                color=0x00ff00
            )
            embed.add_field(
                name=" Thông tin",
                value="• File gốc được giữ nguyên bên trong\n• Có thể chạy bình thường\n• Code được bảo vệ khỏi chỉnh sửa",
                inline=False
            )
            await ctx.send(embed=embed, file=file)
        
        # Xóa file tạm
        os.remove(encrypted_filename)
        await wait_msg.delete()
        
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi xử lý file: {str(e)}")

@bot.command(name='ping')
async def ping(ctx):
    """Kiểm tra độ trễ"""
    latency = round(bot.latency * 1000)
    await ctx.send(f' Ping! Độ trễ: {latency}ms')

@bot.command(name='trogiup')
async def help_command(ctx):
    """Hướng dẫn sử dụng"""
    help_text = """
**🤖 Bot Bảo Vệ Code**

**Lệnh:**
`!mahoa` - Bảo vệ file code (giữ nguyên code gốc bên trong)
`!ping` - Kiểm tra độ trễ
`!trogiup` - Hiển thị hướng dẫn

**Đặc điểm:**
• File .lua được tạo ra vẫn chứa code gốc bên trong
• Code gốc được mã hóa và bảo vệ
• File có thể chạy bình thường với Lua interpreter
• Bảo vệ code khỏi chỉnh sửa trực tiếp

**Hỗ trợ file:** .lua, .txt, .py, .js, .cpp, .c, .java, .php, .xml, .json
"""
    await ctx.send(help_text)

# Slash command support
@bot.tree.command(name="mahoa", description="Bảo vệ file code thành file .lua (giữ code gốc)")
async def slash_encrypt(interaction: discord.Interaction):
    """Slash command cho mã hóa"""
    await interaction.response.send_message("Vui lòng gửi file code đính kèm khi sử dụng lệnh này. Sử dụng `!mahoa` với file đính kèm.")

@bot.event
async def on_message(message):
    if message.content in ['/mahoa', '!mahoa'] and not message.attachments:
        await message.channel.send(" Vui lòng gửi file code đính kèm khi sử dụng lệnh này.")
    
    await bot.process_commands(message)

# Chạy bot với token từ environment variable
if __name__ == "__main__":
    token = os.environ.get('TOKEN')
    if not token:
        print("Lỗi: TOKEN không được tìm thấy trong environment variables!")
        exit(1)
    
    print("🤖 Đang khởi động bot...")
    print("🌐 Flask server đang chạy trên port 8080")
    bot.run(token)
