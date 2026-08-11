"""Fix JSONB string values in SQL migration files."""
import re
from pathlib import Path

base = Path(__file__).parent

for fname in ['14_centro_costo_comun.sql', '15_centro_costo_intramural.sql']:
    path = base / fname
    sql = path.read_text(encoding='utf-8-sig')
    lines = sql.split('\n')
    fixed = []
    
    for line in lines:
        stripped = line.strip()
        if 'VALUES' in stripped and ("'eq'" in stripped or "'cat_in'" in stripped):
            # Replace: , 'VALUE', DIGIT);
            # With:    , to_jsonb('VALUE'::text), DIGIT);
            line = re.sub(
                r", '([^']+)', (\d+)\);?$",
                lambda m: f", to_jsonb('{m.group(1)}'::text), {m.group(2)}){';' if line.rstrip().endswith(';') else ''}",
                line.rstrip()
            )
        fixed.append(line)
    
    result = '\n'.join(fixed)
    path.write_text(result, encoding='utf-8')
    print(f'Fixed: {fname}')
    
    # Verify no remaining plain strings in VALUES
    for i, line in enumerate(fixed, 1):
        s = line.strip()
        if 'VALUES' in s and ("'eq'" in s or "'cat_in'" in s):
            if re.search(r", '[^']+', \d+\)", s.rstrip()):
                print(f'  REMAINING line {i}: {s[:100]}')

print('Done')
