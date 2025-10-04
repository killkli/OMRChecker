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
**Status**: Not Started

### Tasks:
- [ ] Create `frontend/config/constants.py` for all constant values
- [ ] Define page dimensions, bubble sizes, margins, spacing defaults
- [ ] Define font paths and sizes
- [ ] Create `Config` class to load and access configuration
- [ ] Replace all hardcoded values in app.py with config references
- [ ] Test that application behavior is unchanged

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
**Status**: Not Started

### Tasks:
- [ ] Create `frontend/utils/marker_utils.py` for marker generation
- [ ] Create `frontend/utils/text_utils.py` for text rendering
- [ ] Create `frontend/utils/coordinate_utils.py` for coordinate calculations
- [ ] Extract duplicate marker generation logic into single function
- [ ] Extract duplicate custom text handling into utilities
- [ ] Replace all duplicated code with utility function calls
- [ ] Write unit tests for all utility functions

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
**Status**: Not Started

### Tasks:
- [ ] Create `frontend/core/` directory
- [ ] Move `OMRProcessorGradio` to `frontend/core/processor.py`
- [ ] Move `TemplateBuilder` to `frontend/core/template_builder.py`
- [ ] Move `OMRSheetGenerator` to `frontend/core/sheet_generator.py`
- [ ] Refactor each class to use config and utilities
- [ ] Update imports in app.py
- [ ] Write unit tests for each core class

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
**Status**: Not Started

### Tasks:
- [ ] Break `generate_sheet` into logical sub-functions:
  - `_setup_page_dimensions()`
  - `_draw_markers()`
  - `_render_custom_texts()`
  - `_generate_question_blocks()`
  - `_add_qr_code()`
  - `_save_outputs()`
- [ ] Break `create_gradio_interface` into tab-specific functions:
  - `_create_processing_tab()`
  - `_create_template_builder_tab()`
  - `_create_sheet_generator_tab()`
  - `_create_batch_generation_tab()`
- [ ] Ensure each function has clear input/output
- [ ] Write unit tests for all new functions

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
**Status**: Not Started

### Tasks:
- [ ] Create `frontend/ui/` directory
- [ ] Create `frontend/ui/tabs/` for individual tab modules
- [ ] Move Gradio interface code to `frontend/ui/interface.py`
- [ ] Create controller classes to mediate between UI and business logic
- [ ] Extract all Gradio event handlers to UI layer
- [ ] Ensure core business logic has no UI dependencies
- [ ] Update app.py to only initialize and launch interface

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
