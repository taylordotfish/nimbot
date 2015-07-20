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
        return "{0} {1} {2} {3} {4} {5}".format(
              self.time.strftime("%Y-%m-%d/%H:%M:%S"), self.index - offset,
              self.private, self.sender, self.target, self.message)

    @classmethod
    def from_string(cls, string):
        split = string.rstrip().split(" ", 5)
        time = datetime.strptime(split[0], "%Y-%m-%d/%H:%M:%S")
        index = int(split[1])
        private = split[2] == "True"
        sender, target, message = split[3:]
        return cls(message, sender, target, index, time, private)
