# Curated CDC source cards

This directory is MedLLM's small, reviewed starting corpus: diabetes basics, diabetes symptoms, and high blood pressure basics. Each card is an educational summary with a direct CDC URL, review date, and SHA-256 digest in `manifest.json`.

## Rebuild locally

From `backend`:

```powershell
python scripts/build_curated_index.py --verify-only
python scripts/build_curated_index.py --replace-curated
```

`--verify-only` is offline: it fails if a card is missing or does not match its pinned SHA-256. `--replace-curated` batches the verified cards into Chroma and removes only records tagged `corpus=curated`; it does not delete uploaded documents.

## Updating a card

Review the linked CDC page in a browser, revise the concise card deliberately, update its review date and SHA-256 in `manifest.json`, then run the offline verification and rebuild commands. Do not treat a card as a substitute for the linked source or for professional medical judgment.

Source: Centers for Disease Control and Prevention (CDC). Use of these cards does not imply CDC, HHS, or United States Government endorsement of MedLLM or its developers. The original pages remain available without charge at the links in the manifest.
