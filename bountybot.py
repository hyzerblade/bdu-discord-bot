from datetime import datetime
import asyncio
from configparser import ConfigParser

import pandas
import discord
from discord.ext import commands, tasks

intents = discord.Intents(messages=True, guilds=True, members=True, presences=False, reactions =True)
client = commands.Bot(command_prefix='b.', intents = intents, chunk_guilds_at_startup = False)
client.remove_command('help')
start_time = datetime.now()

config = ConfigParser()
config.read(r'config.ini')

BOT_TOKEN = config.get('BOT', f'BOT_TOKEN')

def isManager(ctx):
    whitelist = [int(x) for x in list(config.get('BOT', f'MANAGERS_IDS').split(" "))]

    if ctx.message.author.guild_permissions.administrator or (ctx.message.author.id in whitelist):
        return True
    return False


@client.event
async def on_ready():
    print('\nWe have logged in as {0.user}'.format(client))


@client.event
async def on_command(command):
    print(f'\"{command.message.content}\" was used by {command.author}')

@client.command()
@commands.check(isManager)
async def goodbye(ctx):
    await ctx.send(f'Goodbye!\nLeaving **{ctx.guild.name}**...')
    await ctx.guild.leave()

@commands.check(isManager)
@client.command(brief='Client Latency')
async def ping(ctx):  
    await ctx.send(f'🏓 {round(client.latency * 1000)}ms')

@client.command(brief='Available commands')
async def help(ctx):
    
    infobox = discord.Embed(
                title = f'Commands for Bounty Bot',
                description = '\n',
                color = discord.Color.from_rgb(79, 145, 205),
                )
    infobox.add_field(name=f'b.help:', value= f'Available commands.', inline=False)
    infobox.add_field(name=f'b.info:', value= f'About this bot.', inline=False)
    infobox.add_field(name=f'b.ping:', value= f'Pong.', inline=False)
    infobox.add_field(name=f'\u200b', value= f'**[ADMIN]**', inline=False)
    infobox.add_field(name=f'b.start / b.stop', value= f'Start/stop listening to contract.', inline=False)
    infobox.add_field(name=f'b.channels', value= f'See notification channels.', inline=False)
    infobox.add_field(name=f'b.add / b.remove [text_channel]', value= f'Add/remove notification channel.', inline=False)
    infobox.add_field(name=f'b.say [text]', value= f'Send announcement to all notification channels.', inline=False)
    infobox.add_field(name=f'b.goodbye', value= f'Remove bot from this server.', inline=False)
    
    await ctx.send(embed=infobox)

@client.command(brief='Bot Information')
async def info(ctx, more = None):

    infomsg = ('```ini\n[General Info]\n\nWritten by HyzerBlade#4042.\n'
    '\nThis bot was built for the BDU Discord server.\n'
    '\nGithub: [coming_soon].\n'
    '\n\n[Privacy]\n'
    '\nThis bot does NOT save or store any user data.\nIf you have any doubts or concerns about the functionality of this bot,\nmessage HyzerBlade#4042'
    '\n\n= = Info last updated: 2021-12-5 = =```')
    
    if len(client.guilds) < 2:
        svr = 'server'   
    else: 
        svr = 'servers'

    uptime = pandas.Timedelta(datetime.now() - start_time)
    events = client.get_cog('Event_watcher')


    botM = ctx.guild.get_member(client.user.id)
    display = discord.Embed(
                title = f'BDU Bounty Bot',
                description = 'For all your bounty tracking needs.',
                color = discord.Color.from_rgb(79, 145, 205),
                )
    display.set_thumbnail(url=botM.avatar_url)
    display.add_field(name='Status:', value=events.status, inline = False)
    display.add_field(name='Uptime:', value=str(uptime.round('1s')), inline = False)
    display.add_field(name='Inhabiting:', value=f'**{len(client.guilds)}** {svr}')
    display.set_footer(text = f'For more info type \'b.info more\'')

    if more == 'more':
        await ctx.send(infomsg)
    else: 
        await ctx.send(embed=display)

@client.event
async def on_command_error(ctx, error):
    
    if isinstance(error, commands.CheckFailure):
        await ctx.send(f'**You don\'t have permission to use that command, {ctx.author.display_name}.**') 
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f'That\'s not a command, {ctx.author.display_name}')
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f'**Error: `{error}`.**\n')
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
    else:
        await ctx.send(f'An error has been detected:\n`{error}`\n')
    print(error)


extensions = ['cogs.Event_watcher']

if __name__ == '__main__':

    for ext in extensions:
        client.load_extension(ext)

client.run(BOT_TOKEN)