import re
from pathlib import Path
from datetime import datetime
from scipy.stats import ttest_rel

# ==== Step 1: Set file paths ====
ground_truth_file = r"Insert Path"
context_file = r"Insert Path"
context_free_file = r"Insert Path"
output_dir = Path(r"Insert Path")
output_dir.mkdir(exist_ok=True)

# ==== Step 2: Timestamp normalization ====
def normalize_timestamp(ts):
    return ts.replace("UTC", "").strip()

def timestamps_match(a, b, hour_threshold=14):
    try:
        dt1 = datetime.strptime(normalize_timestamp(a), "%Y-%m-%d %H:%M:%S")
        dt2 = datetime.strptime(normalize_timestamp(b), "%Y-%m-%d %H:%M:%S")
        return abs((dt1 - dt2).total_seconds()) <= hour_threshold * 3600
    except:
        return False

# ==== Step 3: Parse input files ====
def parse_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lid_to_entities = {}
    schema_lines = {}
    rows = re.split(r"\(LID,", content)
    for row in rows:
        row = row.strip()
        if not row:
            continue
        lid_part, rest = row.split(")", 1)
        lid = lid_part.strip()
        matches = re.findall(r"\((\d+),\s*([\w\s]+),\s*(.+?),\s*(\d+)\)", rest)
        ents = set()
        lines = []
        for rl, etype, value, conf in matches:
            etype_clean = etype.strip().lower()
            value_clean = value.strip().lower()
            ents.add((etype_clean, value_clean))
            lines.append(f"({rl}, {etype.strip()}, {value.strip()}, {conf})")
        lid_to_entities[lid] = ents
        schema_lines[lid] = lines
    return lid_to_entities, schema_lines

# ==== Step 4: Match with timestamp tolerance ====
def compare_entities(gt, ai):
    tp = 0
    fp_items = set(ai)
    fn_items = set()

    for item in gt:
        if item in fp_items:
            tp += 1
            fp_items.remove(item)
        elif item[0] == "timestamp":
            matched = False
            for ai_item in fp_items.copy():
                if ai_item[0] == "timestamp" and timestamps_match(item[1], ai_item[1]):
                    tp += 1
                    fp_items.remove(ai_item)
                    matched = True
                    break
            if not matched:
                fn_items.add(item)
        else:
            fn_items.add(item)

    fp = len(fp_items)
    fn = len(fn_items)
    return tp, fp, fn, fp_items, fn_items

# ==== Step 5: Precision/Recall/F1 ====
def calc_f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    return precision, recall, f1

# ==== Step 6: Helper for schema key ====
def get_key(schema_line):
    match = re.match(r'\(\d+,\s*([\w\s]+),\s*(.+?),\s*\d+\)', schema_line.strip())
    if match:
        return (match.group(1).strip().lower(), match.group(2).strip().lower())
    return None

