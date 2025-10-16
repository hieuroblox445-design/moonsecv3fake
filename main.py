import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io
import os
import threading
from flask import Flask

# =========================
# ⚙️ Flask keep-alive setup
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!"

def run_alive():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run_alive)
    t.daemon = True
    t.start()

# =========================
# ⚙️ Discord Bot setup
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔧 Slash commands synced: {len(synced)} lệnh")
    except Exception as e:
        print(f"❌ Lỗi sync slash: {e}")

# =========================
# 📁 DOCFILE PREFIX CMD
# =========================
@bot.command(name="docfile")
async def docfile_prefix(ctx):
    await ctx.send("📎 Gửi file .txt / .md / .log bạn muốn đọc trong vòng 30 giây.")

    def check(m):
        return m.author == ctx.author and m.attachments

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        attachment = msg.attachments[0]

        if not attachment.filename.endswith((".txt", ".md", ".log")):
            await ctx.send("❌ Chỉ chấp nhận file .txt, .md, .log thôi nha.")
            return

        file_bytes = await attachment.read()
        content = file_bytes.decode("utf-8", errors="ignore")

        if len(content) > 50000:
            await ctx.send("⚠️ File quá dài (>50.000 ký tự)! Chỉ gửi phần đầu.")
            content = content[:50000]

        chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
        await ctx.send(f"📖 **Nội dung `{attachment.filename}` ({len(chunks)} phần):**")

        for i, chunk in enumerate(chunks[:10]):  # gửi tối đa 10 phần để tránh spam
            await ctx.send(f"```{chunk}```")
        if len(chunks) > 10:
            await ctx.send("⏹️ Nội dung bị cắt bớt (chỉ hiển thị 10 phần đầu).")

    except asyncio.TimeoutError:
        await ctx.send("⏰ Hết thời gian chờ file. Hãy thử lại `!docfile` nhé.")

# =========================
# 📁 DOCFILE SLASH CMD
# =========================
@bot.tree.command(name="docfile", description="Gửi file để bot đọc nội dung")
async def docfile_slash(interaction: discord.Interaction):
    await interaction.response.send_message("📎 Gửi file văn bản bạn muốn bot đọc (txt/md/log)... trong vòng 30 giây.", ephemeral=True)

    def check(m):
        return m.author == interaction.user and m.attachments

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        attachment = msg.attachments[0]

        if not attachment.filename.endswith((".txt", ".md", ".log")):
            await interaction.followup.send("❌ Chỉ chấp nhận file .txt, .md, .log thôi nha.")
            return

        file_bytes = await attachment.read()
        content = file_bytes.decode("utf-8", errors="ignore")

        if len(content) > 50000:
            await interaction.followup.send("⚠️ File quá dài (>50.000 ký tự)! Chỉ gửi phần đầu.")
            content = content[:50000]

        chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
        await interaction.followup.send(f"📖 **Nội dung `{attachment.filename}` ({len(chunks)} phần):**")

        for i, chunk in enumerate(chunks[:10]):
            await interaction.channel.send(f"```{chunk}```")
        if len(chunks) > 10:
            await interaction.channel.send("⏹️ Nội dung bị cắt bớt (chỉ hiển thị 10 phần đầu).")

    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Hết thời gian chờ file. Hãy thử lại `/docfile` nhé.")

# =========================
# 🚀 Run Flask + Discord
# =========================
keep_alive()  # chạy web server 0.0.0.0:8080

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("❌ Thiếu biến môi trường TOKEN!")
else:
    bot.run(TOKEN)
