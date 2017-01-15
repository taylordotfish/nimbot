#!/usr/bin/env python3
# Copyright (C) 2015-2017 taylor.fish <contact@taylor.fish>
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
  nimbot [options] <host> <port> <nickname> <channel>
  nimbot -h | --help | --version

Options:
  -c --check-id    Force users registered with NickServ to be identified.
                   Server must support account-notify.
  -f --force-id    Force all users to be identified with NickServ.
                   Server must support account-notify.
  -p --password    Set a connection password. Can be used to identify
                   with NickServ. Uses getpass() if stdin is a TTY.
  --getpass        Force password to be read with getpass().
  --loop           Restart if disconnected from the IRC server.
  --ssl            Use SSL/TLS to connect to the IRC server.
  -v --verbose     Display communication with the IRC server.
"""
from mentions import Mention, MailUser
from pyrcb2 import IRCBot, Event, event_decorator, Status, astdio
import mentions

from humanize import naturaltime
from datetime import datetime
from docopt import docopt
from getpass import getpass
import os
import re
import sys

__version__ = "0.3.1"

# If modified, replace the source URL with one to the modified version.
HELP_MESSAGE = """\
nimbot: The Non-Intrusive Mailbot. (v%s)
Source: https://github.com/taylordotfish/nimbot (AGPLv3 or later)
To send mail, begin your message with "<nickname>: ".
You can specify multiple nicknames separated by commas or colons.
(Users must have {0} enabled or be offline to receive the message.)
{0} is {1}. Commands:
  help: Show this help message.
  check: Manually check for mail.
  clear: Clear mail without reading.
  enable: Enable {0}.
  disable: Disable {0}. You'll still receive messages sent when you're offline.
  send <nickname> <message>: Send a private message.
  enabled? [<nickname>]: Check if {0} is enabled for you or another user.
