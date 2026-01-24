"""
Migrate Xata database to MongoDB
This script migrates all data from Xata to MongoDB, including:
- Guild configurations (prod and dev)
- LFG sessions
- Activity logs
"""

import os
import sys
import argparse
import json

from xata import XataClient
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Environment variables
XATA_URL = os.getenv("XATA_DATABASE_URL")
XATA_API_KEY = os.getenv("XATA_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")

# Validate environment variables
if not all([XATA_URL, XATA_API_KEY, MONGO_URL]):
    print("Error: Missing required environment variables.")
    print("Required: XATA_DATABASE_URL, XATA_API_KEY, MONGO_URL")
    sys.exit(1)

# Initialize Xata client
xata = XataClient(db_url=XATA_URL, api_key=XATA_API_KEY)
xata_data = xata.data()

# Initialize MongoDB client with SSL/TLS configuration
# Using ssl.CERT_NONE to bypass certificate verification issues on Windows
mongo_cluster = MongoClient(MONGO_URL, server_api=ServerApi("1"), tls=True, tlsInsecure=True)
mongo_db = mongo_cluster["compass-db"]

# MongoDB collections
mongo_col_guilds = mongo_db["guilds"]
mongo_col_dev_guilds = mongo_db["dev-guilds"]
mongo_col_lfgs = mongo_db["lfgs"]
mongo_col_activity_log = mongo_db["activity-log"]


def create_indexes():
    """Create indexes for MongoDB collections"""
    print("Creating indexes...")

    # Guild collections - index on guild_id for fast lookups
    mongo_col_guilds.create_index("guild_id", unique=True)
    mongo_col_dev_guilds.create_index("guild_id", unique=True)

    # LFG collection - index on lfg_id for fast lookups
    mongo_col_lfgs.create_index("lfg_id", unique=True)

    # Activity log - compound index
    mongo_col_activity_log.create_index([("guild_id", 1), ("user_id", 1)], unique=True)

    print("Indexes created successfully.")


def migrate_guilds(table_name, collection, is_dev=False, dry_run=False):
    """Migrate guild data from Xata to MongoDB

    Args:
        table_name: Xata table name (e.g., 'guilds' or 'test-guilds')
        collection: MongoDB collection object
        is_dev: Whether this is a dev environment migration
        dry_run: If True, only display what would be migrated without modifying the database
    """
    print(f"\n{'=' * 60}")
    print(f"Migrating {table_name} to MongoDB...")
    print(f"{'=' * 60}")

    try:
        # Query all records from Xata
        response = xata_data.query(table_name, {"page": {"size": 200}})

        records = response.get("records", [])
        print(f"Found {len(records)} records in Xata table '{table_name}'")

        if not records:
            print(f"No records to migrate from {table_name}")
            return

        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for record in records:
            try:
                # Build clean record with fields in schema order for easy visual inspection
                clean_record = {}

                # Core identification fields
                clean_record["guild_id"] = int(record.get("guild_id", 0))
                clean_record["guild_name"] = record.get("guild_name", "Unknown Guild")
                clean_record["prefix"] = record.get("prefix", ";")

                # Role fields
                mem_role = record.get("mem_role")
                clean_record["mem_role"] = int(mem_role) if mem_role is not None else None

                # Convert role IDs from strings to integers
                mod_roles = record.get("mod_roles") or []
                clean_record["mod_roles"] = [int(role_id) for role_id in mod_roles]
                
                required_roles = record.get("required_roles") or []
                clean_record["required_roles"] = [int(role_id) for role_id in required_roles]

                # Channel fields
                default_channel = record.get("default_channel")
                clean_record["default_channel"] = int(default_channel) if default_channel is not None else None

                chan_bot = record.get("chan_bot")
                clean_record["chan_bot"] = int(chan_bot) if chan_bot is not None else None

                chan_logs = record.get("chan_logs")
                clean_record["chan_logs"] = int(chan_logs) if chan_logs is not None else None

                chan_welcome = record.get("chan_welcome")
                clean_record["chan_welcome"] = int(chan_welcome) if chan_welcome is not None else None

                chan_music = record.get("chan_music")
                clean_record["chan_music"] = int(chan_music) if chan_music is not None else None

                chan_lfg = record.get("chan_lfg")
                clean_record["chan_lfg"] = int(chan_lfg) if chan_lfg is not None else None

                chan_vids = record.get("chan_vids")
                clean_record["chan_vids"] = int(chan_vids) if chan_vids is not None else None

                # Other settings
                clean_record["track_activity"] = record.get("track_activity", False)
                
                # Convert video whitelist channel IDs from strings to integers
                videos_whitelist = record.get("videos_whitelist") or []
                clean_record["videos_whitelist"] = [int(channel_id) for channel_id in videos_whitelist]

                if dry_run:
                    # Dry run mode: just display the record
                    migrated_count += 1
                    print(
                        f"\n[DRY RUN] Would migrate guild: {clean_record.get('guild_name', 'Unknown')} (ID: {clean_record['guild_id']})"
                    )
                    print(json.dumps(clean_record, indent=2, default=str, ensure_ascii=False))
                else:
                    # Insert or update in MongoDB
                    result = collection.update_one(
                        {"guild_id": clean_record["guild_id"]}, {"$set": clean_record}, upsert=True
                    )

                    if result.upserted_id:
                        migrated_count += 1
                        print(
                            f"✓ Migrated guild {clean_record.get('guild_name', 'Unknown')} (ID: {clean_record['guild_id']})"
                        )
                    else:
                        skipped_count += 1
                        print(
                            f"○ Updated guild {clean_record.get('guild_name', 'Unknown')} (ID: {clean_record['guild_id']})"
                        )

            except Exception as e:
                error_count += 1
                print(f"✗ Error migrating record: {e}")
                print(f"  Record ID: {record.get('id', 'Unknown')}")

        print(f"\n{table_name} Migration Summary:")
        if dry_run:
            print(f"  Records to migrate: {migrated_count}")
        else:
            print(f"  New records: {migrated_count}")
            print(f"  Updated records: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total processed: {len(records)}")

    except Exception as e:
        print(f"✗ Error querying Xata table '{table_name}': {e}")
        sys.exit(1)


