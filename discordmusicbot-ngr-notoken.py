import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.DEBUG)


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

FFMPEG_OPTIONS = {'options': '-vn'}
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': True}

class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = []
        self.last_action_time = datetime.now()
        self.leave_task.start()
        self.last_channel = None

    def cog_unload(self):
        self.leave_task.cancel()

    @tasks.loop(seconds=60)  # Check every 60 seconds
    async def leave_task(self):
        if self.client.voice_clients:
            now = datetime.now()
            if (now - self.last_action_time) > timedelta(minutes=2):
                for vc in self.client.voice_clients:
                    if not vc.is_playing() and not vc.is_paused():
                        await vc.disconnect()
                        if self.last_channel:
                            try:
                                await self.last_channel.send("I left because I got bored")
                            except Exception as e:
                                logging.error(f"Failed to send message in the channel: {e}")
                        else:
                            logging.debug("No channel set for sending leave message.")
                        


    @leave_task.before_loop
    async def before_leave_task(self):
        await self.client.wait_until_ready()

    async def update_last_action(self, ctx):
        self.last_action_time = datetime.now()
        self.last_channel = ctx.channel
        logging.debug(f"Updated last action time: {self.last_action_time} and channel: {self.last_channel}")

    @commands.command()
    async def play(self, ctx, *, search):
        print("Received play command")  # Debug log
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You're not in a voice channel!")
        if not ctx.voice_client:
            await voice_channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                title = info['title']
                self.queue.append((url, title))
                await ctx.send(f'Added to queue: **{title}**')
            if not ctx.voice_client.is_playing():
                await self.play_next(ctx)

    async def play_next(self, ctx):
        print("Playing next in queue")  # Debug log
        if self.queue:
            url, title = self.queue.pop(0)
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda _: self.client.loop.create_task(self.play_next(ctx)))
            await ctx.send(f'Now playing: **{title}**')
        elif not ctx.voice_client.is_playing():
            await ctx.send("Queue is empty!")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused")
        else:
            await ctx.send("No audio is playing to pause stupido")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed")
        else:
            await ctx.send("Music is not paused stupido")

    @commands.command()
    async def queue(self, ctx):
        if self.queue:
            queue_list = "\n".join([f"{idx + 1}, {title}" for idx, (_, title) in enumerate(self.queue)])
            await ctx.send(f"Current Queue:\n{queue_list}")
        else:
            await ctx.send("The queue is empty")       
             

client = commands.Bot(command_prefix="?", intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')  # Debug log

async def main():
    await client.add_cog(MusicBot(client))
    await client.start('DISCORD_TOKEN')

asyncio.run(main())

