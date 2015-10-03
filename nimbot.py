#!/usr/bin/env python3
# Copyright (C) 2015 taylor.fish (https://github.com/taylordotfish)
# Copyright (C) 2015 nc Krantz-Fire (https://pineco.net/)
# Improved password input and .gitignore.
#
# This file is part of nimbot.
#
# nimbot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# nimbot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with nimbot.  If not, see <http://www.gnu.org/licenses/>.
"""
Usage:
  nimbot [options] <host> <port> <channel>
  nimbot -h | --help | --version

Options:
  -n <nickname>    The nickname to use [default: nimbot].
  --check-id       Force users registered with NickServ to be identified.
                   Server must support account-notify.
  --force-id       Force all users to be identified with NickServ.
                   Server must support account-notify.
  --password       Set a connection password. Can be used to identify
                   with NickServ. Uses getpass() if stdin is a TTY.
  --getpass        Force password to be read with getpass().
  --loop           Restart if disconnected from the IRC server.
  --ssl            Use SSL/TLS to connect to the IRC server.
  --cafile <file>  Use the specified list of CA root certificates to verify
                   the IRC server's certificate. System CA certificates will
                   be used if not provided.
"""
from pyrcb import IRCBot, IStr
from mention import Mention
from user import User, Users
from docopt import docopt
from humanize import naturaltime
from datetime import datetime
from getpass import getpass
import os
import re
import sys
import threading

__version__ = "0.1.6"

# If modified, replace the source URL with one to the modified version.
help_message = """\
nimbot: The Non-Intrusive Mailbot. (v{0})
Source: https://github.com/taylordotfish/nimbot (AGPLv3 or later)
To send mail, begin your message with "<nickname>:".
You can specify multiple nicknames, separated by commas or colons.
nimbot is {{0}}.
Usage:
  help     Show this help message.
  check    Manually check for mail.
  clear    Clear mail without reading.
  enable   Enable nimbot.
  disable  Disable nimbot. You'll still receive private
           messages sent when you're offline.
  send     Send a private message.
           Usage: send <nickname> <message>
""".format(__version__)

script_dir = os.path.dirname(os.path.realpath(__file__))
users_path = os.path.join(script_dir, "saved-users")
mentions_path = os.path.join(script_dir, "saved-mentions")


