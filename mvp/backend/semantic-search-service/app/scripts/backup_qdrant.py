#!/usr/bin/env python3
"""
ContentGrün Qdrant Backup Script
Creates a snapshot of the Qdrant collection and saves it to backup directory
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


class QdrantBackup:
    """Handles backup of Qdrant collection to snapshot file."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.qdrant_url = settings.qdrant_url or "http://localhost:6333"
        self.collection_name = settings.qdrant_collection or "content_collection"
        self.client = QdrantClient(url=self.qdrant_url, timeout=60)

    def create_snapshot(self) -> str:
        """
        Create a snapshot of the collection.

        Returns:
            str: Name of the created snapshot
        """
        logger.info(f"Creating snapshot for collection: {self.collection_name}")

        try:
            # Create snapshot (returns snapshot info)
            result = self.client.create_snapshot(collection_name=self.collection_name)

            snapshot_name = result.name
            logger.info(f"Snapshot created: {snapshot_name}")
            return snapshot_name

        except UnexpectedResponse as e:
            logger.error(f"Failed to create snapshot: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating snapshot: {e}")
            raise

    def download_snapshot(self, snapshot_name: str, output_path: str):
        """
        Download snapshot file from Qdrant.

        Args:
            snapshot_name: Name of the snapshot to download
            output_path: Local path to save the snapshot
        """
        logger.info(f"Downloading snapshot {snapshot_name} to {output_path}")

        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Download snapshot
            # Note: The Python client doesn't have direct download method,
            # so we use the REST API directly via requests
            import requests

            snapshot_url = f"{self.qdrant_url}/collections/{self.collection_name}/snapshots/{snapshot_name}"
            response = requests.get(snapshot_url, stream=True, timeout=300)
            response.raise_for_status()

            # Write to file
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verify file was written
            file_size = os.path.getsize(output_path)
            logger.info(f"Snapshot downloaded successfully ({file_size:,} bytes)")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download snapshot: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading snapshot: {e}")
            raise

    def list_snapshots(self):
        """List all available snapshots for the collection."""
        try:
            snapshots = self.client.list_snapshots(collection_name=self.collection_name)
            logger.info(f"Available snapshots for {self.collection_name}:")
            for snapshot in snapshots:
                logger.info(
                    f"  - {snapshot.name} ({snapshot.size} bytes, created: {snapshot.creation_time})"
                )
            return snapshots
        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            raise

    def delete_snapshot(self, snapshot_name: str):
        """Delete a snapshot from Qdrant."""
        try:
            self.client.delete_snapshot(
                collection_name=self.collection_name, snapshot_name=snapshot_name
            )
            logger.info(f"Deleted snapshot: {snapshot_name}")
        except Exception as e:
            logger.error(f"Failed to delete snapshot: {e}")
            raise

    def run(self, output_path: str, cleanup: bool = True):
        """
        Run the complete backup process.

        Args:
            output_path: Path where snapshot file should be saved
            cleanup: Whether to delete the snapshot from Qdrant after download
        """
        try:
            logger.info("=" * 50)
            logger.info("Starting Qdrant collection backup...")
            logger.info(f"Collection: {self.collection_name}")
            logger.info(f"Qdrant URL: {self.qdrant_url}")

            # Create snapshot
            snapshot_name = self.create_snapshot()

            # Wait a moment for snapshot to be ready
            time.sleep(1)

            # Download snapshot
            self.download_snapshot(snapshot_name, output_path)

            # Optionally clean up snapshot from Qdrant
            if cleanup:
                logger.info("Cleaning up snapshot from Qdrant...")
                self.delete_snapshot(snapshot_name)

            logger.info("=" * 50)
            logger.info("Qdrant backup completed successfully!")
            logger.info(f"Snapshot saved to: {output_path}")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backup Qdrant collection to snapshot")
    parser.add_argument(
        "--output",
        required=True,
        help="Output snapshot file path (e.g., /backups/backup_20250916/qdrant_snapshot.tar)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep snapshot in Qdrant after download (default: delete after download)",
    )

    args = parser.parse_args()

    # Initialize settings
    settings = Settings()

    # Run backup
    backup = QdrantBackup(settings)
    backup.run(args.output, cleanup=not args.no_cleanup)


if __name__ == "__main__":
    main()
