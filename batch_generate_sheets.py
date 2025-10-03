"""
Batch OMR Sheet Generator with QR Codes from Excel ID List

This script reads a list of IDs from an Excel file and generates
individual OMR sheets with unique QR codes for each ID.
"""
import sys
from pathlib import Path
import argparse
import pandas as pd
from typing import List, Optional
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator
from src.logger import logger


class BatchOMRGenerator:
    """Generate multiple OMR sheets from an Excel ID list."""

    def __init__(self):
        self.generator = OMRSheetGenerator()

    def read_ids_from_excel(
        self, excel_path: str, column_name: Optional[str] = None, sheet_name: int = 0
    ) -> List[str]:
        """
        Read IDs from an Excel file.

        Args:
            excel_path: Path to Excel file (.xlsx, .xls, .csv)
            column_name: Name of column containing IDs (default: first column)
            sheet_name: Sheet index or name (default: 0 for first sheet)

        Returns:
            List of ID strings
        """
        try:
            # Read Excel file
            if excel_path.endswith('.csv'):
                df = pd.read_csv(excel_path)
            else:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)

            # Get the column
            if column_name:
                if column_name not in df.columns:
                    raise ValueError(
                        f"Column '{column_name}' not found. Available columns: {list(df.columns)}"
                    )
                id_column = df[column_name]
            else:
                # Use first column
                id_column = df.iloc[:, 0]

            # Convert to strings and remove NaN
            ids = [str(x).strip() for x in id_column if pd.notna(x)]

            logger.info(f"Read {len(ids)} IDs from {excel_path}")
            return ids

        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            raise

    def generate_batch(
        self,
        ids: List[str],
        output_dir: Path,
        num_questions: int = 20,
        question_type: str = "QTYPE_MCQ4",
        num_columns: int = 4,
        include_markers: bool = True,
        page_width: int = 2100,
        page_height: int = 2970,
        bubble_size: int = 40,
    ) -> tuple[int, int]:
        """
        Generate OMR sheets for a batch of IDs.

        Args:
            ids: List of ID strings
            output_dir: Directory to save generated sheets
            num_questions: Number of questions per sheet
            question_type: Type of questions (QTYPE_MCQ4, QTYPE_MCQ5, etc.)
            num_columns: Number of columns for layout
            include_markers: Whether to include alignment markers
            page_width: Page width in pixels
            page_height: Page height in pixels
            bubble_size: Bubble size in pixels

        Returns:
            Tuple of (successful_count, failed_count)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        sheets_dir = output_dir / "sheets"
        templates_dir = output_dir / "templates"
        sheets_dir.mkdir(exist_ok=True)
        templates_dir.mkdir(exist_ok=True)

        success_count = 0
        failed_count = 0

        logger.info(f"Starting batch generation for {len(ids)} IDs...")

        for idx, student_id in enumerate(ids, 1):
            try:
                logger.info(f"[{idx}/{len(ids)}] Generating sheet for ID: {student_id}")

                # Generate sheet with QR code
                sheet_temp_path, template_temp_path, msg = self.generator.generate_sheet(
                    num_questions=num_questions,
                    question_type=question_type,
                    num_columns=num_columns,
                    include_markers=include_markers,
                    page_width=page_width,
                    page_height=page_height,
                    bubble_size=bubble_size,
                    include_qr=True,
                    qr_content=student_id,
                )

                if sheet_temp_path is None or template_temp_path is None:
                    logger.error(f"Failed to generate sheet for {student_id}: {msg}")
                    failed_count += 1
                    continue

                # Copy sheet image with ID as filename
                sheet_filename = f"{student_id}.png"
                sheet_path = sheets_dir / sheet_filename
                shutil.copy2(sheet_temp_path, sheet_path)

                # Copy template with ID as filename
                template_filename = f"{student_id}_template.json"
                template_dest = templates_dir / template_filename
                shutil.copy2(template_temp_path, template_dest)

                logger.info(f"✓ Generated: {sheet_path}")
                success_count += 1

            except Exception as e:
                logger.error(f"Error generating sheet for {student_id}: {e}")
                failed_count += 1

        logger.info(f"\nBatch generation complete:")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info(f"  Output directory: {output_dir}")

        return success_count, failed_count


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch generate OMR sheets with QR codes from Excel ID list"
    )

    # Required arguments
    parser.add_argument(
        "excel_file",
        type=str,
        help="Path to Excel file (.xlsx, .xls, .csv) containing IDs",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="generated_sheets",
        help="Output directory for generated sheets (default: generated_sheets)",
    )

    # Excel reading options
    parser.add_argument(
        "-c",
        "--column",
        type=str,
        default=None,
        help="Column name containing IDs (default: first column)",
    )
    parser.add_argument(
        "-s",
        "--sheet",
        type=str,
        default="0",
        help="Excel sheet name or index (default: 0)",
    )

    # Sheet generation options
    parser.add_argument(
        "-q",
        "--questions",
        type=int,
        default=20,
        help="Number of questions (default: 20)",
    )
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        default="QTYPE_MCQ4",
        choices=["QTYPE_MCQ4", "QTYPE_MCQ5", "QTYPE_INT"],
        help="Question type (default: QTYPE_MCQ4)",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=4,
        help="Number of columns for layout (default: 4)",
    )
    parser.add_argument(
        "--no-markers",
        action="store_true",
        help="Disable alignment markers",
    )
    parser.add_argument(
        "--page-width",
        type=int,
        default=2100,
        help="Page width in pixels (default: 2100)",
    )
    parser.add_argument(
        "--page-height",
        type=int,
        default=2970,
        help="Page height in pixels (default: 2970)",
    )
    parser.add_argument(
        "--bubble-size",
        type=int,
        default=40,
        help="Bubble size in pixels (default: 40)",
    )

    args = parser.parse_args()

    # Validate Excel file exists
    excel_path = Path(args.excel_file)
    if not excel_path.exists():
        print(f"Error: Excel file not found: {excel_path}")
        sys.exit(1)

    # Parse sheet argument (can be name or index)
    try:
        sheet_name = int(args.sheet)
    except ValueError:
        sheet_name = args.sheet

    # Create generator and read IDs
    try:
        generator = BatchOMRGenerator()
        ids = generator.read_ids_from_excel(
            str(excel_path), column_name=args.column, sheet_name=sheet_name
        )

        if not ids:
            print("Error: No IDs found in Excel file")
            sys.exit(1)

        print(f"\nFound {len(ids)} IDs to process")
        print(f"Sample IDs: {ids[:5]}")
        print(f"\nGenerating sheets to: {args.output_dir}\n")

        # Generate batch
        success, failed = generator.generate_batch(
            ids=ids,
            output_dir=Path(args.output_dir),
            num_questions=args.questions,
            question_type=args.type,
            num_columns=args.columns,
            include_markers=not args.no_markers,
            page_width=args.page_width,
            page_height=args.page_height,
            bubble_size=args.bubble_size,
        )

        print(f"\n{'='*60}")
        print(f"Batch Generation Complete!")
        print(f"{'='*60}")
        print(f"  Successful: {success}")
        print(f"  Failed: {failed}")
        print(f"  Output: {args.output_dir}/")
        print(f"{'='*60}\n")

        sys.exit(0 if failed == 0 else 1)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
