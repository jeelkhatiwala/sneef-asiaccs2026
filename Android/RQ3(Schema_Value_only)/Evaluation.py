import re
from pathlib import Path
from datetime import datetime

# ✅ STEP 1: SET YOUR FILES HERE (Only change these)
ground_truth_file = r"Insert Path"
ai_file = r"Insert Path"
output_dir = r"Insert Path"

# ✅ Normalize and compare timestamps
def normalize_timestamp(ts):
    ts = ts.replace("UTC", "").strip()
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def timestamps_match(val1, val2, max_hour_diff=14):
    dt1 = normalize_timestamp(val1)
    dt2 = normalize_timestamp(val2)
    if dt1 and dt2:
        diff = abs((dt1 - dt2).total_seconds())
        return diff <= max_hour_diff * 3600
    return False

# ✅ Parse the input file
def parse_file_exact(file_path):
    lid_to_entities = {}
    lid_to_original_lines = {}
    lid_to_schema_map = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by LID blocks, robustly
    rows = re.split(r"\(LID,", content)
    for row in rows:
        row = row.strip()
        if not row:
            continue

        # Ensure consistent structure
        try:
            lid_part, rest = row.split(")", 1)
        except ValueError:
            continue  # Skip malformed row

        lid = lid_part.strip()
        rest = rest.strip()

        # Remove embedded empty lines
        rest = "\n".join([line for line in rest.splitlines() if line.strip()])

        raw_line = f"(LID,{lid}){rest}"
        lid_to_original_lines[lid] = raw_line

        entities = set()
        schema_map = {}

        matches = re.findall(r'\((\d+),\s*([\w\s]+),\s*(.+?),\s*(\d+)\)', raw_line)
        for rl, etype, value, conf in matches:
            etype_clean = etype.strip().lower()
            value_clean = value.strip().lower()
            key = (etype_clean, value_clean)
            entities.add(key)
            schema_map[key] = f"({rl}, {etype.strip()}, {value.strip()}, {conf});"

        lid_to_entities[lid] = entities
        lid_to_schema_map[lid] = schema_map

    return lid_to_entities, lid_to_original_lines, lid_to_schema_map


# ✅ Match entities considering timestamp tolerance
def match_entities(gt_set, ai_set):
    tp = set()
    fp = set(ai_set)
    fn = set(gt_set)

    for a in ai_set:
        matched = False
        for g in gt_set:
            if a == g:
                tp.add(a)
                matched = True
                break
            if a[0] == "timestamp" and g[0] == "timestamp":
                if timestamps_match(a[1], g[1]):
                    tp.add(a)
                    matched = True
                    break
        if matched:
            fp.discard(a)
            fn.discard(a)
    return tp, fp, fn

# ✅ Write results to a text file
def write_output_file(output_path, lid_to_lines):
    with open(output_path, 'w', encoding='utf-8') as f:
        for lid in sorted(lid_to_lines, key=lambda x: int(x)):
            f.write(f"(LID, {lid}); " + " ".join(lid_to_lines[lid]) + "\n\n")

# ✅ Main comparison function
def evaluate_exact_matching(gt_path, ai_path, out_dir):
    gt_entities, gt_raw, gt_schema_map = parse_file_exact(gt_path)
    ai_entities, ai_raw, ai_schema_map = parse_file_exact(ai_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)

    tp_path = out_dir / "true_positives.txt"
    fp_path = out_dir / "false_positives.txt"
    fn_path = out_dir / "false_negatives.txt"
    summary_path = out_dir / "summary.txt"

    tp_rows, fp_rows, fn_rows = {}, {}, {}
    tp_count = fp_count = fn_count = 0

    all_lids = sorted(set(gt_entities.keys()) | set(ai_entities.keys()), key=lambda x: int(x))

    for lid in all_lids:
        gt_set = gt_entities.get(lid, set())
        ai_set = ai_entities.get(lid, set())

        tp, fp, fn = match_entities(gt_set, ai_set)

        if tp:
            tp_rows[lid] = [ai_schema_map.get(lid, {}).get(ent) for ent in tp if ai_schema_map.get(lid, {}).get(ent)]
            tp_count += len(tp)
        if fp:
            fp_rows[lid] = [ai_schema_map.get(lid, {}).get(ent) for ent in fp if ai_schema_map.get(lid, {}).get(ent)]
            fp_count += len(fp)
        if fn:
            fn_rows[lid] = [gt_schema_map.get(lid, {}).get(ent) for ent in fn if gt_schema_map.get(lid, {}).get(ent)]
            fn_count += len(fn)

    write_output_file(tp_path, tp_rows)
    write_output_file(fp_path, fp_rows)
    write_output_file(fn_path, fn_rows)

    total_gt_rows = len(gt_entities)
    total_ai_rows = len(ai_entities)
    total_gt_schemas = sum(len(v) for v in gt_entities.values())
    total_ai_schemas = sum(len(v) for v in ai_entities.values())

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"📊 RQ1 EVALUATION SUMMARY\n")
        f.write(f"---------------------------\n")
        f.write(f"Total Rows in Ground Truth: {total_gt_rows}\n")
        f.write(f"Total Schemas in Ground Truth: {total_gt_schemas}\n")
        f.write(f"Total Rows in AI File: {total_ai_rows}\n")
        f.write(f"Total Schemas in AI File: {total_ai_schemas}\n\n")
        f.write(f"✅ True Positives (TP): {tp_count}\n")
        f.write(f"❌ False Positives (FP): {fp_count}\n")
        f.write(f"❌ False Negatives (FN): {fn_count}\n")

    print("\n📊 Evaluation complete")
    print(f" - GT Rows: {total_gt_rows}, AI Rows: {total_ai_rows}")
    print(f" - GT Schemas: {total_gt_schemas}, AI Schemas: {total_ai_schemas}")
    print(f" - ✅ TP: {tp_count} | ❌ FP: {fp_count} | ❌ FN: {fn_count}")
    print(f"Results saved to: {out_dir}")

# ✅ Run it
evaluate_exact_matching(ground_truth_file, ai_file, output_dir)
