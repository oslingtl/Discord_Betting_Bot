# Imports
import discord
from discord.ext import commands

import configparser
from datetime import datetime, timedelta

import pickle

################################################
# Classes

class BettingSystem():
    def __init__(self):
        self._users = {}
        self._curr_events = {}
        self._past_events = {}
        self._eventIds = 0
        self._valid_yes = ["y", "yes", "w", "win", "t", "true"]
        self._valid_no = ["n", "no", "l", "loss", "lose", "f", "false"]
        self._invalid_side_message = "result must be one of " + str(self._valid_yes + self._valid_no)
        self.MAX_BET = 5000
        self.MIN_BET = 1

    def add_event(self, description, odds = 2.00):
        event = BetEvent(self.next_event_id(), "\"" + description + "\"", odds)
        self._curr_events[event._id] = event
        return "<" + str(event._id) + "> " + event.information() + "\n"

    def resolve_event(self, event_id, result):
        side = False
        if any(sstring in result.lower() for sstring in self._valid_yes):
            side = True
        elif not(any(sstring in result.lower() for sstring in self._valid_no)):
            return self._invalid_side_message

        if not (event_id in self._curr_events):
            return "invalid eventId, try using <ongoing> to see current events."

        event = self._curr_events[event_id]
        event.payout(side)
        return event.information(True)

    def next_event_id(self):
        self._eventIds += 1
        return self._eventIds
    
    def list_current_events(self):
        output = ""
        for key in self._curr_events:
            event = self._curr_events[key]
            output += "<" + str(event._id) + "> " + event.information() + "\n"
        if output == "":
            output = "No ongoing events."
        return output

    def user_bet(self, event_id, user, result, amount):
        if not user.id in self._users:
            self._users[user.id] = User(user.display_name, user.id)

        person = self._users[user.id]
        if not person.has_money(amount):
            return person.name() + " does not have enough money for that bet! You have " + "$" + "{:.2f}".format(person.money()) + "."
        
        if amount > self.MAX_BET:
            return person.name() + " that amount is above the maximum of " + "$" + "{:.2f}".format(self.MAX_BET) + "."

        if amount < self.MIN_BET:
            return person.name() + " that amount is below the minimum of " + "$" + "{:.2f}".format(self.MIN_BET) + "."

        if not event_id in self._curr_events:
            return person.name() + " that event could not be found."

        side = True
        if any(sstring in result.lower() for sstring in self._valid_no): # self._valid_no in result:
            side = False
        elif not(any(sstring in result.lower() for sstring in self._valid_yes)) :
            return self._invalid_side_message
        event = self._curr_events[event_id]
        
        return event.add_bet(person, amount, side)

    def list_user_bets(self, user):
        if not user.id in self._users:
            self._users[user.id] = User(user.display_name, user.id)

        person = self._users[user.id]
        return person.list_bets()

    def list_user_past_bets(self, user):
        if not user.id in self._users:
            self._users[user.id] = User(user.display_name, user.id)

        person = self._users[user.id]
        return person.list_past_bets()
    
    def list_money_leaderboard(self):
        output = "LEADERBOARD ($):\n"
        i = 1
        users_sorted_by_money = sorted(self._users.items(), key=lambda x: x[1].money(), reverse=True)
        for (_id, user) in users_sorted_by_money:
            output +=  f"{str(i): >{2}}" + ". " + f"{user.name(): <{15}}" + " $" + f"{user.money(): <20.2f}\n"
            i += 1
        return output

    def list_best_pnl(self):
        output = "LEADERBOARD (PnL):\n"
        i = 1
        users_sorted_by_money = sorted(self._users.items(), key=lambda x: x[1].pnl(), reverse=True)
        for (_id, user) in users_sorted_by_money:
            neg = ""
            if user.pnl() < 0:
                neg = "-"
            output +=  f"{str(i): >{2}}" + ". " + f"{user.name(): <{15}} " + neg + "$" + f"{abs(user.pnl()): <20.2f}\n"
            i += 1
        return output

    def print_money(self, user):
        if not user.id in self._users:
            self._users[user.id] = User(user.display_name, user.id)

        person = self._users[user.id]
        return person.print_money()

    def daily(self, user):
        if not user.id in self._users:
            self._users[user.id] = User(user.display_name, user.id)

        person = self._users[user.id]
        return person.daily()

