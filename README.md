# nimbot
`nimbot` is a non-intrustive IRC mailbot. It notifies users when they're
mentioned in an IRC channel, but without spamming the channel. In fact, it
doesn't talk in the channel at all. Communication with the bot is done only
through private queries, and it can be enabled or disabled on a per-user basis.

`nimbot` can be enabled or disabled for each user with the command `/msg nimbot
(enable|disable)`. It is enabled by default for all users. For more information
on how to use nimbot, `/msg nimbot help`.

`nimbot` will create a file named `prefs` when run. This file contains a list
of users who have ever been on the IRC channel and whether or not `nimbot` is
enabled for them. Entries are line-separated in the format `[name (lowercase)]
[enabled (True/False)]`. Entries can be manually added to notify `nimbot` of
users who won't be on the channel when it first joins.

See `nimbot --help` for information on how to run it.

### Dependencies
[humanize >= v0.5.1](https://pypi.python.org/pypi/humanize)
