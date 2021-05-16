# Bounty Bot

Developed for Blockchain Developers United's bounty platofrm, this Discord bot can 
easily watch any ethereum contract for events and update discord channels in real-time.

## Setup

There are four fields in the config.ini file which the user must provide.
   
   1. **contract_address:** The ethereum address of the contract to be watched.
   2. **contract_abi_path:** Path to the ABI of the contract.
   3. **websocket_provider:** Websocket address (eg. wss://xdai.poanetwork.dev/wss) .  
   4. **bot_token:** Token for the bot account provided by Discord.
   5. **manager_ids:** Discord users with permission to use bot commands aside from server admins.

   Note: you can manually set **notification_channel_ids**, but I recommend
   doing it through the bot's commands to avoid setting up invalid channels.



## License
[MIT](https://choosealicense.com/licenses/mit/)