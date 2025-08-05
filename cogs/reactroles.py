# cogs/reactroles.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional

class ReactRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles_file = 'react_roles.json'
        self.reaction_messages = self.load_reaction_messages()

    def load_reaction_messages(self):
        """從 JSON 檔案載入反應身分組訊息數據"""
        if os.path.exists(self.reaction_roles_file):
            with open(self.reaction_roles_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print(f"警告: {self.reaction_roles_file} 檔案內容無效或為空。將重新初始化數據。")
                    return {} # 如果檔案損壞或為空，則返回空字典
        return {}

    def save_reaction_messages(self):
        """將反應身分組訊息數據儲存到 JSON 檔案"""
        with open(self.reaction_roles_file, 'w', encoding='utf-8') as f:
            json.dump(self.reaction_messages, f, indent=4)

    async def send_reaction_role_message(self, channel: discord.TextChannel, message_data: dict):
        """發送或更新反應身分組嵌入訊息"""
        # 從 message_data 中獲取顏色，如果沒有則預設為白色 (0xFFFFFF)
        embed_color = discord.Color(message_data.get('embed_color', 0xFFFFFF))

        embed = discord.Embed(
            title=message_data.get('embed_title', '請點擊反應以獲取身份組'),
            description=message_data.get('embed_description', '點擊下面的反應符號來獲取您的身份組。'),
            color=embed_color # 使用自訂顏色
        )
        
        # 為每個身分組添加一個欄位到嵌入訊息中
        for emoji_repr, role_id in message_data['roles'].items():
            try:
                role = channel.guild.get_role(int(role_id))
                if role:
                    embed.add_field(name=emoji_repr, value=role.mention, inline=True)
            except ValueError:
                 print(f"警告: 無效的身分組 ID 儲存在 JSON 中: {role_id}")
                 continue

        message = None
        message_id = message_data.get('message_id')

        # 嘗試編輯現有訊息
        if message_id:
            try:
                message = await channel.fetch_message(int(message_id))
                await message.edit(embed=embed)
            except (discord.NotFound, discord.Forbidden): # 訊息找不到或機器人沒有編輯權限
                message = None # 重置為 None，將發送新訊息

        # 如果無法編輯現有訊息，則發送新訊息
        if not message:
            message = await channel.send(embed=embed)
            message_data['message_id'] = str(message.id) # 更新訊息 ID
            self.save_reaction_messages() # 儲存更新後的數據

        # 為訊息添加反應符號
        for emoji_repr in message_data['roles'].keys():
            try:
                # 檢查 emoji_repr 是否為有效 emoji
                # 如果是 Unicode emoji，直接添加
                # 如果是自訂 emoji (<:name:id>), 則需要從 guild 中獲取
                if discord.utils.get(self.bot.emojis, name=emoji_repr.strip(':').split(':')[0]) or \
                   (emoji_repr.startswith('<') and emoji_repr.endswith('>')): # Custom emoji format
                    await message.add_reaction(emoji_repr)
                else: # Assume it's a standard unicode emoji
                    await message.add_reaction(emoji_repr)
            except discord.HTTPException as e:
                print(f"無法添加反應 {emoji_repr} 到訊息 {message.id}: {e}")
            except Exception as e:
                print(f"添加反應時發生未知錯誤 {emoji_repr}: {e}")


    @app_commands.command(name="設定自動身份組訊息", description="設定一個自動身份組訊息")
    @app_commands.describe(
        channel="訊息發送的頻道",
        title="嵌入訊息的標題",
        description="嵌入訊息的描述",
        emoji1="第一個反應符號 (例如: ✅)", # 移到必填參數區域
        role1="第一個身份組 (身份組名稱或ID)", # 移到必填參數區域
        color="嵌入訊息的顏色 (例如: #RRGGBB，預設為白色)", # 移到選填參數區域
        emoji2="第二個反應符號 (可選)",
        role2="第二個身份組 (可選)",
        emoji3="第三個反應符號 (可選)",
        role3="第三個身份組 (可選)",
        emoji4="第四個反應符號 (可選)",
        role4="第四個身份組 (可選)",
        emoji5="第五個反應符號 (可選)",
        role5="第五個身份組 (可選)"
    )
    @commands.has_permissions(manage_roles=True)
    async def set_reaction_role_message(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str,
        emoji1: str, # 必填參數
        role1: str,  # 必填參數
        color: Optional[str] = None, # 選填參數，在所有必填參數之後
        emoji2: Optional[str] = None,
        role2: Optional[str] = None,
        emoji3: Optional[str] = None,
        role3: Optional[str] = None,
        emoji4: Optional[str] = None,
        role4: Optional[str] = None,
        emoji5: Optional[str] = None,
        role5: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        
        # --- 顏色解析邏輯 ---
        embed_color_int = 0xFFFFFF # 預設為白色
        if color:
            color_str_clean = color.lstrip('#') # 移除 # 符號
            # 檢查是否為六位十六進制數字
            if len(color_str_clean) == 6 and all(c in '0123456789abcdefABCDEF' for c in color_str_clean.lower()):
                try:
                    embed_color_int = int(color_str_clean, 16) # 將十六進制字串轉換為整數
                except ValueError: 
                    await interaction.followup.send("提供的顏色碼轉換失敗，將使用預設白色。", ephemeral=True)
            else:
                await interaction.followup.send("提供的顏色碼格式不正確，請使用 #RRGGBB 格式（例如：#FF0000）。將使用預設白色。", ephemeral=True)
        # --- 顏色解析邏輯結束 ---

        roles_mapping = {}
        # 將所有的表情符號和身份組配對放入列表中
        role_pairs = [(emoji1, role1), (emoji2, role2), (emoji3, role3), (emoji4, role4), (emoji5, role5)]

        for emoji_str, role_input in role_pairs:
            if emoji_str and role_input: # 確保表情符號和身份組都有提供
                role = discord.utils.get(interaction.guild.roles, name=role_input) # 嘗試按名稱查找
                if not role:
                    try:
                        role_id = int(role_input)
                        role = interaction.guild.get_role(role_id) # 嘗試按 ID 查找
                    except ValueError:
                        pass # role_input 既不是有效名稱也不是有效 ID

                if not role:
                    await interaction.followup.send(f"找不到身份組：`{role_input}`。請檢查名稱或 ID。", ephemeral=True)
                    return
                
                # 檢查機器人是否有足夠權限管理這個身份組
                if interaction.guild.me.top_role <= role:
                    await interaction.followup.send(
                        f"我的機器人身份組 ({interaction.guild.me.top_role.name}) 權限不足，無法管理 `{role.name}` 身份組。"
                        "請確保我的機器人身份組在 Discord 設定中高於我需要管理的身份組。", ephemeral=True
                    )
                    return

                roles_mapping[emoji_str] = str(role.id)

        if not roles_mapping:
            await interaction.followup.send("您至少需要指定一個表情符號和一個身份組來設定自動身份組訊息。", ephemeral=True)
            return

        # 準備要儲存和發送的訊息數據
        message_data = {
            "channel_id": channel.id,
            "embed_title": title,
            "embed_description": description,
            "embed_color": embed_color_int, # 儲存整數形式的顏色值
            "roles": roles_mapping
        }

        # 發送/編輯訊息並獲取其 ID
        await self.send_reaction_role_message(channel, message_data)

        # 確保頂層結構存在並保存數據
        if guild_id not in self.reaction_messages:
            self.reaction_messages[guild_id] = {}
        
        # 獲取 send_reaction_role_message 返回的 message_id
        message_id = message_data.get('message_id') 
        if message_id:
            self.reaction_messages[guild_id][message_id] = message_data
            self.save_reaction_messages()
            await interaction.followup.send(f"已成功設定自動身份組訊息！訊息 ID: `{message_id}`", ephemeral=False)
        else:
             await interaction.followup.send("設定自動身份組訊息時發生錯誤，請檢查。", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id is None: # 忽略私聊
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return

        member = guild.get_member(payload.user_id)
        if not member or member.bot: # 忽略機器人自己的反應
            return

        guild_id = str(payload.guild_id)
        message_id = str(payload.message_id)
        emoji_str = str(payload.emoji)
        
        if guild_id in self.reaction_messages and message_id in self.reaction_messages[guild_id]:
            message_data = self.reaction_messages[guild_id][message_id]
            
            if emoji_str in message_data['roles']:
                role_id = int(message_data['roles'][emoji_str])
                role = guild.get_role(role_id)
                if role and member:
                    try:
                        # 檢查機器人是否有權限賦予此身分組
                        if guild.me.top_role > role:
                            await member.add_roles(role)
                        else:
                            print(f"機器人權限不足以賦予 {role.name} 給 {member.display_name}")
                    except discord.Forbidden:
                        print(f"機器人缺少權限來賦予身份組 {role.name}。")
                    except Exception as e:
                        print(f"賦予身份組時發生錯誤：{e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.guild_id is None: # 忽略私聊
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return

        member = guild.get_member(payload.user_id) # 在移除事件中，payload.member 可能為 None
        if not member or member.bot: # 忽略機器人自己的反應或已不在伺服器的成員
            return

        guild_id = str(payload.guild_id)
        message_id = str(payload.message_id)
        emoji_str = str(payload.emoji)
        
        if guild_id in self.reaction_messages and message_id in self.reaction_messages[guild_id]:
            message_data = self.reaction_messages[guild_id][message_id]
            
            if emoji_str in message_data['roles']:
                role_id = int(message_data['roles'][emoji_str])
                role = guild.get_role(role_id)
                if role and member:
                    try:
                        # 檢查機器人是否有權限移除此身分組
                        if guild.me.top_role > role:
                            await member.remove_roles(role)
                        else:
                            print(f"機器人權限不足以移除 {role.name} 給 {member.display_name}")
                    except discord.Forbidden:
                        print(f"機器人缺少權限來移除身份組 {role.name}。")
                    except Exception as e:
                        print(f"移除身份組時發生錯誤：{e}")

async def setup(bot):
    await bot.add_cog(ReactRoles(bot))