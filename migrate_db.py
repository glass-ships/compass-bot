"""
Migrate Xata database to MongoDB
This script migrates all data from Xata to MongoDB, including:
- Guild configurations (prod and dev)
- LFG sessions
- Activity logs
"""

import os
import sys
import ssl

import certifi
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


def migrate_guilds(table_name, collection, is_dev=False):
    """Migrate guild data from Xata to MongoDB

    Args:
        table_name: Xata table name (e.g., 'guilds' or 'test-guilds')
        collection: MongoDB collection object
        is_dev: Whether this is a dev environment migration
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
                # Remove Xata metadata fields
                clean_record = {k: v for k, v in record.items() if not k.startswith("xata.") and k != "id"}

                # Ensure guild_id is an integer
                if "guild_id" in clean_record:
                    clean_record["guild_id"] = int(clean_record["guild_id"])

                # Convert numeric fields to integers where appropriate
                int_fields = [
                    "mem_role",
                    "chan_bot",
                    "chan_logs",
                    "chan_welcome",
                    "chan_music",
                    "chan_lfg",
                    "chan_vids",
                    "default_channel",
                ]
                for field in int_fields:
                    if field in clean_record and clean_record[field] is not None:
                        clean_record[field] = int(clean_record[field])

                # Ensure list fields are actually lists
                list_fields = ["mod_roles", "required_roles", "videos_whitelist"]
                for field in list_fields:
                    if field in clean_record and clean_record[field] is None:
                        clean_record[field] = []

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
        print(f"  New records: {migrated_count}")
        print(f"  Updated records: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total processed: {len(records)}")

    except Exception as e:
        print(f"✗ Error querying Xata table '{table_name}': {e}")
        sys.exit(1)


def migrate_lfgs(table_name):
    """Migrate LFG data from Xata to MongoDB

    Args:
        table_name: Xata table name (e.g., 'lfgs' or 'test-lfgs')
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

                # Ensure joined and standby are lists of strings
                clean_record["joined"] = [str(x) for x in clean_record["joined"]]
                clean_record["standby"] = [str(x) for x in clean_record["standby"]]

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
        print(f"  New records: {migrated_count}")
        print(f"  Updated records: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total processed: {len(records)}")

    except Exception as e:
        print(f"✗ Error querying Xata table '{table_name}': {e}")


def migrate_activity_log():
    """Migrate activity log data from Xata to MongoDB"""
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
            try:
                # Clean the record
                clean_record = {
                    "guild_id": int(record.get("guild_id", 0)),
                    "guild_name": record.get("guild_name", ""),
                    "user_id": int(record.get("user_id", 0)),
                    "user_name": record.get("user_name", ""),
                    "timestamp": record.get("timestamp", ""),
                }

                # Insert or update in MongoDB
                result = mongo_col_activity_log.update_one(
                    {"guild_id": clean_record["guild_id"], "user_id": clean_record["user_id"]},
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


def main():
    """Main migration function"""
    print(f"\n{'#' * 60}")
    print("# Xata to MongoDB Migration Script")
    print(f"{'#' * 60}")

    try:
        # Create indexes
        create_indexes()

        # Migrate production guilds
        migrate_guilds("guilds", mongo_col_guilds, is_dev=False)

        # Migrate dev guilds
        migrate_guilds("test-guilds", mongo_col_dev_guilds, is_dev=True)

        # Migrate LFGs (production)
        migrate_lfgs("lfgs")

        # Migrate LFGs (dev) if they exist
        try:
            migrate_lfgs("test-lfgs")
        except Exception as e:
            print(f"\nNote: No 'test-lfgs' table found, skipping... ({e})")

        # Migrate activity log
        try:
            migrate_activity_log()
        except Exception as e:
            print(f"\nNote: No 'activity-log' table found, skipping... ({e})")

        # Verify migration
        verify_migration()

        print(f"\n{'#' * 60}")
        print("# Migration completed successfully!")
        print(f"{'#' * 60}\n")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        # Close connections
        mongo_cluster.close()


if __name__ == "__main__":
    main()