""" % __version__

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
USERS_PATH = os.path.join(SCRIPT_DIR, "saved-users")
MENTIONS_PATH = os.path.join(SCRIPT_DIR, "saved-mentions")


class Event(Event):
    @event_decorator
    def query_command(command):
        return (Event, ("query_command", command))


class Nimbot:
    def __init__(self, check_id, force_id, channel, **kwargs):
        self.bot = IRCBot(**kwargs)
        self.bot.load_events(self)

        self.channel = channel
        self.check_id = check_id or force_id
        self.force_id = force_id
        if check_id or force_id:
            self.bot.track_known_id_statuses = True

        self.msg_index = 0
        self.mail_users = mentions.MailUserDict()

        # If more than this number of messages are after
        # a given message, the message is considered old.
        self.old_message = 7  # 50
        # If fewer than this number of messages are after
        # a given message, the message is considered new.
        self.new_message = 3  # 40

        self.read_users()
        self.read_mentions()

    def deliver(self, nickname, mentions):
        for mention in mentions:
            message = "[{}] <{}> {}".format(
                naturaltime(mention.time), mention.sender, mention.message)
            if mention.private:
                message = "[private] " + message
            self.bot.privmsg(nickname, message)
            log("[deliver -> {}] {}".format(nickname, message))

    @Event.query_command("help")
    def on_cmd_help(self, user, message):
        response = HELP_MESSAGE.format(
            self.bot.nickname, "enabled" if user.enabled else "disabled",
        ).splitlines()
        for line in response:
            self.bot.privmsg(user, line)

    @Event.query_command("check")
    def on_cmd_check(self, user, message):
        if user.mentions:
            self.deliver(user, user.mentions)
            user.clear_mentions()
        elif user.enabled:
            self.bot.privmsg(user, "No new mail.")
        else:
            self.bot.privmsg(
                user, "No new mail. (Note: %s is disabled.)"
                % self.bot.nickname,
            )

    @Event.query_command("clear")
    def on_cmd_clear(self, user, message):
        user.clear_mentions()
        self.bot.privmsg(user, "Mail cleared.")

    @Event.query_command("enable")
    def on_cmd_enable(self, user, message):
        user.enabled = True
        self.bot.privmsg(user, "%s enabled." % self.bot.nickname)

    @Event.query_command("disable")
    def on_cmd_disable(self, user, message):
        user.enabled = False
        self.bot.privmsg(
            user, "%s disabled. You'll still receive messages sent to you "
            "when you're offline." % self.bot.nickname,
        )

    @Event.query_command("send")
    def on_cmd_send(self, user, message):
        args = message.split(None, 1)
        if len(args) < 2:
            self.on_cmd_other(user, message)
            return
        target, msg = args
        if target not in self.mail_users:
            self.bot.privmsg(
                user, "You can send private messages only to users "
                "%s is aware of." % self.bot.nickname,
            )
        elif target in self.bot.users[self.channel]:
            self.bot.privmsg(
                user, "%s is online. Send them a regular "
                "private message." % target,
            )
        else:
            target_user = self.mail_users[target]
            target_user.mentions.append(Mention(
                msg, user, target_user, 0, datetime.now(), private=True))
            self.bot.privmsg(user, "Message sent.")

    @Event.query_command("enabled?")
    def on_cmd_enabled(self, user, message):
        if " " in message:
            self.on_cmd_other(user, message)
            return
        if not message:
            state = "enabled" if user.enabled else "disabled"
            self.bot.privmsg(
                user, "You have %s %s." % (self.bot.nickname, state))
            return
        target = message
        if target not in self.mail_users:
            self.bot.privmsg(
                user, "%s is not aware of that user." % self.bot.nickname)
            return
        target_user = self.mail_users[target]
        state = "enabled" if target_user.enabled else "disabled"
        self.bot.privmsg(
            user, "%s has %s %s." % (target, self.bot.nickname, state))

    @Event.query_command("other")
    def on_cmd_other(self, user, message):
        self.bot.privmsg(user, 'Type "help" for help.')

    @Event.privmsg
    async def on_privmsg(self, sender, channel, message):
        if channel is None:
            await self.on_query(sender, message)
            return
        sender_user = self.mail_users[sender]
        self.msg_index += 1
        log("[{}] <{}> {}".format(channel, sender, message))

        mentioned_users = list(filter(None, (
            self.mail_users.get(n.strip(":,")) for n in
            re.match(r"([^:, ]+[:,] +)*", message).group(0).split())))

        for user in mentioned_users:
            if user.enabled and user != sender_user:
                user.mentions.append(Mention(
                    message, sender_user, user, self.msg_index,
                    datetime.now()))

        if mentioned_users:
            log("[mentioned] %s" % ", ".join(map(str, mentioned_users)))
        if not sender_user.enabled and sender in self.bot.users[self.channel]:
            return

        identified = await self.identify_user(sender)
        mentions = []
        keep_mentions = []

        for mention in sender_user.mentions:
            access_allowed = identified or (
                not mention.private and
                mention.index > sender_user.identified_below)
            is_old = self.msg_index - mention.index > self.old_message
            has_reply = mention.sender in mentioned_users
            new_msg_exists = any(
                self.msg_index - m.index < self.new_message and
                m.sender == mention.sender for m in sender_user.mentions)
            if not access_allowed:
                keep_mentions.append(mention)
            elif is_old and (not has_reply or new_msg_exists):
                mentions.append(mention)

        self.deliver(sender, mentions)
        sender_user.mentions = keep_mentions

    async def on_query(self, sender, message):
        log("[query] <{}> {}".format(sender, message))
        if sender not in self.mail_users:
            self.bot.privmsg(
                sender, "Please join the channel monitored by %s."
                % self.bot.nickname)
            return
        identified = await self.identify_user(sender, communicate=True)
        if not identified:
            return
        mail_user = self.mail_users[sender]
        mail_user.save = True

        command, message, *_ = message.split(None, 1) + ["", ""]
        event_id = ("query_command", command)
        if not self.bot.any_event_handlers(Event, event_id):
            event_id = ("query_command", "other")
        await self.bot.call(Event, event_id, mail_user, message)

    @Event.join
    async def on_join(self, sender, channel):
        if sender == self.bot.nickname:
            for nickname in self.bot.users[channel]:
                if nickname != self.bot.nickname:
                    self.mail_users[nickname]
            return
        self.mail_users[sender]
        await self.identify_user(sender)
        if not self.check_id:
            self.on_id_status_known(sender, Status.logged_in)

    @Event.nick
    async def on_nick(self, old_nickname, new_nickname):
        if new_nickname == self.bot.nickname:
            return
        old_user = self.mail_users[old_nickname]
        if new_nickname not in self.mail_users:
            new_user = self.mail_users[new_nickname]
            new_user.enabled = old_user.enabled
        await self.identify_user(new_nickname)
        if not self.check_id:
            self.on_id_status_known(new_nickname, Status.logged_in)

    async def identify_user(self, nickname, communicate=False):
        def privmsg(*args, **kwargs):
            if not communicate:
                return
            return self.bot.privmsg(*args, **kwargs)

        if not self.check_id:
            return True
        if not self.bot.is_id_status_synced(nickname):
            msg = "Checking your account; please wait..."
            if nickname not in self.bot.users[self.channel]:
                msg += " (Join the channel monitored by %s to prevent this.)"
                msg %= self.bot.nickname
            privmsg(nickname, msg)

        result = await self.bot.get_id_status(nickname)
        if not result.success:
            privmsg(nickname, "Error: Could not check your account.")
            return False

        id_status = result.value
        if id_status == Status.logged_in:
            return True
        if id_status != Status.no_account or self.force_id:
            privmsg(nickname, "Please log in with NickServ.")
            return False
        if self.bot.is_id_status_synced(nickname):
            return True
        if self.bot.is_tracking_known_id_statuses:
            privmsg(nickname, (
                "Please either join the channel monitored by %s, "
                "or log in with NickServ." % self.bot.nickname))
            return False
        privmsg(nickname, "Please log in with NickServ.")
        return False

    @Event.id_status_known
    def on_id_status_known(self, nickname, status):
        user = self.mail_users[nickname]
        user.identified_below = self.msg_index
        if user.enabled and self.identified_with_status(status):
            self.deliver(user, user.mentions)
            user.clear_mentions()

    def identified_with_status(self, status):
        if not self.check_id:
            return True
        if status == Status.logged_in:
            return True
        if status == Status.no_account and not self.force_id:
            return True
        return False

    def serialize_users(self):
        users = (u for u in self.mail_users.values() if u.save)
        for user in users:
            yield user.to_string()

    def serialize_mentions(self):
        users = (u for u in self.mail_users.values() if u.save)
        mentions = (m for u in users for m in u.mentions)
        for mention in mentions:
            offset = 0 if mention.private else self.msg_index
            yield mention.to_string(offset)

    def save_users(self):
        with open(USERS_PATH, "w") as f:
            print("# <nickname> <enabled (True/False)>", file=f)
            for line in self.serialize_users():
                print(line, file=f)

    def save_mentions(self):
        with open(MENTIONS_PATH, "w") as f:
            for line in self.serialize_mentions():
                print(line, file=f)

    def read_users(self):
        if not os.path.isfile(USERS_PATH):
            return
        with open(USERS_PATH) as f:
            for line in f:
                if not line.startswith("#"):
                    user = MailUser.from_string(line.rstrip())
                    self.mail_users[user.nickname] = user

    def read_mentions(self):
        if not os.path.isfile(MENTIONS_PATH):
            return
        with open(MENTIONS_PATH) as f:
            for line in f:
                mention = Mention.from_string(line, self.mail_users)
                mention.target.mentions.append(mention)

    async def command_loop(self):
        while True:
            try:
                command = await astdio.input()
            except EOFError:
                break
            text = "Commands: users, mentions"
            if command == "users":
                text = "\n".join((
                    "<nickname> <enabled>",
                    *self.serialize_users(),
                ))
            elif command == "mentions":
                text = "\n".join((
                    "<date> <offset> <private> <sender> <target> <message>",
                    *self.serialize_mentions(),
                ))
            await stderr_async(text)

    async def start_async(self, hostname, port, ssl, nickname, password):
        await self.bot.connect(hostname, port, ssl=ssl)
        await self.bot.register(nickname, password=password)
        if self.check_id:
            if not self.bot.is_tracking_known_id_statuses:
                raise RuntimeError(
                    "The IRC server must support account-notify "
                    "when using --check-id and --force-id.",
                )
        self.bot.join(self.channel)
        await self.bot.listen()

    def start(self, hostname, port, ssl, nickname, password):
        self.bot.schedule_coroutine(self.command_loop())
        self.bot.call_coroutine(
            self.start_async(hostname, port, ssl, nickname, password),
        )


def stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


async def stderr_async(*args, **kwargs):
    await astdio.print(*args, file=sys.stderr, **kwargs)


def log(*args, **kwargs):
    date_str = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(date_str, *args, **kwargs)


def main(argv):
    args = docopt(__doc__, argv=argv[1:], version=__version__)
    password = None
    if args["--password"]:
        stderr("Password: ", end="", flush=True)
        use_getpass = sys.stdin.isatty() or args["--getpass"]
        password = getpass("") if use_getpass else input()
        if not use_getpass:
            stderr("Received password.")

    nimbot = Nimbot(
        args["--check-id"], args["--force-id"], args["<channel>"],
        log_communication=args["--verbose"],
    )

    try:
        start_args = [
            args["<host>"], int(args["<port>"]), args["--ssl"],
            args["<nickname>"], password]
        nimbot.start(*start_args)
        while args["--loop"]:
            nimbot.start(*start_args)
    finally:
        nimbot.save_users()
        nimbot.save_mentions()

if __name__ == "__main__":
    main(sys.argv)
