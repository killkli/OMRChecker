"""View generated template"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import OMRSheetGenerator
import json

gen = OMRSheetGenerator()
sheet, tmpl, msg = gen.generate_sheet(
    num_questions=10,
    question_type='QTYPE_MCQ4',
    questions_per_row=2,
    include_roll_number=True,
    roll_digits=5,
    include_markers=True,
    page_width=1500,
    page_height=2000,
    bubble_size=40
)

print('=== Generated Template JSON ===')
with open(tmpl, 'r') as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
print(f'\n✅ Sheet image saved to: {sheet}')
print(f'✅ Template saved to: {tmpl}')