def migrate_lfgs(table_name, dry_run=False):
    """Migrate LFG data from Xata to MongoDB

    Args:
        table_name: Xata table name (e.g., 'lfgs' or 'test-lfgs')
        dry_run: If True, only display what would be migrated without modifying the database
    """
    print(f"\n{'=' * 60}")
    print(f"Migrating {table_name} to MongoDB...")
    print(f"{'=' * 60}")

    try:
        # Query all records from Xata
        response = xata_data.query(table_name, {"page": {"size": 200}})

        records = response.get("records", [])
        print(f"Found {len(records)} LFG records in Xata table '{table_name}'")

        if not records:
            print(f"No LFG records to migrate from {table_name}")
            return

        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for record in records:
            try:
                # Get the LFG ID from Xata's id field
                lfg_id = record.get("id")

                # Clean the record
                clean_record = {
                    "lfg_id": lfg_id,
                    "leader": int(record.get("leader", 0)),
                    "joined": record.get("joined", []),
                    "standby": record.get("standby", []),
                    "num_players": int(record.get("num_players", 0)),
                }

                if dry_run:
                    # Dry run mode: just display the record
                    migrated_count += 1
                    print(
                        f"\n[DRY RUN] Would migrate LFG: {lfg_id} (Leader: {clean_record['leader']}, Players: {len(clean_record['joined'])}/{clean_record['num_players']})"
                    )
                    print(json.dumps(clean_record, indent=2, default=str, ensure_ascii=False))
                else:
                    # Insert or update in MongoDB
                    result = mongo_col_lfgs.update_one({"lfg_id": lfg_id}, {"$set": clean_record}, upsert=True)

                    if result.upserted_id:
                        migrated_count += 1
                        print(
                            f"✓ Migrated LFG {lfg_id} (Leader: {clean_record['leader']}, "
                            f"Players: {len(clean_record['joined'])}/{clean_record['num_players']})"
                        )
                    else:
                        skipped_count += 1
                        print(f"○ Updated LFG {lfg_id}")

            except Exception as e:
                error_count += 1
                print(f"✗ Error migrating LFG record: {e}")
                print(f"  Record ID: {record.get('id', 'Unknown')}")

        print(f"\n{table_name} Migration Summary:")
        if dry_run:
            print(f"  Records to migrate: {migrated_count}")
        else:
            print(f"  New records: {migrated_count}")
            print(f"  Updated records: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total processed: {len(records)}")

    except Exception as e:
        print(f"✗ Error querying Xata table '{table_name}': {e}")


