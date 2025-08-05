# cogs/weather.py
import discord
from discord import app_commands
from discord.ext import commands
from utils.weather import get_weather_forecast

# 台灣各縣市列表，用於下拉式選單
TAIWAN_CITIES = [
    app_commands.Choice(name="臺北市", value="臺北市"),
    app_commands.Choice(name="新北市", value="新北市"),
    app_commands.Choice(name="桃園市", value="桃園市"),
    app_commands.Choice(name="臺中市", value="臺中市"),
    app_commands.Choice(name="臺南市", value="臺南市"),
    app_commands.Choice(name="高雄市", value="高雄市"),
    app_commands.Choice(name="基隆市", value="基隆市"),
    app_commands.Choice(name="新竹市", value="新竹市"),
    app_commands.Choice(name="新竹縣", value="新竹縣"),
    app_commands.Choice(name="苗栗縣", value="苗栗縣"),
    app_commands.Choice(name="彰化縣", value="彰化縣"),
    app_commands.Choice(name="南投縣", value="南投縣"),
    app_commands.Choice(name="雲林縣", value="雲林縣"),
    app_commands.Choice(name="嘉義市", value="嘉義市"),
    app_commands.Choice(name="嘉義縣", value="嘉義縣"),
    app_commands.Choice(name="屏東縣", value="屏東縣"),
    app_commands.Choice(name="宜蘭縣", value="宜蘭縣"),
    app_commands.Choice(name="花蓮縣", value="花蓮縣"),
    app_commands.Choice(name="臺東縣", value="臺東縣"),
    app_commands.Choice(name="澎湖縣", value="澎湖縣"),
    app_commands.Choice(name="金門縣", value="金門縣"),
    app_commands.Choice(name="連江縣", value="連江縣")
]

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="查詢天氣", description="查詢指定地區未來3個時段的天氣預報")
    @app_commands.describe(location="查詢天氣的縣市")
    @app_commands.choices(location=TAIWAN_CITIES)
    async def weather_command(self, interaction: discord.Interaction, location: app_commands.Choice[str]):
        await interaction.response.defer(thinking=True)
        forecast_message = await get_weather_forecast(location.value)
        await interaction.followup.send(forecast_message)

async def setup(bot):
    await bot.add_cog(Weather(bot))
