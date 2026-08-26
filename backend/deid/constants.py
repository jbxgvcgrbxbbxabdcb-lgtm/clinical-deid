"""Domain constants for Clinical De-identify."""

MULTIMODAL_HINT = 'DOCX support needs: pip install "openmed[multimodal]".'
PDF_SCANNED_HINT = (
    "No selectable text layer was found in this PDF — it may be a scanned / "
    "image-only document. Only non-scanned PDFs are supported for now."
)
DEIDENTIFICATION_METHODS = (
    "mask",
    "replace",
    "hash",
    "remove",
    "shift_dates",
    "format_preserve",
)
FORCE_DENY_LABEL = "OTHER"
HIGH_CONFIDENCE_THRESHOLD = 0.9
# openmed default is 0.7; slightly lower so borderline emails / orgs surface in review.
DETECTION_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_CONFIDENCE_FILTER = 0.5
REPLACE_SEED = 7
# Demo-only HMAC material for in-memory SurrogateVault (never log).
REPLACE_VAULT_SECRET = b"openmed-clinical-deid-demo-vault-v1"
CROSS_LIST_CONFLICT_MESSAGE = (
    "Term appears in both 必脱敏 and 勿脱敏 lists; remove one before continuing."
)
SYNTHETIC_CLINICAL_TEXT = (
    "Synthetic note: John Doe (MRN 123456) was seen on 01/15/2023 by "
    "Dr. Alice Smith. Reach John Doe at john.doe@example.com or "
    "(415) 555-0142."
)