def migrate_activity_log(dry_run=False):
    """Migrate activity log data from Xata to MongoDB

    Args:
        dry_run: If True, only display what would be migrated without modifying the database
    """
    print(f"\n{'=' * 60}")
    print(f"Migrating activity-log to MongoDB...")
    print(f"{'=' * 60}")

    try:
        # Query all records from Xata
        response = xata_data.query("activity-log", {"page": {"size": 200}})

        records = response.get("records", [])
        print(f"Found {len(records)} activity log records in Xata")

        if not records:
            print("No activity log records to migrate")
            return

        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for record in records:
            id = f"{record.get('guild_id', 0)}-{record.get('user_id', 0)}"
            try:
                # Clean the record
                clean_record = {
                    "guild_id": int(record.get("guild_id", 0)),
                    "guild_name": record.get("guild_name", ""),
                    "user_id": int(record.get("user_id", 0)),
                    "user_name": record.get("user_name", ""),
                    "timestamp": record.get("timestamp", ""),
                }

                if dry_run:
                    # Dry run mode: just display the record
                    migrated_count += 1
                    print(
                        f"\n[DRY RUN] Would migrate activity log: {clean_record['user_name']} in {clean_record['guild_name']}"
                    )
                    print(json.dumps(clean_record, indent=2, default=str, ensure_ascii=False))
                else:
                    # Insert or update in MongoDB
                    result = mongo_col_activity_log.update_one(
                        {"_id": id},
                        {"$set": clean_record},
                        upsert=True,
                    )

                    if result.upserted_id:
                        migrated_count += 1
                    else:
                        skipped_count += 1

            except Exception as e:
                error_count += 1
                print(f"✗ Error migrating activity log record: {e}")

        print(f"\nActivity Log Migration Summary:")
        if dry_run:
            print(f"  Records to migrate: {migrated_count}")
        else:
            print(f"  New records: {migrated_count}")
            print(f"  Updated records: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total processed: {len(records)}")

    except Exception as e:
        print(f"✗ Error querying Xata activity-log table: {e}")


def verify_migration():
    """Verify the migration by comparing record counts"""
    print(f"\n{'=' * 60}")
    print("Verifying Migration...")
    print(f"{'=' * 60}")

    # Check guilds
    xata_guilds = xata_data.query("guilds", {"page": {"size": 0}})
    mongo_guilds = mongo_col_guilds.count_documents({})
    print(f"Guilds - Xata: {xata_guilds.get('totalCount', 0)}, MongoDB: {mongo_guilds}")

    # Check dev guilds
    xata_dev = xata_data.query("test-guilds", {"page": {"size": 0}})
    mongo_dev = mongo_col_dev_guilds.count_documents({})
    print(f"Dev Guilds - Xata: {xata_dev.get('totalCount', 0)}, MongoDB: {mongo_dev}")

    # Check LFGs
    xata_lfgs = xata_data.query("lfgs", {"page": {"size": 0}})
    mongo_lfgs_count = mongo_col_lfgs.count_documents({})
    print(f"LFGs - Xata: {xata_lfgs.get('totalCount', 0)}, MongoDB: {mongo_lfgs_count}")

    print()


def main(dry_run=False):
    """Main migration function

    Args:
        dry_run: If True, only display what would be migrated without modifying the database
    """
    print(f"\n{'#' * 60}")
    if dry_run:
        print("# Xata to MongoDB Migration Script (DRY RUN MODE)")
        print("# No changes will be made to the database")
    else:
        print("# Xata to MongoDB Migration Script")
    print(f"{'#' * 60}")

    try:
        # Create indexes (skip in dry run mode)
        if not dry_run:
            create_indexes()
        else:
            print("\n[DRY RUN] Skipping index creation\n")

        # Migrate production guilds
        migrate_guilds("guilds", mongo_col_guilds, is_dev=False, dry_run=dry_run)

        # Migrate dev guilds
        migrate_guilds("test-guilds", mongo_col_dev_guilds, is_dev=True, dry_run=dry_run)

        # Migrate LFGs (production)
        migrate_lfgs("lfgs", dry_run=dry_run)

        # Migrate LFGs (dev) if they exist
        try:
            migrate_lfgs("test-lfgs", dry_run=dry_run)
        except Exception as e:
            print(f"\nNote: No 'test-lfgs' table found, skipping... ({e})")

        # Migrate activity log
        try:
            migrate_activity_log(dry_run=dry_run)
        except Exception as e:
            print(f"\nNote: No 'activity-log' table found, skipping... ({e})")

        # Verify migration (skip in dry run mode)
        if not dry_run:
            verify_migration()

        print(f"\n{'#' * 60}")
        if dry_run:
            print("# Dry run completed successfully!")
            print("# Run without --dry-run to actually migrate the data")
        else:
            print("# Migration completed successfully!")
        print(f"{'#' * 60}\n")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        # Close connections
        mongo_cluster.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate data from Xata to MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display what would be migrated without making any changes to the database",
    )
    args = parser.parse_args()

    main(dry_run=args.dry_run)
