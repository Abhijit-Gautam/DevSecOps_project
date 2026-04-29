# Student Report Evaluation Scripts

These scripts let you run your local Hugging Face classification checkpoints
(`checkpoint-*`) against student report files.

## 1) Install dependencies

```powershell
pip install -r requirements.txt
```

## 2) Check which checkpoint will be used

```powershell
python select_best_checkpoint.py --workspace .
```

Selection logic:
- Uses the checkpoint referenced by `best_model_checkpoint` when available.
- Otherwise picks the highest `(best_metric, global_step)`.

## 3) Evaluate all reports in a folder

```powershell
python evaluate_reports.py --workspace . --reports-dir downloads --output-json downloads/predictions.json --output-csv downloads/predictions.csv
```

## 4) Evaluate one report

```powershell
python evaluate_reports.py --workspace . --report-file downloads/report_3b902648.txt
```

## 5) Optional custom label names

Create a JSON map (example in `label_map.example.json`) and pass:

```powershell
python evaluate_reports.py --workspace . --reports-dir downloads --label-map label_map.example.json
```

## Notes

- Your checkpoints do not include tokenizer files, so the evaluator falls back to
  `roberta-base` tokenizer automatically.
- Add `--local-files-only` only if tokenizer files are already cached locally.
- Supported input formats: `.txt`, `.md`, `.log`, and optional `.pdf` / `.docx`
  (if extra packages are installed from `requirements.txt`).
