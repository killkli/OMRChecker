# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- Install dependencies: `pip install -r requirements.txt`
- Install dev dependencies: `pip install -r requirements.dev.txt`
- Install pre-commit hooks: `pre-commit install`
- Format and lint: `pre-commit run --all-files` (runs black, isort, flake8, check-yaml, etc.)
- Run all tests: `pytest src/tests/`
- Run single test: `pytest src/tests/test_all_samples.py` (or replace with specific test file)
- Run the application: `python main.py -i inputs/ --outputDir outputs/`

## High-Level Architecture

OMRChecker is a Python CLI tool for evaluating Optical Mark Recognition (OMR) sheets using computer vision with OpenCV. It processes scanned or photographed OMR images to detect marked bubbles against a predefined template.

Key components:
- **CLI Entry**: `main.py` parses arguments and invokes `entry_point` in `src/entry.py`.
- **Processing Pipeline**: `src/entry.py` traverses input directories, loads `template.json` (bubble layouts via `src/template.py` and `src/schemas/template_schema.py`), applies image preprocessors from `src/processors/` (e.g., CropPage, CropOnMarkers implementing ImagePreprocessor), and detects responses in `src/core.py` using adaptive thresholding on bubble intensities.
- **Detection Logic**: `src/core.py` (ImageInstanceOps) handles resizing, alignment (if enabled), CLAHE enhancement, morphology, and bubble marking based on local/global thresholds computed from mean intensities. Supports multi-mark detection and error cases (e.g., no markers).
- **Evaluation**: `src/evaluation.py` scores responses against `evaluation.json` (using `src/schemas/evaluation_schema.py`).
- **Configs**: Tuning via `config.json` (`src/schemas/config_schema.py`), defaults in `src/defaults/config.py`.
- **Utilities**: `src/utils/` for image ops (OpenCV wrappers), file handling, parsing, and interaction (Rich console, Matplotlib visuals).
- **Outputs**: CSV results (Pandas), marked images, debug stacks, and error logs.

The codebase uses Pydantic for schema validation, NumPy for arrays, and follows src/ layout. Tests use pytest in `src/tests/`. Pre-commit enforces PEP8 via black/isort/flake8.

When modifying, prioritize schema-driven configs, pluggable preprocessors, and threshold adaptability for robustness across scan qualities.