#!/usr/bin/env python3
# Copyright (C) 2015 nickolas360 (https://github.com/nickolas360)
# Copyright (C) 2015 Nathan Krantz-Fire (https://github.com/zippynk)
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
  nimbot <host> <port> <channel> [options]
  nimbot -h | --help

Options:
  -h --help      Display this help message.
  -i --identify  Identify with NickServ. Accepts a password through stdin.
  -n NICKNAME    The nickname to use [default: nimbot].
"""
from pyrcb import IrcBot
from mention import Mention
from docopt import docopt
from collections import defaultdict
from datetime import datetime
from humanize import naturaltime
from getpass import getpass
import os
import re
import sys
import threading

# If modified, replace the source URL with one to the modified version.
help_message = """\
nimbot: The non-intrusive mailbot.
Source: https://github.com/nickolas360/nimbot (AGPLv3 or later)
To send mail, begin your message with "[nickname]:".
You can specify multiple nicknames, separated by commas or colons.
nimbot is {0}.
Usage:
  help     Show this help message.
  check    Manually check for mail.
  clear    Clear all non-private mail without reading.
  enable   Enable nimbot.
  disable  Disable nimbot.
  send     Send a private message.
           Syntax: send [nickname] [message]
"""


class Nimbot(IrcBot):
    def __init__(self):
        super(Nimbot, self).__init__()
        self.msg_index = 0
        self.names = []

        self.mentions = defaultdict(list)
        self.private_mentions = defaultdict(list)
        self.enabled = defaultdict(lambda: True)

        self.script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.prefs_path = os.path.join(self.script_dir, "prefs")
        self.mentions_path = os.path.join(self.script_dir, "saved_mentions")

        self.read_prefs()
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
        cmd = message.split(" ", 1)[0].lower()
        nick = nickname.lower()
        print("[{2}] [query] <{0}> {1}".format(
            nickname, message, datetime.now().replace(microsecond=0)))

        if cmd == "help":
            help_lines = help_message.format(
                ["disabled", "enabled"][self.enabled[nick]]).splitlines()
            for line in help_lines:
                self.send(nick, line)
        elif cmd == "check":
            if not self.enabled[nick]:
                self.send(nick, "nimbot is disabled.")
            elif self.mentions[nick] or self.private_mentions[nick]:
                self.deliver(nick, self.mentions[nick])
                self.deliver(nick, self.private_mentions[nick])
                self.mentions[nick] = []
                self.private_mentions[nick] = []
            else:
                self.send(nick, "No new mail.")
        elif cmd == "clear":
            self.mentions[nick] = []
            self.send(nick, "Mail cleared.")
        elif cmd == "enable" or cmd == "disable":
            if self.enabled[nick] != (cmd == "enable"):
                self.enabled[nick] = (cmd == "enable")
                self.mentions[nick] = []
            self.send(nick, "nimbot {0}d.".format(cmd))
        elif cmd == "send" and len(message.split(" ", 2)) == 3:
            target, msg = message.split(" ", 2)[1:]
            if not self.enabled[target]:
                self.send(nick, "{0} has disabled nimbot.".format(target))
            else:
                self.private_mentions[target].append(Mention(
                    msg, nickname, target, 0, datetime.now(), private=True))
                self.send(nick, "Message sent.")
        else:
            self.send(nick, '"/msg {0} help" for help.'.format(self.nickname))

        if self.mentions[nick] or self.private_mentions[nick]:
            self.send(nick, 'You have unread messages. "/msg {0} check" '
                            'to read.'.format(self.nickname))

    def on_message(self, message, nickname, target, is_query):
        if is_query:
            self.on_query(message, nickname)
            return

        self.msg_index += 1
        nick = nickname.lower()
        mentioned = defaultdict(bool)
        print("[{3}] [{0}] <{1}> {2}".format(
            target, nickname, message, datetime.now().replace(microsecond=0)))

        for name in self.names:
            if not self.enabled[name] or name == nick:
                continue
            if re.match(r"(\W*{0}\W|([a-z0-9\\\-[\]{{}}_^`]+[:,] ?)+{0}\W)"
                        .format(re.escape(name)), message, re.I):
                self.mentions[name].append(Mention(
                    message, nickname, name, self.msg_index, datetime.now()))
                mentioned[name] = True

        if mentioned:
            print("[mentioned] {0}".format(", ".join(mentioned)))
        if not self.enabled[nick]:
            return

        for mention in self.mentions[nick]:
            old_message = self.msg_index - mention.index > 50
            is_reply = mentioned[mention.sender]
            new_msg_exists = any(self.msg_index - m.index < 40 and
                                 m.sender.lower() == mention.sender.lower()
                                 for m in self.mentions[nick])
            if old_message and (not is_reply or new_msg_exists):
                self.deliver(nick, [mention])

        self.deliver(nick, self.private_mentions[nick])
        self.mentions[nick] = []
        self.private_mentions[nick] = []

    def on_join(self, nickname, channel, is_self):
        nick = nickname.lower()
        if is_self:
            return
        if nick not in self.names:
            self.names.append(nick)
            return
        if self.enabled[nick]:
            self.deliver(nick, self.mentions[nick])
            self.mentions[nick] = []

    def on_nick(self, nickname, new_nickname, is_self):
        if is_self:
            return
        nick = nickname.lower()
        new_nick = new_nickname.lower()
        if new_nick not in self.names:
            self.names.append(new_nick)
            self.enabled[new_nick] = self.enabled[nick]

    def on_names(self, channel, names):
        for name in [n.lower() for n in names]:
            if name not in self.names and name != self.nickname.lower():
                self.names.append(name)

    def print_prefs(self, file=sys.stdout):
        for name in self.names:
            print(name, self.enabled[name], file=file)

    def print_mentions(self, file=sys.stdout):
        for mentions in self.mentions.values():
            for m in mentions:
                print(m.to_string(self.msg_index), file=file)
        for mentions in self.private_mentions.values():
            for m in mentions:
                print(m.to_string(), file=file)

    def save_prefs(self):
        with open(self.prefs_path, "w") as f:
            print("# [name (lowercase)] [enabled (True/False)]", file=f)
            self.print_prefs(file=f)

    def save_mentions(self):
        with open(self.mentions_path, "w") as f:
            self.print_mentions(file=f)

    def read_prefs(self):
        if not os.path.isfile(self.prefs_path):
            return
        with open(self.prefs_path) as f:
            for line in f:
                if not line.startswith("#"):
                    name, enabled = line.rstrip().split(" ", 1)
                    self.names.append(name)
                    self.enabled[name] = enabled == "True"

    def read_mentions(self):
        if not os.path.isfile(self.mentions_path):
            return
        with open(self.mentions_path) as f:
            for line in f:
                m = Mention.from_string(line)
                if not m.private:
                    self.mentions[m.target].append(m)
                else:
                    self.private_mentions[m.target].append(m)


def command_loop(bot):
    while True:
        line = input()
        if line == "prefs":
            bot.print_prefs(file=sys.stderr)
        elif line == "mentions":
            bot.print_mentions(file=sys.stderr)
        else:
            print('Unknown command. Type "prefs" or "mentions".',
                  file=sys.stderr)


def main():
    args = docopt(__doc__)
    bot = Nimbot()
    bot.connect(args["<host>"], int(args["<port>"]))

    if args["--identify"]:
        bot.password(getpass("Password: ", stream=sys.stderr))
        print("Received password.", file=sys.stderr)
    bot.register(args["-n"])
    bot.join(args["<channel>"])

    t = threading.Thread(target=command_loop, args=[bot])
    t.daemon = True
    t.start()

    try:
        bot.listen()
    except KeyboardInterrupt:
        return
    finally:
        bot.save_prefs()
        bot.save_mentions()
    print("Disconnected from server.")

if __name__ == "__main__":
    main()