def custom_format(td):
    minutes, _seconds = divmod(td.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return '{:d}hr {:02d}m'.format(hours, minutes)

class User():
    def __init__(self, name, userId):
        self._id = userId
        self._name = name
        self._money = 10000
        self._current_bets = []
        self._past_bets = []
        self._daily = self._today() - timedelta(days=1)
        self._total_pnl = 0

    def name(self):
        return self._name

    def pnl(self):
        return self._total_pnl

    def money(self):
        return self._money

    def mention(self):
        return "<@" + str(self._id) + ">"

    def print_money(self):
        return self.name() + " has " + "$" + "{:.2f}".format(self.money()) + "."

    def list_bets(self):
        neg = ""
        if self._total_pnl < 0:
            neg = "-"
        output = self.name() + " has total PnL " + neg + "${:.2f}".format(abs(self._total_pnl)) + ".\n"
        if len(self._current_bets) > 0:
            output += "Live bets:\n"
        else:
            output += "No current bets.\n"
        for bet in self._current_bets:
            output += "\t" + bet.description() + "\n"
        return output
    
    def list_past_bets(self):
        neg = ""
        if self._total_pnl < 0:
            neg = "-"
        output = self.mention() + " has total PnL " + neg + "${:.2f}".format(abs(self._total_pnl)) + ".\n```Past bets:\n"
        for bet in self._past_bets:
            output += "\t" + bet.description() + "\n"
        return output + "```"

    def archive_bet(self, event_id):
        i = 0
        for bet in self._current_bets:
            if bet._underlying._id == event_id:
                self._past_bets.append(self._current_bets.pop(i))
            i += 1
        return

    def _today(self):
        dt = datetime.today()
        return datetime(dt.year, dt.month, dt.day)

    def daily(self):
        if self._today() - self._daily < timedelta(days=1):
            return self.name() + " you need to wait " + custom_format(timedelta(days=1) - (datetime.today() - self._daily)) + " more to retrieve your daily reward!"
        else:
            self._money += 100
            self._daily = self._today()
        return self.name() + " gained $100.00!"

    def has_money(self, amount):
        return self._money >= amount

    def win_bet(self, amount, odds):
        self._money += amount * odds
        self._total_pnl += amount * odds

    def lose_bet(self, amount):
        self._total_pnl -= amount

    def place_bet(self, betEvent, amount, side):
        assert(self.has_money(amount))
        bet = Bet(betEvent, self, amount, side)
        self._money -= amount
        self._current_bets.append(bet)
        return bet

class BetEvent():
    def __init__(self, eventId, description, odds):
        self._id = eventId
        self._description = description
        self._bets = []
        self._odds = odds #odds for "yes"
        self._resolved = False
        self._result = "n/a"
    
    def add_bet(self, user, amount, side):
        if user.has_money(amount):
            self._bets.append(user.place_bet(self, amount, side))
            return  user.name() + "'s $" + "{:.2f}".format(amount) + " bet placed successfully."
        else:
            return "insufficient funds " + user.name() + "!"

    def payout(self, winning_side):
        self._resolved = True
        self._result = winning_side
        for bet in self._bets:
            bet.resolve(winning_side, self.odds(bet.side()))
            bet.user().archive_bet(bet._underlying._id)
    
    def resolved(self):
            return self._resolved

    def odds(self, side):
        if side:
            return self._odds
        return self._odds/(self._odds-1)  # x/(x-1) is the other side

    def information(self, mention=False):
        output = ""
        if mention:
            output = "```"
        output += self._description + " @ $" + "{:.2f}".format(self.odds(True)) + "\n"
        if self.resolved():
            output += "RESULT: " + str(self._result).upper() + "\n"
        if mention:
            output += "```"
        for bet in self._bets:
            output += "\t" + bet.short_info(mention) + "\n"
        return output

class Bet():
    def __init__(self, event, user, amount, side):
        self._underlying = event
        self._user = user
        self._amount = amount
        self._side = side
        self._resolution = "n/a"

    def description(self):
        join = " that "
        if not(self.side()):
            join = " against "
        if self._resolution == "n/a":
            return self.user().name() + " bet " + "$" + "{:.2f}".format(self.amount()) + " @ $" + "{:.2f}".format(self.underlying().odds(self.side())) + join + self.underlying()._description
        else:
            return self.user().name() + " " + self._resolution + " " + "$" + "{:.2f}".format(self.amount() * self.underlying().odds(self.side())) + " betting" + join + self.underlying()._description

    def short_info(self, mention=False):
        join = "DOUBTER:  "
        if self.side():
            join = "BELIEVER: "

        name = self.user().name()
        if mention:
            name = self.user().mention()

        if self._resolution == "n/a":
            return join + self.user().name() + " bet " + "$" + "{:.2f}".format(self.amount())
        else:
            return join + name + " " + self._resolution + " " + "$" + "{:.2f}".format(self.winnings())

    def winnings(self):
        if self._resolution != "won":
            return self._amount
        return self.amount()*self._underlying.odds(self.side())

    def resolve(self, outcome, odds):
        if self._resolution != "n/a":
            raise Exception("oops - double resolve bet")

        if outcome == self.side():
            self._resolution = "won"
            self._user.win_bet(self.amount(), odds)
        else:
            self._resolution = "lost"
            self._user.lose_bet(self.amount())

    def side(self):
        return self._side

    def amount(self):
        return self._amount

    def user(self):
        return self._user

    def underlying(self):
        return self._underlying

# wraps the text in ```<text>``` for ascii table output
def wrap(text):
    return "```" + text + "```"

################################################
# Setup
CONFIG = 'config.ini'
parser = configparser.ConfigParser()
parser.read(CONFIG)
TOKEN = str(parser['DISCORD']['token'])
PREFIX = str(parser['DISCORD']['prefix'])

#intents - todo
# intents = discord.Intents.none()
# intents.messages = True
# intents.members = True
#reactions

help_command = commands.DefaultHelpCommand(
    no_category = 'Commands'
)
client = commands.Bot(case_insensitive=True, command_prefix=commands.when_mentioned_or(PREFIX), description="Simple betting bot to gamble on the outcome of admin created events.", help_command = help_command)#, intents=intents)

#### PICKLE (object persistence)
PICKLE_FILENAME = 'betting_system.pickle'
try:
    with open(PICKLE_FILENAME, 'rb') as handle:
        client.system = pickle.load(handle)
    print("Successfully loaded " + PICKLE_FILENAME)
except:
    print("Couldn't find pickle file " + PICKLE_FILENAME)
    client.system = BettingSystem()

# Startup Information
@client.event
async def on_ready():
    print('Connected to bot: {}'.format(client.user.name))
    print('Bot ID: {}'.format(client.user.id))

################################################
# BETTING

# Create event
@client.command(aliases=["e"], usage="<odds> <description>", help="Allows a BettingAdmin to create an event for users to bet on.\ne.g. event 2 Oslo gets a penta this game.")
@commands.has_role("BettingAdmin")
async def event(ctx, odds, *, description):
    await ctx.send(wrap(client.system.add_event(description, float(odds))))

# Resolve event
@client.command(aliases=["r"], usage="<eventId> <result (yes/no)>", help="Allows a BettingAdmin to resolve an event that users have bet on.\ne.g. resolve 21 y.")
@commands.has_role("BettingAdmin")
async def resolve(ctx, event_id, result):
    await ctx.send(client.system.resolve_event(int(event_id), result))

# Bet on an event
@client.command(aliases=["b"], usage="<eventId> <result (yes/no)> <amount>", help="Allows any user to bet on an ongoing event.\ne.g. bet 1 y 100.")
async def bet(ctx, event_id, result, amount):
    await ctx.send(wrap(client.system.user_bet(int(event_id), ctx.author, result, float(amount))))

################################################
# See current money
@client.command(aliases=["m"], usage="", help="Allows any user to see their current money supply.")
async def money(ctx):
    await ctx.send(wrap(client.system.print_money(ctx.author)))

# Get daily money reward
@client.command(aliases=["d"], usage="", help="Retrieve daily login reward.")
async def daily(ctx):
    await ctx.send(wrap(client.system.daily(ctx.author)))

################################################
# System information

# list all ongoing events
@client.command(aliases=["list", "o", "live"], usage="", help="Allows any user to see live events and bets.")
async def ongoing(ctx):
    await ctx.send(wrap(client.system.list_current_events()))

# list a users current bets
@client.command(aliases=["bs"], usage="", help="Allows any user to see their current bets.")
async def bets(ctx):
    await ctx.send(wrap(client.system.list_user_bets(ctx.author)))

# A user's betting history
@client.command(aliases=["h", "hist"], usage="", help="Allows any user to see their past betting history.")
async def history(ctx):
    await ctx.send(client.system.list_user_past_bets(ctx.author))

# A user's betting history
@client.command(aliases=["top", "leader", "l"], usage="", help="Ranks everyone by money.")
async def leaderboard(ctx):
    await ctx.send(wrap(client.system.list_money_leaderboard()))

# A user's betting history
@client.command(aliases=["allpnl", "pnl", "p"], usage="", help="Ranks everyone by profit/loss.")
async def bestpnl(ctx):
    await ctx.send(wrap(client.system.list_best_pnl()))

# Store all user data (serialized)
@client.command(aliases=["s", "shutdown"], usage="", help="Save current system state to file.")
async def save(ctx):
    with open(PICKLE_FILENAME, 'wb') as handle:
        pickle.dump(client.system, handle, protocol=pickle.HIGHEST_PROTOCOL)
    await ctx.send(wrap("Data saved successfully"))

@client.command(aliases=["latency"], usage="", help="Show bot latency")
async def ping(ctx):
    await ctx.send(wrap(str(round(client.latency*1000,2)) + "ms"))

# test
@client.command()
async def rage(ctx):
    await ctx.send(wrap('Sucks to suck idiots'))

client.run(TOKEN)
