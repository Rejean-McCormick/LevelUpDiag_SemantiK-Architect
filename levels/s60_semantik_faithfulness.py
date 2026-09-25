from __future__ import annotations

from pathlib import Path

from levelupdiag_core.semantik import json_from_stdout, run_target_python


def run(cfg, report):
    root = Path(cfg["_target_root"])
    required = [
        "src/semantik_architect/application/validation/coverage.py",
        "src/semantik_architect/application/planning/communication_planner.py",
        "src/semantik_architect/application/planning/language_planner.py",
        "src/semantik_architect/domain/semantics/obligations.py",
        "src/semantik_architect/domain/language/realization_unit.py",
    ]
    missing = [rel for rel in required if not (root / rel).is_file()]
    report.add(
        "semantik.faithfulness.components_present",
        "FAIL" if missing else "PASS",
        "faithfulness",
        "Faithfulness, obligation coverage and both planning stages are implemented."
        if not missing
        else "One or more faithfulness/planning components are missing.",
        evidence=missing or required,
    )

    script = r'''
import json
from semantik_architect.domain.communication.request import CommunicationRequest
from semantik_architect.application.planning.communication_planner import CommunicationPlanner
from semantik_architect.application.planning.language_planner import GenericLanguagePlanner
from semantik_architect.application.validation.coverage import CoverageValidator
from semantik_architect.domain.language.lexical import LexicalPlanningContext
from semantik_architect.domain.errors import SemantikArchitectError
req=CommunicationRequest.from_dict({
 "schema_version":"1.0",
 "semantic_graph":{"graph_id":"g","nodes":[
  {"id":"a","kind":"entity_ref","external_ref":"demo:alice","labels":{"en":"Alice"}},
  {"id":"b","kind":"entity_ref","external_ref":"demo:pump","labels":{"en":"pump"}},
  {"id":"v","kind":"concept_ref","concept_ref":"demo:repair"}],
  "statements":[{"id":"s","predicate_ref":"demo:repair_event","polarity":"positive","arguments":[
   {"role_ref":"semantic-role:agent","value_id":"a"},
   {"role_ref":"semantic-role:patient","value_id":"b"},
   {"role_ref":"semantic-role:event_type","value_id":"v"}]}]},
 "obligations":[{"obligation_id":"o","semantic_refs":["s"],"force":"ASSERT"}],
 "context":{"target_language":"en"},
 "constraints":{"allowed_block_kinds":["utterance"]},
 "capability_profile":"sa-core-1"})
cp=CommunicationPlanner().plan(req)
lp=GenericLanguagePlanner().plan(req,cp,LexicalPlanningContext("en",{}))
CoverageValidator().validate_plan(req,lp)
negative_ok=False
try:
 bad=type(lp)(lp.plan_id,lp.language,lp.locale,lp.blocks,(),lp.capability_profile)
 CoverageValidator().validate_plan(req,bad)
except (SemantikArchitectError,ValueError):
 negative_ok=True
print(json.dumps({"communication_items":len(cp.items),"operation":lp.units[0].operation_id,"obligations":list(lp.units[0].obligation_ids),"semantic_refs":list(lp.units[0].semantic_refs),"negative_coverage_rejected":negative_ok}))
'''
    probe = run_target_python(cfg, ["-c", script], timeout=60)
    data = json_from_stdout(probe)
    valid = (
        probe.get("exit_code") == 0
        and isinstance(data, dict)
        and data.get("operation") == "clause.transitive_event"
        and data.get("obligations") == ["o"]
        and data.get("semantic_refs") == ["s"]
        and data.get("negative_coverage_rejected") is True
    )
    report.add(
        "semantik.faithfulness.core_probe",
        "PASS" if valid else "FAIL",
        "faithfulness",
        "The pure core preserves obligation/semantic-reference coverage and selects the expected operation without a runtime."
        if valid
        else "The pure semantic→communication→language planning/coverage probe failed.",
        evidence=data if isinstance(data, dict) else probe,
    )

    bridge = root / "src/semantik_architect/adapters/realization/gf/bridge.py"
    render = root / "src/semantik_architect/application/use_cases/render_communication.py"
    source = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (bridge, render)
        if path.is_file()
    ).lower()
    forbidden = [token for token in ("fallback english", "safe_mode", "family_engine") if token in source]
    report.add(
        "semantik.faithfulness.no_hidden_fallback",
        "FAIL" if forbidden else "PASS",
        "faithfulness",
        "The canonical realization path contains no hidden language/family fallback implementation."
        if not forbidden
        else "Hidden fallback markers exist in the canonical realization path.",
        evidence=forbidden or None,
    )
