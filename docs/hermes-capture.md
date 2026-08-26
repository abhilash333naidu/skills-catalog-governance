# Hermes Capture Bundle

`capture-hermes` is the V2 adapter boundary for a real Hermes-created skill. It does
not invoke Hermes or infer provenance. It accepts evidence produced by Hermes and fails
closed when the evidence is incomplete or the package is outside the V2 single-file
scope.

## Required Inputs

```bash
python3 scripts/catalog_governance.py capture-hermes \
  --skill-dir /path/to/hermes/skills/<skill-name> \
  --usage /path/to/hermes/skills/.usage.json \
  --metadata /path/to/capture/hermes-capture.json \
  --active-root /path/to/active/skills \
  --output /path/to/capture-bundle
```

`hermes-capture.json` must contain the native Hermes identity fields below. `source_task`
and `write_origin` are optional because Hermes does not persist either value in the
native `.usage.json` record, and a session can run without a kanban task. When present,
they are copied as adapter context rather than independently verified authorship facts:

```json
{
  "schema": "hermes-capture-1",
  "hermes_version": "<version>",
  "hermes_commit": "<40 hex characters>",
  "source_session": "<actual Hermes session id>",
  "captured_at_utc": "<RFC 3339 timestamp>",
  "source_task": "<actual task or workflow id, or empty when no task is bound>",
  "write_origin": "<actual Hermes write origin, when separately captured>"
}
```

The `.usage.json` record for the skill must be present and contain
`created_by: "agent"`. The legacy `agent_created: true` alternative remains accepted
for compatibility, but is not produced by the native Hermes path. This marker is
asserted Hermes provenance, not cryptographic proof of authorship.

## Output

The command creates a new bundle containing:

```text
capture-bundle/
  SKILL.md
  .usage.json
  hermes-capture.json
  proposal.json
  receipt.json
```

The proposal is generated from the captured inputs. Its skill hash, usage hash,
metadata hash, proposal hash, Hermes version, commit, session, task, and provenance
status are recorded in the receipt. The output directory must not already exist.

## Intake

Run the unchanged V2 intake command against the generated bundle:

```bash
python3 scripts/catalog_governance.py intake \
  --skill /path/to/capture-bundle/SKILL.md \
  --provenance /path/to/capture-bundle/proposal.json \
  --root /path/to/skill-governance \
  --active-root /path/to/active/skills
```

Expected status: `QUARANTINED`. Intake never writes directly to the active root.

## Scope And Limitations

- The current adapter accepts only a skill directory containing `SKILL.md`; supporting
  files under `references/`, `scripts/`, `templates/`, or `assets/` are rejected.
- The adapter requires an external capture metadata file because Hermes does not expose
  a verified native governance hook in this product. The file supplies Hermes version,
  commit, session, and capture timestamp; task and write origin are optional context.
- `ASSERTED_FROM_USAGE` means the provenance was copied from the supplied Hermes usage
  record. It does not prove that the record itself was not fabricated.
- The live validation gate is not closed until the bundle is produced from an actual
  Hermes agent-created skill rather than a test fixture.
