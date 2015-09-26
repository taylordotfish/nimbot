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

from pyrcb import IStr, IDefaultDict


class User:
    def __init__(self, nickname, enabled=True, valid=False):
        self.nickname = IStr(nickname)
        self.enabled = enabled
        self.valid = valid
        self.identified = False
        self.id_pending = False
        self.mentions = []
        self.validate_on_id = True
        self.deliver_on_id = True
        self.id_callback = None

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
        return cls(nickname, enabled, valid=True)


class Users(IDefaultDict):
    def __missing__(self, key):
        self[key] = User(key)
        return self[key]
