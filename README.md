# Discord_Betting_Bot
Super simple discord betting bot to manage custom events with an imaginary currency in a discord with friends.

## Setup
Create a file `config.ini` in the root folder with structure:
'''
[DISCORD]
token = PUTYOURTOKENHERE 
prefix = ~
'''

## Usage
Use `~help` to find available commands, and `~help <command>` for detailed usage information. A user must be set up with the role `BettingAdmin` in the server to administrate the bot, such as creating and resolving events.

## Shutdown
System state can be saved before shutting the bot down with the `~save` command, which will create a pickle file which will be reloaded when the bot restarts.