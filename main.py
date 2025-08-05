# main.py
import discord
from discord.ext import commands
import os
import asyncio

from config import BOT_TOKEN, WEATHER_API_KEY

# (例如 Message Content Intent, Presence Intent, Server Members Intent)，否則機器人可能無法正常運作部分功能。
intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents) # 替換為您想要的前綴

    async def setup_hook(self):
        print("開始載入擴充功能 (Cogs)...")
        # 定義不需要作為 Cog 載入的檔案列表
        EXCLUDED_COGS = ['giveaway_data.py', 'giveaway_utils.py']
        
        # 遍歷 cogs 資料夾中的所有 .py 檔案
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != '__init__.py' and filename not in EXCLUDED_COGS:
                cog_name = f'cogs.{filename[:-3]}'
                try:
                    await self.load_extension(cog_name)
                    print(f'成功載入擴充功能：{cog_name}')
                except commands.ExtensionAlreadyLoaded:
                    print(f'警告：{cog_name} 已經載入，跳過。')
                except commands.ExtensionNotFound:
                    print(f'錯誤：找不到擴充功能 {cog_name}。請確認檔案是否存在於正確路徑。')
                except commands.NoEntryPointError:
                    print(f'錯誤：擴充功能 {cog_name} 中沒有 setup 函數。')
                except Exception as e:
                    print(f'載入擴充功能 {cog_name} 時發生未知錯誤：{e}')
        
        # 同步所有斜線指令
        try:
            synced = await self.tree.sync()
            print(f'已同步 {len(synced)} 個斜線指令。')
        except Exception as e:
            print(f"同步斜線指令時發生錯誤: {e}")
            
    async def on_ready(self):
        print(f'機器人已成功登入為 {self.user} (ID: {self.user.id})')
        print(f'當前伺服器數量: {len(self.guilds)}')
        print('機器人已準備就緒，可以開始接收指令。')

bot = MyBot()

if __name__ == "__main__":
    if BOT_TOKEN:
        try:
            bot.run(BOT_TOKEN)
        except discord.LoginFailure:
            print("錯誤：機器人 Token 無效。請檢查 config.py 或環境變數中的 BOT_TOKEN 是否正確。")
        except Exception as e:
            print(f"啟動機器人時發生未預期錯誤: {e}")
    else:
        print("錯誤：找不到 BOT_TOKEN。請確認 config.py 中的 BOT_TOKEN 變數已正確設定。")