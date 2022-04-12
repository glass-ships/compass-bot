#### Configuring Compass

Once you invite Compass to your server, setup is pretty simple - you just need to run a few quick commands:  

0. (Optional) Set the bot's prefix for your server (default `;`), ex:  
```;set_prefix $```

1. Set the roles you'd like to access mod-only commands, ex:  
```;setmodroles @modrole1 987654321123456789```

2. Set a channel for Compass logs, ex:  
```;setlogschannel #logs```

3. Sync the bot's command tree to your server:  
```;sync guild```

???+ tldr "Admin Commands - Setting up the bot"
    | Command | Arguments | Description |
    |---------|-----------|-------------|
    | `setprefix` | New prefix | Sets the bot prefix for your guild (default: `;`) |
    | `setmodroles` | Role ID's or mentions | Sets the mod roles for your guild |
    | `setlogschannel` | Channel ID or link | Sets the logs channel for your guild |
    | `sync` | "guild" (required) | Syncs the bot's slash commands to your guild |