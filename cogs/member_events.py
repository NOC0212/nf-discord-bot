# cogs/member_events.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class MemberEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_file = 'welcome_messages.json'
        self.goodbye_file = 'goodbye_messages.json'
        self.welcome_messages = self.load_data(self.welcome_file)
        self.goodbye_messages = self.load_data(self.goodbye_file)

    def load_data(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_data(self, data, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    @app_commands.command(name="設定歡迎訊息", description="設定成員加入伺服器時發送的歡迎訊息")
    @app_commands.describe(channel="發送歡迎訊息的頻道", message="歡迎訊息內容，可使用 {user} 標記")
    @commands.has_permissions(manage_guild=True)
    async def set_welcome_message(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        await interaction.response.defer(ephemeral=True)
        self.welcome_messages[str(interaction.guild_id)] = {'channel_id': channel.id, 'message': message}
        self.save_data(self.welcome_messages, self.welcome_file)
        await interaction.followup.send(f"已成功設定歡迎訊息，將在 {channel.mention} 發送。", ephemeral=True)

    @app_commands.command(name="設定離開訊息", description="設定成員離開伺服器時發送的訊息")
    @app_commands.describe(channel="發送離開訊息的頻道", message="離開訊息內容，可使用 {user} 標記")
    @commands.has_permissions(manage_guild=True)
    async def set_goodbye_message(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        await interaction.response.defer(ephemeral=True)
        self.goodbye_messages[str(interaction.guild_id)] = {'channel_id': channel.id, 'message': message}
        self.save_data(self.goodbye_messages, self.goodbye_file)
        await interaction.followup.send(f"已成功設定離開訊息，將在 {channel.mention} 發送。", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = str(member.guild.id)
        if guild_id in self.welcome_messages:
            channel_id = self.welcome_messages[guild_id]['channel_id']
            message = self.welcome_messages[guild_id]['message'].format(user=member.mention)
            channel = member.guild.get_channel(channel_id)
            if channel:
                await channel.send(message)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = str(member.guild.id)
        if guild_id in self.goodbye_messages:
            channel_id = self.goodbye_messages[guild_id]['channel_id']
            message = self.goodbye_messages[guild_id]['message'].format(user=member.mention)
            channel = member.guild.get_channel(channel_id)
            if channel:
                await channel.send(message)

async def setup(bot):
    await bot.add_cog(MemberEvents(bot))
