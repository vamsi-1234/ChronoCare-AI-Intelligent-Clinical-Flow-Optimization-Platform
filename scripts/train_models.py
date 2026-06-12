"""End-to-end model training script for ChronoCare AI.

Usage:
    python scripts/train_models.py [--data PATH] [--models-dir DIR]
"""
import sys
import os
import logging
import argparse
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ChronoCare AI models")
    parser.add_argument(
        "--data",
        default="data/synthetic_clinic_data.csv",
        help="Path to the synthetic CSV dataset",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate synthetic data before training if CSV not found",
    )
    parser.add_argument("--models-dir", default="models")
    parser.add_argument("--n-records", type=int, default=2000)
    args = parser.parse_args()

    data_path = Path(args.data)

    # Optionally generate data
    if not data_path.exists():
        if args.generate or not data_path.exists():
            logger.info("Data file not found – generating %d synthetic records …", args.n_records)
            from scripts.generate_data import generate_data
            generate_data(n=args.n_records, out=str(data_path))
        else:
            logger.error("Data file not found: %s", data_path)
            sys.exit(1)

    from app.ml.train import train_models
    metrics = train_models(data_path=str(data_path), models_dir=args.models_dir)

    print("\n╔══════════════════════════════════╗")
    print("║   ChronoCare AI – Training Done  ║")
    print("╚══════════════════════════════════╝")
    print(f"\nDURATION MODEL")
    for k, v in metrics["duration"].items():
        print(f"  {k:6s}: {v}")
    print(f"\nNO-SHOW MODEL")
    for k, v in metrics["noshow"].items():
        print(f"  {k:10s}: {v}")
    print()


if __name__ == "__main__":
    main()
