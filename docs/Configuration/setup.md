## Configuring Compass

Compass is intended to be easy to set up and use. The bot has a few settings that can be configured to fit your server's needs.  
Most configuration can be done natively in Discord, using your server's integration settings.  
However, Compass also has a few commands that can be used to set up the bot for your server's needs.

#### Channels

Compass uses a few channels for various features.  
You can set these channels using the `/set` command (see [Admin Commands](../Commands/admin.md) for usage).

- `bot` - If a bot channel is set, Compass will only respond to commands in this channel.
- `lfg` - The LFG (Looking for Group) channel. This is where users can post and join activities.
- `logs` - Required for the 🔍 (mag) reaction message flagger
- `music` - The music channel. If a music channel is set, Compass will only respond to music commands in this channel.
- `videos` - Setting his will move all messages containing videos to your videos channel.
- `welcome` - Currently not implemented.
