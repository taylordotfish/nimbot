# Copyright (C) 2015 nickolas360 (https://github.com/nickolas360)
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


class Mention:
    def __init__(self, message, sender, index, time):
        self.message = message
        self.sender = sender
        self.index = index
        self.time = time
