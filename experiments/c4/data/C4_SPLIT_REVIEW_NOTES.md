# C4 Dataset Split Review Notes

## Purpose
Compare the current C4 dataset splits with the backup created before device-based splitting.

## Files reviewed
- experiments/c4/data/C4_train.csv
- experiments/c4/data/C4_val.csv
- experiments/c4/data/C4_test.csv
- Backup folder: backup_before_device_split_20261013_054519

## Findings

### Current splits
- Training: 5,584 rows
- Validation: 3,252 rows
- Testing: 1,164 rows
- Total: 10,000 rows
- All three files have 62 columns.
- No shared device_id values were found between any pair of splits.
- The scenario column has 10 shared values between each pair of splits.

### Backup splits
- Training: 6,987 rows
- Validation: 1,520 rows
- Testing: 1,493 rows
- Total: 10,000 rows
- All three files have 62 columns.
- Device IDs overlap between the splits.
- The scenario column has 10 shared values between each pair of splits.

## Review conclusions
- Prefer the current splits for evaluating generalization to unseen devices, provided device_id is the correct grouping field.
- Scenario overlap is acceptable only if unseen-scenario generalization is not the evaluation objective.
- Preserve the backup CSVs until the current splits have been fully validated.
- Do not replace the current splits with the backup based on file sizes or class counts alone.
- Verify that split generation is deterministic and that the saved CSVs match the split-generation code.
- Verify the intended meaning of label_untrusted_binary, particularly how Suspicious samples are encoded.
- Check that model training uses only training data for fitting and that validation/test data are not used for model selection or fitting.

## Label distributions

Current training:
- Trusted: 4,275
- Untrusted: 945
- Suspicious: 364

Current validation:
- Trusted: 2,595
- Untrusted: 436
- Suspicious: 221

Current testing:
- Trusted: 887
- Untrusted: 207
- Suspicious: 70

## Status
Review performed using row counts, column names, label distributions, and unique device/scenario overlap.
Further validation of split-generation logic and label semantics is required.
