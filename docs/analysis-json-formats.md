# JSON Output Formats for Analysis Tools

This document summarizes the JSON formats currently used in the SafeContract backend for:

- Mythril
- Slither
- Solhint
- Echidna
- Foundry
- Aggregator (`aggregate()`)

It is intended as a clear reference for training an AI model that reads analysis outputs.

## 1) Canonical Tool Result Wrapper

Every tool service returns a normalized wrapper with the same outer shape:

```json
{
  "issues": [],
  "error": "optional error string",
  "info": "optional informational string"
}
```

Notes:

- `issues` is always expected to be a list.
- `error` is present when a tool is unavailable/failed/unsupported.
- `info` is currently used by Echidna when no `echidna_*` properties are found.
- Tools can return both `issues` and `error` (partial failure). Aggregator handles this.

## 2) Canonical Issue Object (tool-normalized, pre-aggregation)

Each item in `issues` from tool services follows:

```json
{
  "title": "string",
  "description": "string",
  "severity": "high|medium|low|critical|informational|optimization",
  "lineno": 123,
  "swc-id": "107",
  "tool": "mythril|slither|solhint|echidna|foundry",
  "confidence": "string"
}
```

Notes:

- `lineno` can be `null`.
- `swc-id` may be empty (`""`) for tools that do not expose SWC.
- `confidence` meaning depends on tool source.

## 3) Tool-Specific Outputs

## 3.1 Mythril (`mythril_service.py`)

Typical success:

```json
{
  "issues": [
    {
      "title": "External Call To User-Supplied Address",
      "description": "Description text...",
      "severity": "High",
      "lineno": 42,
      "swc-id": "107",
      "tool": "mythril",
      "confidence": "medium"
    }
  ]
}
```

Typical failure:

```json
{
  "issues": [],
  "error": "Mythril non installé (pip install mythril)"
}
```

## 3.2 Slither (`slither_service.py`)

Typical success:

```json
{
  "issues": [
    {
      "title": "reentrancy-eth",
      "description": "Detector description...",
      "severity": "high",
      "lineno": 55,
      "swc-id": "",
      "tool": "slither",
      "confidence": "High"
    }
  ]
}
```

Typical failure:

```json
{
  "issues": [],
  "error": "Slither non installé (pip install slither-analyzer)"
}
```

## 3.3 Solhint (`solhint_service.py`)

Typical success:

```json
{
  "issues": [
    {
      "title": "func-visibility",
      "description": "Explicitly mark visibility...",
      "severity": "low",
      "lineno": 12,
      "swc-id": "",
      "tool": "solhint",
      "confidence": "high"
    }
  ]
}
```

Unsupported file type (`.vy`):

```json
{
  "issues": [],
  "error": "Solhint ne supporte que les fichiers .sol"
}
```

## 3.4 Echidna (`echidna_service.py`)

Typical property violation:

```json
{
  "issues": [
    {
      "title": "Propriété violée : echidna_invariant_balance",
      "description": "Echidna a trouvé un contre-exemple...",
      "severity": "high",
      "lineno": null,
      "swc-id": "",
      "tool": "echidna",
      "confidence": "high"
    }
  ]
}
```

No `echidna_*` properties detected:

```json
{
  "issues": [],
  "info": "Aucune propriété echidna_ trouvée — ajoutez des fonctions echidna_* pour le fuzzing"
}
```

## 3.5 Foundry (`foundry_service.py`)

Compiler warnings:

```json
{
  "issues": [
    {
      "title": "Compiler warning: 1234",
      "description": "formattedMessage...",
      "severity": "low",
      "lineno": 345,
      "swc-id": "",
      "tool": "foundry",
      "confidence": "high"
    }
  ]
}
```

Compile errors are transformed into high-severity issues (not top-level `error`):

```json
{
  "issues": [
    {
      "title": "Erreur de compilation Foundry",
      "description": "Error: ...",
      "severity": "high",
      "lineno": null,
      "swc-id": "",
      "tool": "foundry",
      "confidence": "high"
    }
  ]
}
```

## 4) Aggregator Output (`aggregator.py`)

Input: `tool_results: Record<string, ToolResultWrapper>`

Output:

```json
{
  "score": 72,
  "issues": [
    {
      "tool": "mythril",
      "title": "Reentrancy",
      "description": "Description...",
      "severity": "critical",
      "line": 41,
      "swcId": "SWC-107",
      "confidence": "medium"
    }
  ],
  "tools_used": ["mythril", "slither", "solhint"],
  "tools_errors": {
    "echidna": "Echidna timeout (> 120s)"
  },
  "summary": {
    "critical": 1,
    "medium": 2,
    "low": 3,
    "total": 6
  }
}
```

Important aggregator rules:

- Dedup key is `(title[:60].lower(), line)`.
- If duplicates exist, highest severity is kept.
- Severity normalization:
  - Mythril severities are mapped to `critical|medium|low`.
  - Other tools are passed through as emitted by service.
- Score formula:
  - `score = clamp(100 - critical*25 - medium*10 - low*5, 0, 100)`.

## 5) `/scan` API Response Shape (`backend/app/api/scan.py`)

Top-level response returned to clients:

```json
{
  "status": "completed",
  "id": "mongo_object_id_or_null",
  "report": {
    "score": 72,
    "issues": [],
    "tools_used": [],
    "tools_errors": {},
    "summary": {
      "critical": 0,
      "medium": 0,
      "low": 0,
      "total": 0
    },
    "tools_versions": {
      "mythril": "0.24.8",
      "slither": "0.11.5"
    }
  }
}
```

## 6) MongoDB Stored Analysis Shape

When DB is available, one document is inserted with:

```json
{
  "_id": "ObjectId",
  "filename": "Contract.sol",
  "code": "source code...",
  "score": 72,
  "issues": [],
  "summary": {
    "critical": 1,
    "medium": 2,
    "low": 0,
    "total": 3
  },
  "tools_used": ["mythril", "slither"],
  "tools_errors": {
    "echidna": "..."
  },
  "raw_tool_results": {
    "mythril": { "issues": [] },
    "slither": { "issues": [] },
    "solhint": { "issues": [], "error": "..." }
  },
  "analyzed_at": "ISODate",
  "status": "completed"
}
```

## 7) Training Recommendations

- Use `report.issues` as primary normalized target for cross-tool learning.
- Keep `raw_tool_results` for tool-specific behavior modeling and failure semantics.
- Treat `tools_errors` as first-class signals (availability, timeout, parser mismatch).
- Do not assume `line`/`lineno` is always present.
- Do not assume `swcId` is present for non-Mythril tools.