class Nimbot(IRCBot):
    def __init__(self, check_id, force_id, **kwargs):
        super(Nimbot, self).__init__(**kwargs)
        self.check_id = check_id
        self.force_id = force_id
        self.msg_index = 0
        self.users = Users()

        self.use_acc = True
        self.use_status = True
        self.read_users()
        self.read_mentions()

    def deliver(self, nickname, mentions):
        for mention in mentions:
            message = "[{0}] <{1}> {2}".format(
                naturaltime(mention.time), mention.sender, mention.message)
            if mention.private:
                message = "[private] " + message
            self.send(nickname, message)
            print("[deliver -> {0}] {1}".format(nickname, message))

    def on_query(self, message, nickname):
        def help():
            response = help_message.format(
                ["disabled", "enabled"][user.enabled])
            for line in response.splitlines():
                self.send(nickname, line)

        def check():
            if not user.enabled:
                self.send(nickname, "nimbot is disabled.")
            elif user.mentions:
                self.deliver(nickname, user.mentions)
                user.clear_mentions()
            else:
                self.send(nickname, "No new mail.")

        def clear():
            user.clear_mentions()
            self.send(nickname, "Mail cleared.")

        def enable():
            user.enabled = True
            self.send(nickname, "nimbot enabled.")

        def disable():
            user.clear_mentions()
            user.enabled = False
            self.send(nickname, "nimbot disabled.")

        def send():
            args = message.split(" ", 2)[1:]
            if len(args) < 2:
                other()
                return

            target_nick, msg = args
            if target_nick not in self.users:
                self.send(nickname, "You can only send private messages "
                                    "to users nimbot is aware of.")
            elif target_nick in self.nicklist[self.channels[0]]:
                self.send(nickname, "{0} is online. Send them a regular "
                                    "private message.".format(target_nick))
            else:
                target = self.users[target_nick]
                target.mentions.append(Mention(
                    msg, user, target, 0, datetime.now(), private=True))
                self.send(nickname, "Message sent.")

        def other():
            self.send(nickname, 'Type "help" for help.')

        command = IStr(message.split(" ", 1)[0])
        user = self.users[nickname]
        print("[{2}] [query] <{0}> {1}".format(
            nickname, message, datetime.now().replace(microsecond=0)))

        # Dispatch command to the appropriate function,
        # or other() if not found.
        function = {
            "help": help, "check": check, "clear": clear,
            "enable": enable, "disable": disable, "send": send
        }.get(command, other)

        if nickname not in self.nicklist[self.channels[0]]:
            self.send(nickname, "Please join the channel monitored "
                                "by nimbot first.")
        elif user.id_pending:
            self.send(nickname, "Your nickname is being identified. "
                                "Please try again in a few seconds.")
        elif not user.identified:
            self.send(nickname, "Please identify with NickServ to use nimbot.")
        else:
            function()
            if user.mentions:
                self.send(nickname, "You have unread messages. "
                                    'Type "check" to read.')

    def on_message(self, message, nickname, channel, is_query):
        if is_query:
            self.on_query(message, nickname)
            return

        sender = self.users[nickname]
        self.msg_index += 1
        mentioned = []
        print("[{3}] [{0}] <{1}> {2}".format(
            channel, nickname, message, datetime.now().replace(microsecond=0)))

        for user in self.users.values():
            if not user.enabled or user == sender:
                continue
            # Check if user is mentioned.
            is_mentioned = re.match(r"([^:, ]+[:,] ?)*{0}[:,]".format(
                re.escape(user.nickname)), message, re.I)
            if is_mentioned:
                user.mentions.append(Mention(
                    message, sender, user, self.msg_index, datetime.now()))
                mentioned.append(user)

        if mentioned:
            print("[mentioned] {0}".format(", ".join(map(str, mentioned))))
        if not sender.enabled:
            return

        mentions = []
        for mention in sender.mentions:
            is_old = self.msg_index - mention.index > 50
            has_reply = mention.sender in mentioned
            new_msg_exists = any(self.msg_index - m.index < 40 and
                                 m.sender == mention.sender
                                 for m in sender.mentions)
            if is_old and (not has_reply or new_msg_exists):
                mentions.append(mention)

        self.deliver(nickname, mentions)
        sender.clear_mentions()

    def on_join(self, nickname, channel):
        if nickname == self.nickname:
            return
        self.users[nickname]
        self.identify(nickname)

    def on_nick(self, nickname, new_nickname):
        user = self.users[new_nickname]
        user.enabled = self.users[nickname].enabled
        self.identify(new_nickname)

    def on_names(self, channel, names):
        for name in names:
            if name != self.nickname:
                user = self.users[name]
                user.deliver_on_id = False
                self.identify(name)

    # ===================
    # User identification
    # ===================

    def identify(self, nickname):
        user = self.users[nickname]
        if self.check_id or self.force_id:
            user.id_pending = True
            user.identified = False
            print("Identifying {0}...".format(nickname))
            if self.use_acc:
                self.send("NickServ", "ACC {0} {0}".format(nickname))
            if self.use_status:
                self.send("NickServ", "STATUS {0}".format(nickname))
        else:
            user.identified = True
            self.on_identified(user)

    def on_identified(self, user):
        if user.nickname in self.nicklist[self.channels[0]]:
            user.valid = True
            if user.enabled and user.deliver_on_id:
                self.deliver(user.nickname, user.mentions)
                user.clear_mentions()

    def on_notice(self, message, nickname, channel, is_query):
        if nickname != "NickServ":
            return

        match = None
        if self.use_acc:
            match = re.match("([^ ]*) -> [^ ]* ACC (\d)", message)
            if match:
                self.use_status = False
                nick, status = match.groups()

        if self.use_status:
            match = re.match("STATUS ([^ ]*) (\d) ([^ ]*)", message)
            if match:
                self.use_acc = False
                nick, status, account = match.groups()
                if status == "3" and nick != account:
                    status = "1"

        if match:
            user = self.users[nick]
            user.identified = (
                status == "3" or status == "0" and not self.force_id)
            user.id_pending = False

            id_str = "identified" if user.identified else "not identified"
            print("{0} {1}. (ACC/STATUS {2})".format(nick, id_str, status))
            if user.identified:
                self.on_identified(user)
            user.deliver_on_id = True

    def on_raw(self, nickname, command, args):
        if command == "ACCOUNT":
            print("Account status for {0} changed.".format(nickname))
            self.identify(nickname)

    # ===========
    # Preferences
    # ===========

    def print_users(self, file=sys.stderr):
        users = (u for u in self.users.values() if u.valid)
        for user in users:
            print(user.to_string(), file=file)

    def print_mentions(self, file=sys.stderr):
        users = (u for u in self.users.values() if u.valid)
        mentions = (m for u in users for m in u.mentions)
        for mention in mentions:
            offset = 0 if mention.private else self.msg_index
            print(mention.to_string(offset), file=file)

    def save_users(self):
        with open(users_path, "w") as f:
            print("# <nickname> <enabled (True/False)>", file=f)
            self.print_users(file=f)

    def save_mentions(self):
        with open(mentions_path, "w") as f:
            self.print_mentions(file=f)

    def read_users(self):
        if not os.path.isfile(users_path):
            return
        with open(users_path) as f:
            for line in f:
                if not line.startswith("#"):
                    user = User.from_string(line.rstrip())
                    self.users[user.nickname] = user

    def read_mentions(self):
        if not os.path.isfile(mentions_path):
            return
        with open(mentions_path) as f:
            for line in f:
                mention = Mention.from_string(line, self.users)
                mention.target.mentions.append(mention)


def command_loop(bot):
    while True:
        try:
            command = input()
        except EOFError:
            break
        if command == "users":
            bot.print_users()
        elif command == "mentions":
            bot.print_mentions()
        else:
            print("Unknown command.", file=sys.stderr)
            print('Type "users" or "mentions".', file=sys.stderr)


def start(bot, args, password):
    bot.connect(args["<host>"], int(args["<port>"]),
                use_ssl=args["--ssl"], ca_certs=args["--cafile"])

    if password:
        bot.password(password)
    bot.register(args["-n"])

    if args["--check-id"] or args["--force-id"]:
        bot.send_raw("CAP", ["REQ", "account-notify"])
        bot.send_raw("CAP", ["END"])

    bot.join(args["<channel>"])
    bot.listen()
    print("Disconnected from server.")


def main():
    args = docopt(__doc__, version=__version__)
    password = None
    if args["--password"]:
        print("Password: ", end="", file=sys.stderr, flush=True)
        use_getpass = sys.stdin.isatty() or args["--getpass"]
        password = getpass("") if use_getpass else input()
        if not use_getpass:
            print("Received password.", file=sys.stderr)

    bot = Nimbot(args["--check-id"], args["--force-id"])
    t = threading.Thread(target=command_loop, args=[bot])
    t.daemon = True
    t.start()

    try:
        start(bot, args, password)
        while args["--loop"]:
            start(bot, args, password)
    finally:
        bot.save_users()
        bot.save_mentions()

if __name__ == "__main__":
    main()
