### Admin / Bot Configuration

The following commands are used to configure the bot for your server.  
These commands are only available to users with the administrator permission.  

???+ tldr "/set commands"
    `/set` is a group command that can be used to set a number of bot, channel, and other settings.  
    You can also `/unset` any `channel` or `role`.  
    You cannot unset the bot prefix.  
    Example usage:  
        `/set channel lfg #gaming-room`  
        `/unset role mod`  
    
    | Subcommand | Arguments | Description |
    | :--- | :--- |:--- |
    | `prefix` | `new_prefix` | Set's the bot prefix for your guild. Does not affect slash commands | 
    | `track_activity` | `true | false` | Sets whether the bot should keep track of user's most recent message |
    | `mod_roles` | `mod_roles`: Multiple role IDs or mentions | Sets the mod roles for your guild (required for moderation commands) | 
    | `member_role` | `mod_roles`: Role ID or mention (single) | Sets the member role for your guild |
    | `required_roles` | `required_roles`: Role IDs or mentions | Sets the required roles for your guild (ie. users must have at least one of these roles) |


???+ tldr "/set channel"
    `/set channel` is a subcommand of `/set` that can be used to set a number of channels for the bot.
    
    | Channel | Description |
    | :--- | :--- |
    | `lfg` | Sets a channel for the LFG listener |
    | `logs` | Sets a channel for the bot logs (required if you wish to use the `mag` react logger) |
    | `music` | Sets a channel for the music commands to work in |
    | `videos`* | Sets a channel for the videos to be moved to |
    | `welcome` | Sets a channel for the welcome messages (currently not implemented) |
    | **DEPRECATED** | --- |
    | `bot` | Specify a channel for bot commands to work in (not required, native Discord integration settings can be used to configure this) |

    **\*Note**: If you set a `videos` channel, all messages containing videos will be moved to this channel.<br>You can allow videos in a channel by using `/allowvideos`,<br>or allow videos in all channels again by using `/unset channel videos`