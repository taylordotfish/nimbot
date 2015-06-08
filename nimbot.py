#!/usr/bin/env python3
# Copyright (C) 2015 taylor.fish (https://github.com/taylordotfish)
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
  nimbot <host> <port> <channel> [-i] [-n nick]

Options:
  -i --identify  Identify with NickServ. Accepts a password through stdin.
  -n nick        The nickname to use [default: nimbot].
"""
from pyrcb import IrcBot
from mention import Mention
from docopt import docopt
from collections import defaultdict
from datetime import datetime, timedelta
from humanize import naturaltime
from threading import Event
import os
import re
import sys

# If modified, replace the source URL with one to the modified version.
help_message = """\
nimbot: The non-intrusive mailbot.
Source: https://github.com/taylordotfish/nimbot (AGPLv3 or later)
nimbot is {0}.
Usage:
  help     Show this help message.
  check    Manually check for mail.
  clear    Clear all mail without reading.
  enable   Enable nimbot.
  disable  Disable nimbot.
"""


class Nimbot(IrcBot):
    def __init__(self):
        super(Nimbot, self).__init__()
        self.msg_index = -1
        self.names = []

        self.mentions = defaultdict(list)
        self.enabled = defaultdict(lambda: True)
        self.save_event = Event()

        self.script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.prefs_path = os.path.join(self.script_dir, "prefs")
        self.read_prefs()

    def deliver(self, nickname, mentions):
        for mention in mentions:
            message = "[{0}] <{1}> {2}".format(
                naturaltime(mention.time), mention.sender, mention.message)
            self.send(nickname, message)
            print("[deliver -> {0}] {1}".format(nickname, message))

    def on_query(self, message, nickname):
        cmd = message.lower()
        nick = nickname.lower()
        print("[query] <{0}> {1}".format(nickname, message))

        if cmd == "help":
            help_lines = help_message.format(
                ["disabled", "enabled"][self.enabled[nick]]).splitlines()
            for line in help_lines:
                self.send(nick, line)
        elif cmd == "check":
            if not self.enabled[nick]:
                self.send(nick, "nimbot is disabled.")
            elif self.mentions[nick]:
                self.deliver(nick, self.mentions[nick])
                self.mentions[nick] = []
            else:
                self.send(nick, "No new mail.")
        elif cmd == "clear":
            self.mentions[nick] = []
            self.send(nick, "Mail cleared.")
        elif cmd == "enable" or cmd == "disable":
            if self.enabled[nick] != (cmd == "enable"):
                self.enabled[nick] = (cmd == "enable")
                self.mentions[nick] = []
                self.save_event.set()
            self.send(nick, "nimbot {0}d.".format(cmd))
        else:
            self.send(nick, '"/msg {0} help" for help.'.format(self.nickname))

    def on_message(self, message, nickname, target, is_query):
        if is_query:
            self.on_query(message, nickname)
            return

        self.msg_index += 1
        nick = nickname.lower()
        mentioned = defaultdict(bool)
        print("[{0}] <{1}> {2}".format(target, nickname, message))

        for name in self.names:
            if re.search(r"\b{0}\b".format(name), message):
                self.mentions[name].append(Mention(
                    message, nickname, self.msg_index, datetime.now()))
                mentioned[name] = True

        if mentioned:
            print("[mentioned] {0}".format(", ".join(mentioned)))
        if not self.enabled[nick]:
            return

        for mention in self.mentions[nick]:
            deliver = self.msg_index - mention.index > 50 and (
                      not mentioned[mention.sender] or
                      any(self.msg_index - m.index < 40
                          for m in self.mentions[nick]
                          if m.sender.lower() == mention.sender.lower()))
            if deliver:
                self.deliver(nick, [mention])
        self.mentions[nick] = []

    def on_join(self, nickname, channel):
        nick = nickname.lower()
        if nick == self.nickname.lower():
            return
        if nick not in self.names:
            self.names.append(nick)
            self.save_event.set()
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
            self.save_event.set()

    def on_names(self, channel, names):
        for name in [n.lower() for n in names]:
            if name not in self.names and name != self.nickname.lower():
                self.names.append(name)
                self.save_event.set()

    def read_prefs(self):
        if not os.path.isfile(self.prefs_path):
            open(self.prefs_path, "w").close()
            return

        with open(self.prefs_path) as f:
            for line in f:
                if not line.startswith("#"):
                    name = line.split()[0]
                    self.names.append(name)
                    self.enabled[name] = line.split()[1] == "True"

    def save_prefs(self):
        with open(self.prefs_path, "w") as f:
            print("# [name (lowercase)] [enabled (True/False)]", file=f)
            for name in self.names:
                print(name, self.enabled[name], file=f)

    def save_loop(self):
        while self.is_alive():
            self.save_event.clear()
            self.save_event.wait()
            self.save_prefs()


def main():
    args = docopt(__doc__)
    bot = Nimbot()
    bot.connect(args["<host>"], int(args["<port>"]))

    if args["--identify"]:
        print("Password: ", end="", file=sys.stderr)
        bot.password(input())
    bot.register(args["-n"])

    bot.join(args["<channel>"])
    bot.listen_async(bot.save_event.set)
    bot.save_loop()
    print("Disconnected from server.")

if __name__ == "__main__":
    main()
