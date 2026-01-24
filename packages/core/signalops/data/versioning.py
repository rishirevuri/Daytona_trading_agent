"""
Data versioning utilities for tracking dataset versions and checksums.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from signalops.data.loader import DataLoader


class DataVersioning:
    """Track and manage dataset versions for reproducibility."""

    def __init__(self, data_dir: Union[str, Path] = "./data"):
        self.data_dir = Path(data_dir)
        self.manifest_path = self.data_dir / "manifest.json"
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        """Load the version manifest from disk."""
        if self.manifest_path.exists():
            with open(self.manifest_path, "r") as f:
                return json.load(f)
        return {"datasets": {}}

    def _save_manifest(self) -> None:
        """Save the version manifest to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def register_dataset(
        self,
        name: str,
        filepath: Union[str, Path],
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Register a new dataset version.

        Args:
            name: Dataset name (e.g., 'sp500_daily')
            filepath: Path to the data file
            description: Optional description
            metadata: Additional metadata to store

        Returns:
            Version info dictionary
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        # Compute checksum
        checksum = DataLoader.compute_checksum(filepath)

        # Get file stats
        stats = filepath.stat()

        # Load data to get row count and date range
        loader = DataLoader(self.data_dir)
        if filepath.suffix == ".parquet":
            df = loader.load_parquet(filepath)
        elif filepath.suffix == ".csv":
            df = loader.load_csv(filepath)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")

        validation = loader.validate_data(df)

        # Create version entry
        version = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        version_info = {
            "version": version,
            "checksum": checksum,
            "filepath": str(filepath),
            "size_bytes": stats.st_size,
            "row_count": validation["row_count"],
            "date_range": validation["date_range"],
            "description": description,
            "metadata": metadata or {},
            "registered_at": datetime.now().isoformat(),
        }

        # Store in manifest
        if name not in self.manifest["datasets"]:
            self.manifest["datasets"][name] = {"versions": []}
        self.manifest["datasets"][name]["versions"].append(version_info)
        self.manifest["datasets"][name]["latest"] = version

        self._save_manifest()

        return version_info

    def get_dataset_info(self, name: str, version: Optional[str] = None) -> Optional[dict]:
        """Get information about a dataset version.

        Args:
            name: Dataset name
            version: Specific version or None for latest

        Returns:
            Version info or None if not found
        """
        if name not in self.manifest["datasets"]:
            return None

        dataset = self.manifest["datasets"][name]
        versions = dataset["versions"]

        if version is None:
            version = dataset.get("latest")

        for v in versions:
            if v["version"] == version:
                return v

        return None

    def verify_checksum(self, name: str, version: Optional[str] = None) -> bool:
        """Verify that a dataset's checksum matches the registered value.

        Args:
            name: Dataset name
            version: Specific version or None for latest

        Returns:
            True if checksum matches, False otherwise
        """
        info = self.get_dataset_info(name, version)
        if info is None:
            return False

        filepath = Path(info["filepath"])
        if not filepath.exists():
            return False

        current_checksum = DataLoader.compute_checksum(filepath)
        return current_checksum == info["checksum"]

    def list_datasets(self) -> list[dict]:
        """List all registered datasets.

        Returns:
            List of dataset summaries
        """
        summaries = []
        for name, dataset in self.manifest["datasets"].items():
            latest = self.get_dataset_info(name)
            summaries.append(
                {
                    "name": name,
                    "latest_version": dataset.get("latest"),
                    "num_versions": len(dataset["versions"]),
                    "row_count": latest["row_count"] if latest else None,
                    "date_range": latest["date_range"] if latest else None,
                }
            )
        return summaries

    def export_fingerprint(self, datasets: list[str]) -> dict:
        """Export a reproducibility fingerprint for multiple datasets.

        Args:
            datasets: List of dataset names

        Returns:
            Fingerprint dictionary with checksums and versions
        """
        fingerprint = {
            "generated_at": datetime.now().isoformat(),
            "datasets": {},
        }

        for name in datasets:
            info = self.get_dataset_info(name)
            if info:
                fingerprint["datasets"][name] = {
                    "version": info["version"],
                    "checksum": info["checksum"],
                    "date_range": info["date_range"],
                }

        return fingerprint
