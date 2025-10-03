# OMRChecker Gradio Frontend

A modern, user-friendly web interface for OMRChecker built with Gradio.

## Features

- 📤 **Easy File Upload**: Drag-and-drop interface for OMR images and configuration files
- 🖼️ **Multiple Image Processing**: Process single or multiple OMR sheets at once
- ⚙️ **Configurable Options**: Support for custom templates, configs, and evaluation files
- 📊 **Visual Results**: View marked images and download results as CSV
- 🚀 **No JavaScript Required**: Pure Python implementation with Gradio

## Quick Start

### 1. Installation

Make sure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### 2. Launch the Frontend

Run the launcher script from the project root:

```bash
python run_frontend.py
```

Or directly run the app:

```bash
python frontend/app.py
```

The web interface will open automatically in your browser at `http://localhost:7860`

### 3. Using the Interface

1. **Upload OMR Images**: Click "OMR Images" and select one or more PNG/JPG files
2. **Upload Template**: Click "Template File" and select your `template.json`
3. **Optional Files**:
   - Upload `config.json` for custom processing parameters
   - Upload `evaluation.json` for answer key and scoring
4. **Processing Options**:
   - Enable Auto-Alignment for slightly misaligned scans (experimental)
   - Enable Set Layout Mode to visualize template layout
5. **Click "Process OMR Sheets"** and wait for results

## Interface Layout

### Upload Section (Left)
- **OMR Images**: Multiple file upload for OMR sheets
- **Template File**: Single template.json file (required)
- **Optional Configuration Files** (expandable):
  - Config File (config.json)
  - Evaluation File (evaluation.json)
- **Processing Options** (expandable):
  - Auto-Alignment toggle
  - Set Layout Mode toggle

### Results Section (Right)
- **Status**: Processing status and summary
- **Results CSV**: Download processed results
- **Marked OMR Images**: Gallery view of marked sheets
- **Processing Log**: Detailed processing information

## File Requirements

### Required Files

1. **OMR Images** (PNG/JPG)
   - Scanned or photographed OMR sheets
   - Should match the template layout

2. **template.json**
   - Defines the bubble layout and structure
   - Must be properly formatted JSON

### Optional Files

1. **config.json**
   - Custom tuning parameters
   - Image processing settings
   - Display preferences

2. **evaluation.json**
   - Answer key definitions
   - Scoring rules
   - Question configurations

## Architecture

### Core Components

- **`app.py`**: Main Gradio application
- **`OMRProcessorGradio`**: Wrapper class for processing logic
- **Integration**: Uses existing OMRChecker processing pipeline from `src/entry.py`

### Processing Flow

1. Files uploaded through Gradio interface
2. Temporary directories created for input/output
3. Files copied to temporary input directory
4. Existing `entry_point()` function called with appropriate arguments
5. Results collected from output directory
6. CSV and marked images displayed in interface
7. Temporary directories cleaned up

## Configuration Options

### Auto-Alignment
- Experimental feature for handling slight misalignments
- Useful when scans are not perfectly aligned
- May increase processing time

### Set Layout Mode
- Visualizes template layout on images
- Useful for template development and debugging
- Does not perform actual OMR processing

## Output Files

### Results CSV
- Contains detected responses for each OMR sheet
- Includes file names, paths, scores (if evaluation enabled)
- Can be downloaded directly from interface

### Marked Images
- Visual representation of detected bubbles
- Shows which options were marked
- Useful for verification and quality control

## Troubleshooting

### Interface Won't Start
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check if port 7860 is already in use
- Try running directly: `python frontend/app.py`

### Processing Errors
- Verify template.json is valid JSON
- Ensure OMR images match template layout
- Check processing logs in "Processing Log" section
- Review error messages in status output

### No Results Displayed
- Verify that processing completed successfully
- Check that template.json matches image layout
- Review logs for error messages
- Try with sample data first

## Development

### Customization

The frontend can be customized by editing `frontend/app.py`:

- **Theme**: Change `theme=gr.themes.Soft()` to other Gradio themes
- **Port**: Modify `server_port=7860` in launch()
- **Layout**: Adjust gr.Row() and gr.Column() configurations
- **Components**: Add/modify Gradio components as needed

### Integration with Existing Code

The frontend reuses the existing OMRChecker processing pipeline:
- `src/entry.py`: Main processing logic
- `src/template.py`: Template handling
- `src/core.py`: Image processing and bubble detection
- `src/evaluation.py`: Answer evaluation

No modifications to existing code are required.

## Technical Details

### Dependencies
- **Gradio**: Web interface framework
- **OpenCV**: Image processing (from existing OMRChecker)
- **Pandas**: CSV handling (from existing OMRChecker)
- **Rich**: Console logging (from existing OMRChecker)

### Temporary Files
- Input files are copied to temporary directories
- Output is written to temporary directories
- Directories are cleaned up after processing
- Original files are never modified

### Performance
- Processes same as CLI version
- Supports batch processing of multiple images
- Results displayed in real-time
- Network overhead minimal (runs locally)

## License

Same as OMRChecker project - check main repository for details.

## Credits

- **OMRChecker**: Original project by Udayraj Deshmukh
- **Gradio Frontend**: Built with Claude Code
- **Gradio**: Web interface framework by Hugging Face
