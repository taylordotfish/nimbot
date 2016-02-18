nimbot
======

Version 0.2.2

**nimbot** is a non-intrusive mailbot (hence the name) for IRC. It notifies
users when they're mentioned in an IRC channel, but without spamming the
channel. In fact, it doesn't talk in the channel at all. Communication with the
bot is done only through private queries, and it can be enabled or disabled on
a per-user basis.

To send mail with nimbot, start your message with ``<nickname>:``. You can
specify multiple nicknames, separated by commas or colons. For example:
* ``nickname: Message.``
* ``nickname1, nickname2: Message.``
* ``nickname1: nickname2: Message.``

nimbot can be enabled or disabled for each user with the command ``/msg nimbot
(enable|disable)``. It is enabled by default for all users. For more
information on how to use nimbot, ``/msg nimbot help``.

nimbot will create two files when terminated: ``saved-users`` and
``saved-mentions``.

``saved-users`` contains a list of users nimbot knows about. Entries are
line-separated in the format ``<name> <enabled (True/False)>``. nimbot only
listens for mentions of users it knows about, so you may want to add users who
won't be on the channel when nimbot joins to ``saved-users``.

``saved-mentions`` contains a list of messages which have not yet been
delivered.  nimbot will read from this file when starting up, so undelivered
messages won't be lost when restarting.

See ``nimbot --help`` for information on how to run it.

What's new
----------

Version 0.2.2:

* Updated pyrcb.

Version 0.2.0:

* Users can now use the ``enabled?`` command to check if someone has nimbot
  enabled.

Dependencies
------------

* Python 3.3 or higher
* [docopt 0.6.6 or higher](https://pypi.python.org/pypi/docopt)
* [humanize 0.5.1 or higher](https://pypi.python.org/pypi/humanize)
