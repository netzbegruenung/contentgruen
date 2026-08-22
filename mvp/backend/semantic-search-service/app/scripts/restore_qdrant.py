#!/usr/bin/env python3
"""
Gut gesagt Qdrant Restore Script
Restores a Qdrant collection from a snapshot file
"""

import sys
import os
import argparse
import time
from pathlib import Path
from datetime import datetime

# Add app directory to path for imports
sys.path.insert(0, "/app")

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from core.config import Settings

# Use simple logging for standalone script (not application logging)
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class QdrantRestore:
    """Handles restore of Qdrant collection from snapshot file."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.qdrant_url = settings.qdrant_url or "http://localhost:6333"
        self.collection_name = settings.qdrant_collection or "content_collection"
        self.client = QdrantClient(url=self.qdrant_url, timeout=60)

    def upload_and_recover_snapshot(self, snapshot_path: str):
        """
        Upload snapshot file to Qdrant and automatically recover collection.

        Uses Qdrant's built-in upload+recover functionality via priority parameter.
        If collection doesn't exist, it will be created automatically.

        Args:
            snapshot_path: Local path to the snapshot file
        """
        logger.info(f"Uploading and recovering from snapshot: {snapshot_path}")

        if not os.path.exists(snapshot_path):
            raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")

        file_size = os.path.getsize(snapshot_path)
        logger.info(f"Snapshot file size: {file_size:,} bytes")

        try:
            # Upload using REST API with priority=snapshot parameter
            # This tells Qdrant to automatically recover the collection from the snapshot
            # and create the collection if it doesn't exist
            import requests

            upload_url = (
                f"{self.qdrant_url}/collections/{self.collection_name}/snapshots/upload"
                f"?priority=snapshot"
            )

            logger.info("Uploading snapshot with auto-recovery (priority=snapshot)...")
            with open(snapshot_path, "rb") as f:
                files = {"snapshot": f}
                response = requests.post(upload_url, files=files, timeout=300)
                response.raise_for_status()

            result = response.json()
            logger.info(f"Upload and recovery response: {result}")

            if result.get("status") == "ok" or result.get("result") is True:
                logger.info("Snapshot uploaded and collection recovered successfully")
            else:
                logger.warning(f"Unexpected response format: {result}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload and recover snapshot: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during upload and recovery: {e}")
            raise

    def verify_restore(self):
        """Verify that the collection was restored successfully."""
        try:
            logger.info("Verifying restore...")

            # Get collection info
            collection_info = self.client.get_collection(
                collection_name=self.collection_name
            )

            logger.info(f"Collection: {self.collection_name}")
            logger.info(f"Status: {collection_info.status}")
            logger.info(f"Points count: {collection_info.points_count}")
            logger.info(f"Vectors count: {collection_info.vectors_count}")

            if collection_info.points_count == 0:
                logger.warning("Collection is empty after restore!")
                return False

            return True

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

    def run(self, snapshot_path: str):
        """
        Run the complete restore process.

        Uses Qdrant's priority=snapshot parameter to automatically handle collection
        creation/recovery. The snapshot data will take priority over any existing data.

        Args:
            snapshot_path: Path to the snapshot file to restore
        """
        try:
            logger.info("=" * 50)
            logger.info("Starting Qdrant collection restore...")
            logger.info(f"Collection: {self.collection_name}")
            logger.info(f"Qdrant URL: {self.qdrant_url}")
            logger.info(f"Snapshot file: {snapshot_path}")

            # Upload with priority=snapshot parameter
            # This automatically handles collection creation/recovery
            # If collection exists, snapshot data takes priority
            # If collection doesn't exist, it will be created from snapshot
            self.upload_and_recover_snapshot(snapshot_path)

            # Wait for recovery to complete
            logger.info("Waiting for recovery to stabilize...")
            time.sleep(5)

            # Verify restore
            logger.info("Verifying restore...")
            if self.verify_restore():
                logger.info("=" * 50)
                logger.info("Qdrant restore completed successfully!")
                logger.info("=" * 50)
            else:
                logger.error("Restore verification failed!")
                sys.exit(1)

        except Exception as e:
            logger.error(f"Restore failed: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Restore Qdrant collection from snapshot"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input snapshot file path (e.g., /backups/backup_20250916/qdrant_snapshot.tar)",
    )

    args = parser.parse_args()

    # Initialize settings
    settings = Settings()

    # Run restore
    restore = QdrantRestore(settings)
    restore.run(args.input)


if __name__ == "__main__":
    main()