# ==== Step 7: Main comparison ====
def run_analysis(gt_path, ctx_path, cf_path, out_dir):
    gt_data, gt_lines = parse_file(gt_path)
    ctx_data, ctx_lines = parse_file(ctx_path)
    cf_data, cf_lines = parse_file(cf_path)

    lids = sorted(gt_data.keys(), key=lambda x: int(x))

    ctx_fp = []
    ctx_fn = []
    cf_fp = []
    cf_fn = []
    ctx_f1s = []
    cf_f1s = []

    with open(out_dir / "row_accuracy.csv", "w", encoding="utf-8") as acc_file:
        acc_file.write("LID,F1_Context,F1_ContextFree,TP_C,FP_C,FN_C,TP_CF,FP_CF,FN_CF\n")

        for lid in lids:
            gt = gt_data.get(lid, set())
            ctx = ctx_data.get(lid, set())
            cf = cf_data.get(lid, set())

            tp_c, fp_c, fn_c, fp_items_c, fn_items_c = compare_entities(gt, ctx)
            tp_f, fp_f, fn_f, fp_items_f, fn_items_f = compare_entities(gt, cf)

            _, _, f1_c = calc_f1(tp_c, fp_c, fn_c)
            _, _, f1_f = calc_f1(tp_f, fp_f, fn_f)

            ctx_f1s.append(f1_c)
            cf_f1s.append(f1_f)

            acc_file.write(f"{lid},{f1_c:.4f},{f1_f:.4f},{tp_c},{fp_c},{fn_c},{tp_f},{fp_f},{fn_f}\n")

            if fp_c:
                ctx_fp.append(f"(LID, {lid}); " + " ".join(
                    [line for line in ctx_lines[lid] if get_key(line) in fp_items_c]))
            if fn_c:
                ctx_fn.append(f"(LID, {lid}); " + " ".join(
                    [line for line in gt_lines[lid] if get_key(line) in fn_items_c]))
            if fp_f:
                cf_fp.append(f"(LID, {lid}); " + " ".join(
                    [line for line in cf_lines[lid] if get_key(line) in fp_items_f]))
            if fn_f:
                cf_fn.append(f"(LID, {lid}); " + " ".join(
                    [line for line in gt_lines[lid] if get_key(line) in fn_items_f]))

    Path(out_dir / "Context_Aware_fp.txt").write_text("\n\n".join(ctx_fp), encoding="utf-8")
    Path(out_dir / "Context_Aware_fn.txt").write_text("\n\n".join(ctx_fn), encoding="utf-8")
    Path(out_dir / "Context_Free_fp.txt").write_text("\n\n".join(cf_fp), encoding="utf-8")
    Path(out_dir / "Context_Free_fn.txt").write_text("\n\n".join(cf_fn), encoding="utf-8")

    t_val, p_val = ttest_rel(ctx_f1s, cf_f1s)

    total_tp_c = sum([int(row.split(",")[3]) for row in open(out_dir / "row_accuracy.csv").readlines()[1:]])
    total_fp_c = sum([int(row.split(",")[4]) for row in open(out_dir / "row_accuracy.csv").readlines()[1:]])
    total_fn_c = sum([int(row.split(",")[5]) for row in open(out_dir / "row_accuracy.csv").readlines()[1:]])

    total_tp_f = sum([int(row.split(",")[6]) for row in open(out_dir / "row_accuracy.csv").readlines()[1:]])
    total_fp_f = sum([int(row.split(",")[7]) for row in open(out_dir / "row_accuracy.csv").readlines()[1:]])
    total_fn_f = sum([int(row.split(",")[8]) for row in open(out_dir / "row_accuracy.csv").readlines()[1:]])

    with open(out_dir / "summary.txt", "w", encoding="utf-8") as summary:
        summary.write("\n RQ1 FINAL SUMMARY\n")
        summary.write("--------------------------\n")
        summary.write(f"Total Rows Compared: {len(lids)}\n\n")
        summary.write(f"Average F1 With Context: {sum(ctx_f1s)/len(ctx_f1s):.4f}\n")
        summary.write(f"Average F1 Context-Free: {sum(cf_f1s)/len(cf_f1s):.4f}\n\n")
        summary.write("Total Entity-Level Counts:\n")
        summary.write(f"Context-Aware - TP: {total_tp_c}, FP: {total_fp_c}, FN: {total_fn_c}\n")
        summary.write(f"Context-Free  - TP: {total_tp_f}, FP: {total_fp_f}, FN: {total_fn_f}\n\n")
        summary.write(f"Paired t-test:\n")
        summary.write(f"t-value: {t_val:.4f}\n")
        summary.write(f"p-value: {p_val:.6f}\n")
        summary.write(f"Significant? {'YES' if p_val < 0.05 else 'NO'}\n")

    print("\n📊 EVALUATION TOTALS")
    print(f"Context-Aware: TP={total_tp_c} | FP={total_fp_c} | FN={total_fn_c}")
    print(f"Context-Free:  TP={total_tp_f} | FP={total_fp_f} | FN={total_fn_f}")

# ✅ Run
run_analysis(ground_truth_file, context_file, context_free_file, output_dir)

