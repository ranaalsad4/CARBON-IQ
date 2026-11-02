"""CARBON IQ missing-data intelligence (Phase A4).

Rule-based and statistical (no machine learning). Original data are never overwritten: every cleaning step, estimate
and approval is recorded in a ledger with its method, parameters, uncertainty and source.

    quality   - schema, unit conversion and data-quality checks (missing, duplicates, units, invalid, outliers, zeros)
    estimate  - estimation methods, refusal rules, leave-one-out uncertainty, approvals and annual totals
    integrate - feeds annual totals and their uncertainty into the existing CARBON IQ engines; value of information
    synth     - synthetic facility data with known true values (demonstration and validation only)
    validate  - masking experiments: error, interval coverage and failure cases
"""
