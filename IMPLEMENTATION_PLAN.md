# OMR Frontend Refactoring - Implementation Plan

## Overview
Refactor `frontend/app.py` (2090 lines) to improve maintainability, testability, and code organization.

## Current Issues
1. Single file with 2090 lines violates Single Responsibility Principle
2. Multiple classes with different responsibilities in one file
3. Duplicate code (marker generation, custom text handling, coordinate calculations)
4. UI and business logic tightly coupled
5. Long functions (generate_sheet: ~430 lines, create_gradio_interface: ~1027 lines)
6. Hardcoded constants throughout the code
7. Duplicate docstrings and inconsistent error handling

---

## Stage 1: Extract Constants and Configuration
**Goal**: Create a centralized configuration module for all hardcoded values
**Success Criteria**:
- All magic numbers moved to config
- No hardcoded dimensions, sizes, or margins in business logic
- Config values accessible through a single config class
**Tests**:
- Verify all original hardcoded values are now in config
- Ensure app runs with same behavior as before
**Status**: Complete

### Tasks:
- [x] Create `frontend/config/constants.py` for all constant values
- [x] Define page dimensions, bubble sizes, margins, spacing defaults
- [x] Define font paths and sizes
- [x] Create `Config` class to load and access configuration
- [x] Replace all hardcoded values in app.py with config references
- [x] Test that application behavior is unchanged

### Completion Notes:
- Created `frontend/config/constants.py` with 77+ configuration constants
- All hardcoded values extracted and organized into logical groups
- Application tested and verified to run with identical behavior
- Git commit: 23111b0 "refactor: Extract hardcoded constants to centralized config module (Stage 1)"

---

## Stage 2: Extract Shared Utilities
**Goal**: Create reusable utility functions for common operations
**Success Criteria**:
- No duplicate marker generation code
- No duplicate custom text rendering code
- No duplicate coordinate calculation code
**Tests**:
- Unit tests for marker generation
- Unit tests for text rendering utilities
- Unit tests for coordinate calculations
**Status**: Complete

### Tasks:
- [x] Create `frontend/utils/marker_utils.py` for marker generation
- [x] Create `frontend/utils/text_utils.py` for text rendering
- [x] Create `frontend/utils/coordinate_utils.py` for coordinate calculations
- [x] Extract duplicate marker generation logic into single function
- [x] Extract duplicate custom text handling into utilities
- [x] Replace all duplicated code with utility function calls
- [x] Write unit tests for all utility functions

### Completion Notes:
- Created `frontend/utils/marker_utils.py`, `text_utils.py`, `coordinate_utils.py`.
- Extracted duplicate marker generation, text rendering, and coordinate calculation logic.
- Updated `frontend/app.py` to use these new utility functions.
- Created `frontend/tests/test_utils.py` with unit tests for the new utilities.
- Git commit: 5519244 "refactor: Extract shared utilities (Stage 2)"

---

## Stage 3: Separate Business Logic Classes
**Goal**: Move each class to its own module with clear responsibility
**Success Criteria**:
- Each class in separate file under `frontend/core/`
- Clear separation of concerns
- No circular dependencies
**Tests**:
- Unit tests for OMRProcessor
- Unit tests for TemplateBuilder
- Unit tests for SheetGenerator
**Status**: Complete

### Tasks:
- [x] Create `frontend/core/` directory
- [x] Move `OMRProcessorGradio` to `frontend/core/processor.py`
- [x] Move `TemplateBuilder` to `frontend/core/template_builder.py`
- [x] Move `OMRSheetGenerator` to `frontend/core/sheet_generator.py`
- [x] Refactor each class to use config and utilities
- [x] Update imports in app.py
- [x] Write unit tests for each core class

### Completion Notes:
- Created `frontend/core/` directory with three core modules
- Moved `OMRProcessorGradio` to `frontend/core/processor.py`
- Moved `TemplateBuilder` to `frontend/core/template_builder.py`
- Moved `OMRSheetGenerator` to `frontend/core/sheet_generator.py`
- Updated `frontend/app.py` to import from core modules
- Removed class definitions from `frontend/app.py` (reduced from 1947 to 1029 lines)
- Created `frontend/tests/test_core.py` with 13 unit tests (all passing)
- All imports verified successfully
- No circular dependencies detected

