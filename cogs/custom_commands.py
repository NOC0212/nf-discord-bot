# cogs/custom_commands.py

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Dict, Any, List, Optional

CUSTOM_COMMANDS_FILE = 'custom_commands.json'

class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 數據格式：{guild_id: {keyword: response_content}}
        self.guild_commands_map: Dict[str, Dict[str, str]] = self._load_custom_commands()
        print("已載入自訂關鍵詞觸發功能。")

    def _load_custom_commands(self) -> Dict[str, Dict[str, str]]:
        """從 JSON 檔案載入自訂關鍵詞數據"""
        if os.path.exists(CUSTOM_COMMANDS_FILE):
            with open(CUSTOM_COMMANDS_FILE, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print(f"警告: {CUSTOM_COMMANDS_FILE} 檔案內容無效。將建立新的檔案。")
                    return {}
        return {}

    def _save_custom_commands(self):
        """將自訂關鍵詞數據儲存到 JSON 檔案"""
        with open(CUSTOM_COMMANDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.guild_commands_map, f, ensure_ascii=False, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """監聽所有訊息，檢查是否符合自訂關鍵詞"""
        # 忽略機器人自己的訊息
        if message.author.bot:
            return
        
        # 忽略沒有伺服器的訊息 (私訊)
        if message.guild is None:
            return

        guild_id = str(message.guild.id)
        
        # 獲取該伺服器的關鍵詞-回應對應表
        commands_map = self.guild_commands_map.get(guild_id, {})
        
        # 檢查訊息內容是否與任何一個關鍵詞完全匹配
        if message.content in commands_map:
            response = commands_map[message.content]
            try:
                # 使用 await message.channel.send() 來發送回應
                await message.channel.send(response)
            except discord.Forbidden:
                print(f"警告: 在伺服器 {message.guild.name} 頻道 {message.channel.name} 沒有發送訊息的權限。")

    @app_commands.command(name="新增指令", description="新增一個關鍵詞觸發的回應")
    @app_commands.describe(
        關鍵詞="觸發回應的關鍵詞 (例如: 早安)",
        回應="關鍵詞被觸發時的回應內容"
    )
    @commands.has_permissions(manage_guild=True)
    async def add_custom_command(
        self,
        interaction: discord.Interaction,
        關鍵詞: str,
        回應: str
    ):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        
        # 將關鍵詞存儲為小寫並移除空格，以確保一致性
        keyword = 關鍵詞.lower().replace(" ", "")

        if guild_id not in self.guild_commands_map:
            self.guild_commands_map[guild_id] = {}
        
        if keyword in self.guild_commands_map[guild_id]:
            await interaction.followup.send(f"關鍵詞 `{keyword}` 已存在，請使用其他關鍵詞。", ephemeral=True)
            return
            
        self.guild_commands_map[guild_id][keyword] = 回應
        self._save_custom_commands()
        await interaction.followup.send(f"已成功新增關鍵詞觸發的回應：`{keyword}` -> `{回應}`")

    @app_commands.command(name="移除指令", description="移除一個關鍵詞觸發的回應")
    @app_commands.describe(
        關鍵詞="要移除的關鍵詞"
    )
    @commands.has_permissions(manage_guild=True)
    async def remove_custom_command(self, interaction: discord.Interaction, 關鍵詞: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        
        keyword = 關鍵詞.lower().replace(" ", "")

        if guild_id not in self.guild_commands_map or keyword not in self.guild_commands_map[guild_id]:
            await interaction.followup.send(f"找不到名為 `{keyword}` 的關鍵詞觸發回應。", ephemeral=True)
            return

        del self.guild_commands_map[guild_id][keyword]
        self._save_custom_commands()
        await interaction.followup.send(f"已成功移除關鍵詞 `{keyword}`。")

    @app_commands.command(name="查詢指令", description="查詢所有自訂關鍵詞觸發的回應")
    @commands.has_permissions(manage_guild=True)
    async def list_custom_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        guild_id = str(interaction.guild_id)
        
        commands_list = self.guild_commands_map.get(guild_id, {})
        
        if not commands_list:
            await interaction.followup.send("此伺服器目前沒有任何自訂關鍵詞觸發的回應。")
            return
        
        embed = discord.Embed(
            title="📃 自訂關鍵詞列表",
            description="\n".join([f"`{keyword}`: {response}" for keyword, response in commands_list.items()]),
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))