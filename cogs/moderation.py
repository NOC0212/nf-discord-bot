# cogs/moderation.py
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="大量刪除訊息", description="大量刪除指定數量或指定使用者的訊息")
    @app_commands.describe(
        數量="要刪除的訊息數量 (1-100條)",
        使用者="指定要刪除哪個使用者的訊息 (可選，留空則刪除所有人的訊息)"
    )
    @commands.has_permissions(manage_messages=True) # 需要管理訊息權限
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.channel_id)) # 設定 10 秒冷卻時間，防止濫用
    async def bulk_delete_messages(
        self,
        interaction: discord.Interaction,
        數量: app_commands.Range[int, 1, 100], # 數量限制在 1 到 100 之間
        使用者: Optional[discord.Member] = None # 使用者參數是可選的
    ):
        await interaction.response.defer(ephemeral=True) # 延遲回覆，讓使用者知道指令正在處理，回覆僅自己可見

        channel = interaction.channel
        
        # 根據是否指定使用者來定義檢查函數
        # 這個函數會被 channel.purge 用來判斷哪些訊息應該被刪除
        def check_func(message):
            # 確保不刪除機器人自己的互動訊息，儘管由於 ephemeral=True 通常不會在頻道中生成持久訊息
            # 或者可以添加條件來排除特定訊息ID，但對於purge來說，這通常不是必需的
            if 使用者: # 如果指定了使用者
                return message.author == 使用者 # 只刪除該使用者的訊息
            return True # 如果沒有指定使用者，則刪除所有訊息

        try:
            # 使用 channel.purge 進行批量刪除。
            # limit 參數指定要檢查的訊息數量 (從最新開始)，check 函數篩選實際要刪除的訊息。
            # purge 會自動處理 Discord 的 14 天訊息限制，超出時間的訊息將無法被刪除。
            deleted_messages = await channel.purge(limit=數量, check=check_func)
            deleted_count = len(deleted_messages) # 實際刪除的訊息數量

            # 向使用者發送確認訊息，設定 ephemeral=False 讓頻道中所有人可見，告知刪除結果
            if 使用者:
                await interaction.followup.send(
                    f"已成功刪除 {deleted_count} 條來自 {使用者.mention} 的訊息。", ephemeral=False
                )
            else:
                await interaction.followup.send(
                    f"已成功刪除 {deleted_count} 條訊息。", ephemeral=False
                )

        except discord.Forbidden: # 機器人缺少權限
            await interaction.followup.send(
                "我沒有足夠的權限刪除訊息。請檢查我的身份組權限，確保我有 '管理訊息' 權限。", ephemeral=True
            )
        except discord.HTTPException as e: # Discord API 錯誤
            await interaction.followup.send(f"刪除訊息時發生錯誤: {e}", ephemeral=True)
        except Exception as e: # 其他未知錯誤
            await interaction.followup.send(f"發生未知錯誤: {e}", ephemeral=True)

async def setup(bot):
    # 將 Moderation cog 添加到機器人中
    await bot.add_cog(Moderation(bot))