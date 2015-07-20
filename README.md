# nimbot
`nimbot` is a non-intrustive IRC mailbot. It notifies users when they're
mentioned in an IRC channel, but without spamming the channel. In fact, it
doesn't talk in the channel at all. Communication with the bot is done only
through private queries, and it can be enabled or disabled on a per-user basis.

`nimbot` can be enabled or disabled for each user with the command `/msg nimbot
(enable|disable)`. It is enabled by default for all users. For more information
on how to use nimbot, `/msg nimbot help`.

`nimbot` will create two files when terminated: `prefs` and `saved_mentions`.

`prefs` contains a list of users who have ever been on the IRC channel and
whether or not `nimbot` is enabled for them. Entries are line-separated in the
format `[name (lowercase)] [enabled (True/False)]`. Entries can be manually
added to notify `nimbot` of users who won't be on the channel when it first
joins.

`saved_mentions` contains a list of messages which have not yet been delivered.
`nimbot` will read from this file when starting up, so undelivered messages
won't be lost when restarting.

See `nimbot --help` for information on how to run it.

### Dependencies
* Python 3.2 or higher
* [humanize 0.5.1 or higher](https://pypi.python.org/pypi/humanize)
