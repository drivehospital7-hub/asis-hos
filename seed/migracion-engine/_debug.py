"""Debug JSONB fix."""
import re
from pathlib import Path

path = Path(__file__).parent / '14_centro_costo_comun.sql'
lines = path.read_text(encoding='utf-8-sig').split('\n')

for i, line in enumerate(lines, 1):
    if 'Suminstros' in line and "'eq'" in line:
        print(f'Line {i}: [{line.rstrip()}]')
        m = re.search(r", '([^']+)', (\d+)\)$", line.rstrip())
        print(f'  Match: {m}')
        if m:
            print(f'  val={m.group(1)!r}, orden={m.group(2)!r}')
