
import random
import datetime
import os
import asyncio
import typing
from datetime import datetime

import discord
import web3
from web3 import Web3
from web3.logs import STRICT, IGNORE, DISCARD, WARN
from discord.ext import commands, tasks
from configparser import ConfigParser
import requests
from bs4 import BeautifulSoup

now = datetime.now()
config = ConfigParser()

def isManager(ctx):
    whitelist = [int(x) for x in list(config.get('BOT', f'MANAGERS_IDS').split(" ")) if x != '']
    
    if ctx.message.author.guild_permissions.administrator or (ctx.message.author.id in whitelist):
        return True
    return False

class Event_watcher(commands.Cog):
    
    def __init__(self, bot):

        self.bot = bot
        self.status = 'IDLE'
        
        config.read(r'config.ini')

        self.websocket = config.get('CONTRACT', f'WEBSOCKET_PROVIDER')

        self.contract_address = config.get('CONTRACT', f'CONTRACT_ADDRESS')

        with open(config.get('CONTRACT', f'CONTRACT_ABI_PATH'), 'r') as file:
            self.abi = file.read()

        self.provider = None

        self.contract = None
        
        self.event_filter = None

        self.last_dict = None

        self.channel_ids = [int(x) for x in list(config.get('BOT', f'NOTIFICATION_CHANNEL_IDS').split(" "))]
      
        self.ctx = None

    def scrapeName(self, id):
        url = f'https://xdai.devcash.dev/bountyplatform/bounty/{id}'
        reqs = requests.get(url)
        soup = BeautifulSoup(reqs.text, 'lxml')

        return soup.find_all(["h1"])[0].text.strip()

    def eventEmbed(self, event):
    
        receipt = self.provider.eth.waitForTransactionReceipt(event['transactionHash'])
        
        created = self.contract.events.created().processReceipt(receipt, errors=DISCARD)
        rewarded = self.contract.events.rewarded().processReceipt(receipt, errors=DISCARD)

        if len(created) > 0:
            AttributeDict = created[0]
        elif len(rewarded) > 0:
            AttributeDict = rewarded[0]
        else:
            return
        if self.last_dict == AttributeDict:
            return
        self.last_dict = AttributeDict
        
       
        event_name = AttributeDict['event']
        event_args_dict = AttributeDict['args']
        uIndex = event_args_dict['uBountyIndex']
        
        tokens = float(event_args_dict['tokenAmount']) / 10**8
        xDai = float(event_args_dict['weiAmount']) / 10**18
        
        tx_hash = AttributeDict['transactionHash'] 
        tx_hash_hex = hex(int.from_bytes(tx_hash, byteorder='big'))
        
        bounty_name = self.scrapeName(uIndex)
        if event_name == 'rewarded':

            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

            embed = discord.Embed(
                    title = f'Bounty Rewarded',
                    description = f'\nTask: [{bounty_name}](https://xdai.devcash.dev/bountyplatform/bounty/{uIndex})'
                                  f'\nRewards: `{tokens} DevCash` **|** `{xDai} xDai`'
                                  f'\n\n[View](https://blockscout.com/xdai/mainnet/tx/{tx_hash_hex}) on Blockscout'
                                   '\n\n[Explore more bounties](https://xdai.devcash.dev/bountyplatform)',
                    color = discord.Color.green(),
                    )
            embed.set_thumbnail(url='https://avatars.githubusercontent.com/u/23760508?v=4')
            embed.set_footer(text=f'{dt_string}')
        
            return embed

        if event_name == 'created':

            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

            embed = discord.Embed(
                    title = f'Bounty Created',
                    description = f'\nTask: [{self.scrapeName(uIndex)}](https://xdai.devcash.dev/bountyplatform/bounty/{uIndex})'
                                  f'\nRewards: `{tokens} DevCash` **|** `{xDai} xDai`'
                                  f'\n\n[Make a Submission](https://xdai.devcash.dev/bountyplatform/bounty/{uIndex})'
                                  '\n\n[Explore more bounties](https://xdai.devcash.dev/bountyplatform)',
                    color = discord.Color.blue(),
                    )
            embed.set_thumbnail(url='https://avatars.githubusercontent.com/u/23760508?v=4')
            embed.set_footer(text=f'{dt_string}')

            return embed
    
    @commands.check(isManager)
    @commands.group(brief='Send message to notification channels.')
    async def say(self, ctx, *message: typing.Union[str, discord.Embed]):
        if isinstance(message[0], str):
            message = " ".join(message)
            txt = True
        else:
            txt = False
        
        for channel_id in self.channel_ids:
            
            channel = self.bot.get_channel(channel_id)
            if channel == None:
                print(f'Can\'t find channel with id: {channel_id}')
                continue
            if txt == True:    
                await channel.send(message)
            else:
                await channel.send(embed=message)

    async def notify(self, embed:discord.Embed):
      
        for channel_id in self.channel_ids:
            
            channel = self.bot.get_channel(channel_id)
            if channel == None:
                print(f'Can\'t find channel with id: {channel_id}')
                continue

            await channel.send(embed=embed)

    async def eventCheck(self):

        print('\nListening for contract events...\n')
        await self.bot.wait_until_ready()

        while True:
            if self.status == 'IDLE':
                break
            try:
                for event in self.event_filter.get_new_entries():
                    
                    print('[NEW EVENT DETECTED]\n')
                    to_send = self.eventEmbed(event)
                    
                    if to_send != None:
                        
                        await self.notify(to_send)
            except:
                await self.ctx.send('**Refreshing connection...**')
                await self.stop(self.ctx)
                await self.start(self.ctx)
        
            await asyncio.sleep(5)

        print('\nStopped listening.\n')

    @commands.group(brief='Begin Listening')
    @commands.check(isManager)
    async def start(self, ctx, r=0):

        if self.status == 'LISTENING':
            await ctx.send('**Already listening.**')
            return
        
        if len(self.channel_ids) < 1:
            await ctx.send('**Notification channels not properly set up.\nUse `b.add` to add a notification channel.**')
            return
            
        
        try:
            self.ctx = ctx
            print('Fetching provider...')
            self.provider = Web3(Web3.WebsocketProvider(self.websocket, websocket_kwargs={'ping_interval': None}))
            print('Fetching contract...')
            self.contract = self.provider.eth.contract(address=self.contract_address, abi=self.abi)
            print('Creating filter...')
            self.event_filter = self.provider.eth.filter({"address": self.contract_address})
            print('Updating status...')
            self.status = 'LISTENING'
        except:
            print('Failed. Retrying...')
            await self.start(ctx, r)
            return
        if r:
            await ctx.send('**Listening for contract events...**')
        else:
            await ctx.send('**Conncection resumed.**')
        await self.eventCheck()

    @commands.group(brief='Stop Listening')
    @commands.check(isManager)
    async def stop(self, ctx, r=1):
        if self.status == 'LISTENING':
            self.status = 'IDLE'
            if r:
                await ctx.send('**Stopped listening.**')
        else:
            await ctx.send('**Already idle.**')

    @commands.group(brief='Add a notification channel.')
    @commands.check(isManager)
    async def add(self, ctx, channel:discord.TextChannel):

        print(channel)
        if channel.id in self.channel_ids:
            await ctx.send('**Already added.**')
            return

        self.channel_ids.append(channel.id)
        config['BOT']['NOTIFICATION_CHANNEL_IDS'] = config.get('BOT', f'NOTIFICATION_CHANNEL_IDS') + f' {channel.id}'
       
        with open(r'config.ini', 'w') as config_file:
            config.write(config_file)

        await ctx.send(f'**Notification channel added: **{channel.mention}')

    @commands.group(brief='Add a notification channel.')
    @commands.check(isManager)
    async def remove(self, ctx, channel:discord.TextChannel):

        if channel.id not in self.channel_ids:
            await ctx.send('**Could not find that channel.**')
            return

        self.channel_ids.remove(int(channel.id))

        config['BOT']['NOTIFICATION_CHANNEL_IDS'] = ' '.join(str(x) for x in self.channel_ids)
       
        with open(r'config.ini', 'w') as config_file:
            config.write(config_file)

        await ctx.send(f'**Notification channel removed: **{channel.mention}')

    @commands.group(brief='See notification channels.')
    async def channels(self, ctx):

        embed = discord.Embed(
                    title = f'Notification Channels',
                    description = f' ',
                    color = discord.Color.teal(),
                    )

        for i, channel_id in enumerate(self.channel_ids):
            channel = self.bot.get_channel(channel_id)
            if channel == None:
                continue
            embed.add_field(name=f'\u200b', value=f'**{i+1}.** {channel.mention}', inline = False)

        await ctx.send(embed=embed)
    

def setup(bot):
    bot.add_cog(Event_watcher(bot))