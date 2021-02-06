nimbot
======

Version 0.4.0

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

Version 0.4.0:

* nimbot now works with (and requires) [pyrcb2] v0.6.

Version 0.3.2:

* Fixed "old message" and "new message" numbers (they were set to debug
  values).

Version 0.3.1:

* Fixed a bug that caused crashes when users with nimbot disabled mentioned
  other users.

Version 0.3.0:

* Switched to pyrcb2; now using pyrcb2's built-in account tracking.
* Added command-line option ``--verbose``.
* Improved help and error messages.

Dependencies
------------

* Python ≥ 3.7
* Python package: [pyrcb2]
* Python package: [aioconsole]
* Python package: [docopt]
* Python package: [humanize]

Run ``pip3 install -r requirements.txt`` to install the Python packages. You
can also use ``requirements.freeze.txt`` instead to install specific versions
of the dependencies that have been verified to work.

[pyrcb2]: https://pypi.org/project/pyrcb2
[aioconsole]: https://pypiorg/project/aioconsole
[docopt]: https://pypi.org/project/docopt
[humanize]: https://pypi.org/project/humanize

License
-------

nimbot is licensed under version 3 or later of the GNU Affero General Public
License. See [LICENSE](LICENSE).
