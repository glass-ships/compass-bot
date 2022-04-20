#### Configuring Compass

Once you invite Compass to your server, setup is pretty simple - you just need to run a few quick commands:  

1. (Optional) Set the bot's prefix for your server (default `;`), ex:  
```;set_prefix $```

1. Set the roles you'd like to access mod-only commands, ex:  
```/set modroles @modrole1 987654321123456789```

1. Set a channel for Compass logs, ex:  
```/set channel logs #logs```

1. (Optional) Set a videos channel. **Note:** This will move all messages containing videos to your videos channel. To allow videos in a channel, use `/set allowvideos <channel>` or `/unset channel videos`
```/set channel videos #videos-and-clips```

1. Sync the bot's command tree to your server:  
```;sync guild```

And that's it - Compass is ready to go!