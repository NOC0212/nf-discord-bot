# cogs/leveling.py

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import asyncio
from typing import Optional

# 數據檔案
LEVELING_DATA_FILE = "leveling_data.json"
CONFIG_DATA_FILE = "leveling_config.json"
CURRENCY_DATA_FILE = "currency.json" # 新增貨幣檔案路徑

class LevelingData:
    """用於管理等級系統數據和設定的類別"""
    def __init__(self):
        self.file_path = LEVELING_DATA_FILE
        self.config_path = CONFIG_DATA_FILE
        self.currency_path = CURRENCY_DATA_FILE # 新增貨幣路徑
        
        self.data = self._load_data(self.file_path)
        self.config = self._load_config()
        self.cooldowns = {}

    def _load_data(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    return {}
        return {}

    def _load_config(self):
        default_config = {
            "xp_formula": "5 * (level ** 2) + 50 * level + 100",
            "xp_min": 15,
            "xp_max": 25,
            "cooldown": 60,
            "token_formula": "level * 2"
        }
        config = self._load_data(self.config_path)
        return {**default_config, **config}

    def _save_data(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def _load_currency_data(self):
        return self._load_data(self.currency_path)

    def _save_currency_data(self, currency_data):
        with open(self.currency_path, 'w', encoding='utf-8') as f:
            json.dump(currency_data, f, indent=4, ensure_ascii=False)

    def get_user_data(self, user_id: int):
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            self.data[user_id_str] = {"level": 0, "xp": 0}
        self._save_data()
        return self.data[user_id_str]

    def add_xp(self, user_id: int, xp_amount: int):
        user_data = self.get_user_data(user_id)
        user_data["xp"] += xp_amount
        if self._check_level_up(user_id):
            self._save_data()
            return True
        self._save_data()
        return False

    def _get_required_xp(self, level: int):
        try:
            return eval(self.config["xp_formula"], {"level": level})
        except Exception:
            return 5 * (level ** 2) + 50 * level + 100

    def _get_level_up_tokens(self, level: int):
        try:
            return eval(self.config["token_formula"], {"level": level})
        except Exception:
            return level * 2

    def _check_level_up(self, user_id: int):
        user_data = self.get_user_data(user_id)
        level_up = False
        while user_data["xp"] >= self._get_required_xp(user_data["level"]):
            user_data["xp"] -= self._get_required_xp(user_data["level"])
            user_data["level"] += 1
            # 在這裡，我們不再儲存代幣在 leveling_data.json
            level_up = True
        return level_up
    
    def get_leaderboard(self):
        sorted_users = sorted(self.data.items(), key=lambda item: (item[1]['level'], item[1]['xp']), reverse=True)
        return sorted_users

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leveling_data = LevelingData()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = message.author.id
        
        cooldown_time = self.leveling_data.config.get("cooldown", 60)
        if user_id in self.leveling_data.cooldowns and (
            message.created_at - self.leveling_data.cooldowns[user_id]
        ).total_seconds() < cooldown_time:
            return

        self.leveling_data.cooldowns[user_id] = message.created_at
        
        xp_min = self.leveling_data.config.get("xp_min", 15)
        xp_max = self.leveling_data.config.get("xp_max", 25)
        xp_gained = random.randint(xp_min, xp_max)
        
        if self.leveling_data.add_xp(user_id, xp_gained):
            user_data = self.leveling_data.get_user_data(user_id)
            
            # --- 處理代幣獎勵，與 currency.json 互動 ---
            currency_data = self.leveling_data._load_currency_data()
            user_id_str = str(user_id)
            tokens_earned = self.leveling_data._get_level_up_tokens(user_data['level'])
            
            current_tokens = currency_data.get(user_id_str, 0)
            currency_data[user_id_str] = current_tokens + tokens_earned
            self.leveling_data._save_currency_data(currency_data)
            # -----------------------------------------------

            await message.channel.send(
                f"恭喜 {message.author.mention}！您升到了 **等級 {user_data['level']}**！\n"
                f"作為獎勵，您獲得了 **{tokens_earned}** 個代幣！"
            )

    @app_commands.command(name="查看我的等級", description="查看自己的等級和經驗值")
    @app_commands.guild_only()
    async def rank(self, interaction: discord.Interaction):
        user_data = self.leveling_data.get_user_data(interaction.user.id)
        currency_data = self.leveling_data._load_currency_data() # 讀取貨幣數據
        
        level = user_data["level"]
        xp = user_data["xp"]
        tokens = currency_data.get(str(interaction.user.id), 0) # 從貨幣數據中獲取代幣數
        required_xp = self.leveling_data._get_required_xp(level)

        embed = discord.Embed(
            title=f"{interaction.user.display_name} 的等級",
            description=f"等級: **{level}**\n經驗值: **{xp}/{required_xp}**\n代幣: **{tokens}**",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="等級排行榜", description="查看伺服器等級排名")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        leaderboard_data = self.leveling_data.get_leaderboard()
        currency_data = self.leveling_data._load_currency_data() # 讀取貨幣數據
        
        embed = discord.Embed(title="等級排行榜", color=discord.Color.gold())
        
        for i, (user_id_str, user_data) in enumerate(leaderboard_data[:10]):
            user = await self.bot.fetch_user(int(user_id_str))
            if user:
                tokens = currency_data.get(user_id_str, 0) # 從貨幣數據中獲取代幣
                embed.add_field(
                    name=f"#{i+1} {user.display_name}",
                    value=f"等級: {user_data['level']} | 經驗值: {user_data['xp']} | 代幣: {tokens}",
                    inline=False
                )

        if not leaderboard_data:
            embed.description = "目前還沒有人有經驗值，快去發言吧！"

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="等級系統設定", description="設定等級系統的參數")
    @app_commands.describe(
        升級經驗公式="升級所需經驗值的公式，例如：5 * level ** 2 + 50 * level + 100",
        每次聊天最少經驗="每次聊天獲得的最低經驗值",
        每次聊天最多經驗="每次聊天獲得的最高經驗值",
        經驗冷卻時間="每次獲得經驗值的冷卻時間（秒）",
        升級代幣公式="每次升級可獲得的代幣數公式，例如：level * 2"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def leveling_config(self, interaction: discord.Interaction, 
                              升級經驗公式: Optional[str] = None, 
                              每次聊天最少經驗: Optional[int] = None,
                              每次聊天最多經驗: Optional[int] = None,
                              經驗冷卻時間: Optional[int] = None,
                              升級代幣公式: Optional[str] = None):
        
        await interaction.response.defer(ephemeral=True)

        if 升級經驗公式:
            self.leveling_data.config["xp_formula"] = 升級經驗公式
        if 每次聊天最少經驗:
            self.leveling_data.config["xp_min"] = 每次聊天最少經驗
        if 每次聊天最多經驗:
            self.leveling_data.config["xp_max"] = 每次聊天最多經驗
        if 經驗冷卻時間:
            self.leveling_data.config["cooldown"] = 經驗冷卻時間
        if 升級代幣公式:
            self.leveling_data.config["token_formula"] = 升級代幣公式
        
        self.leveling_data._save_data()
        
        embed = discord.Embed(
            title="等級系統設定已更新",
            description="已成功儲存您的設定。",
            color=discord.Color.green()
        )
        embed.add_field(name="升級經驗公式", value=self.leveling_data.config["xp_formula"], inline=False)
        embed.add_field(name="聊天經驗範圍", value=f"{self.leveling_data.config['xp_min']} - {self.leveling_data.config['xp_max']}", inline=False)
        embed.add_field(name="經驗冷卻時間", value=f"{self.leveling_data.config['cooldown']} 秒", inline=False)
        embed.add_field(name="升級代幣公式", value=self.leveling_data.config["token_formula"], inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Leveling(bot))