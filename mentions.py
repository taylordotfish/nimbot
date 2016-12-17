# Copyright (C) 2015-2016 taylor.fish <contact@taylor.fish>
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

from pyrcb2 import IStr, IDict
from datetime import datetime


class Mention:
    def __init__(self, message, sender, target, index, time, private=False):
        self.message = message
        self.sender = sender
        self.target = target
        self.index = index
        self.time = time
        self.private = private

    def to_string(self, offset=0):
        return " ".join(map(str, [
              self.time.strftime("%Y-%m-%d/%H:%M:%S"), self.index - offset,
              self.private, self.sender, self.target, self.message]))

    @classmethod
    def from_string(cls, string, users):
        split = string.rstrip().split(" ", 5)
        time = datetime.strptime(split[0], "%Y-%m-%d/%H:%M:%S")
        index = int(split[1])
        private = split[2] == "True"
        sender, target = map(users.__getitem__, split[3:5])
        message = split[5]
        return cls(message, sender, target, index, time, private)


class MailUser:
    def __init__(self, nickname, enabled=True):
        self.nickname = IStr(nickname)
        self.enabled = enabled
        self.mentions = []
        self.identified_below = 0
        self._save = False

    @property
    def save(self):
        return self._save or bool(self.mentions)

    @save.setter
    def save(self, value):
        self._save = value

    def public_mentions(self):
        return (m for m in self.mentions if not m.private)

    def private_mentions(self):
        return (m for m in self.mentions if m.private)

    def clear_mentions(self):
        self.mentions = []

    def to_string(self):
        return " ".join(map(str, [self.nickname, self.enabled]))

    def __str__(self):
        return self.nickname

    @classmethod
    def from_string(cls, string):
        split = string.split()
        nickname = IStr(split[0])
        enabled = (len(split) < 2 or split[1].lower() == "true")
        user = cls(nickname, enabled)
        user.save = True
        return user


class MailUserDict(IDict):
    def __missing__(self, key):
        self[key] = MailUser(key)
        return self[key]