---

## Stage 4: Refactor Long Functions
**Goal**: Break down long functions into smaller, testable units
**Success Criteria**:
- No function exceeds 100 lines
- Each function has single, clear purpose
- All subfunctions are testable
**Tests**:
- Unit tests for each extracted function
- Integration tests to verify combined behavior
**Status**: Complete

### Tasks:
- [x] Break `generate_sheet` into logical sub-functions:
  - `_setup_page_and_coordinate_system()`
  - `_draw_markers_on_image()`
  - `_render_custom_text_fields()`
  - `_generate_question_layout()`
  - `_add_qr_code_to_sheet()`
  - `_save_sheet_and_template()`
- [x] Break `create_gradio_interface` into tab-specific functions:
  - `_create_processing_tab()`
  - `_create_template_builder_tab()`
  - `_create_sheet_generator_tab()`
  - `_create_batch_generation_tab()`
- [x] Ensure each function has clear input/output
- [x] All existing tests still pass (no new tests needed - pure refactoring)

### Completion Notes:
- Refactored `generate_sheet` from 380 lines to 86 lines main method + 6 helper methods
- Refactored `create_gradio_interface` from ~975 lines to 36 lines main function + 4 tab functions
- All functions now under 100 lines with clear, single responsibilities
- All 23 existing tests pass without modification
- Application behavior verified to be identical
- Git commit: aa441fb "refactor: Break down long functions into smaller units (Stage 4)"

---

## Stage 5: Separate UI Layer
**Goal**: Create clean separation between UI and business logic
**Success Criteria**:
- UI code in separate module
- Business logic has no Gradio dependencies
- Controller/adapter pattern for UI-business communication
**Tests**:
- UI integration tests
- Business logic unit tests can run without Gradio
**Status**: Complete

### Tasks:
- [x] Create `frontend/ui/` directory
- [x] Create `frontend/ui/tabs/` for individual tab modules
- [x] Move Gradio interface code to `frontend/ui/interface.py`
- [x] Create controller classes to mediate between UI and business logic
- [x] Extract all Gradio event handlers to UI layer
- [x] Ensure core business logic has no UI dependencies
- [x] Update app.py to only initialize and launch interface

### Completion Notes:
- Created `frontend/ui/` directory structure with `interface.py` and `tabs/` subdirectory
- Extracted all four tab creation functions to dedicated modules:
  - `frontend/ui/tabs/processing_tab.py` - OMR sheet processing UI
  - `frontend/ui/tabs/template_tab.py` - Template builder UI
  - `frontend/ui/tabs/generator_tab.py` - Sheet generator UI
  - `frontend/ui/tabs/batch_tab.py` - Batch generation UI
- Created `frontend/ui/interface.py` with `create_gradio_interface()` function
- Simplified `frontend/app.py` from 1070 lines to 45 lines (entry point only)
- All 23 existing tests pass without modification
- Application launches successfully with identical behavior
- Clean separation achieved: UI code in `frontend/ui/`, business logic in `frontend/core/`
- No Gradio dependencies in core business logic modules

---

## Final Structure

```
frontend/
├── app.py                      # Entry point only (~50 lines)
├── config/
│   └── constants.py           # All configuration values
├── core/                      # Business logic
│   ├── processor.py          # OMR processing
│   ├── template_builder.py   # Template creation
│   └── sheet_generator.py    # Sheet generation
├── utils/                     # Shared utilities
│   ├── marker_utils.py       # Marker generation
│   ├── text_utils.py         # Text rendering
│   └── coordinate_utils.py   # Coordinate calculations
└── ui/                        # Gradio UI layer
    ├── interface.py          # Main interface
    ├── controllers/          # UI controllers
    └── tabs/                 # Individual tab modules
        ├── processing_tab.py
        ├── template_tab.py
        ├── generator_tab.py
        └── batch_tab.py
```

---

## Notes

- Each stage must pass all tests before moving to next stage
- Maintain backward compatibility throughout refactoring
- Commit after each completed stage with clean history
- No functionality changes - pure refactoring only
