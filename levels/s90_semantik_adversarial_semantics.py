from __future__ import annotations

from levelupdiag_core.semantik import json_from_stdout, run_target_python


def run(cfg, report):
    script = r'''
import json
from semantik_architect.domain.communication.request import CommunicationRequest
from semantik_architect.application.validation.request_validation import RequestValidator
from semantik_architect.application.validation.coverage import CoverageValidator
from semantik_architect.application.planning.communication_planner import CommunicationPlanner
from semantik_architect.application.planning.language_planner import GenericLanguagePlanner
from semantik_architect.application.use_cases.render_communication import RenderCommunication
from semantik_architect.domain.language.lexical import LexicalPlanningContext
from semantik_architect.domain.language.language_plan import LanguagePlan, LanguageBlockPlan
from semantik_architect.domain.language.realization_unit import RealizationUnit
from semantik_architect.domain.errors import SemantikArchitectError


def request(*, roles=None, polarity="positive", force="ASSERT", obligations=None,
            supporting_context=None, constraints=None, deadline=None):
    roles = roles or [
        ("semantic-role:agent", "a"),
        ("semantic-role:patient", "b"),
        ("semantic-role:event_type", "v"),
    ]
    nodes = [
        {"id":"a","kind":"entity_ref","external_ref":"demo:alice","labels":{"en":"Alice"}},
        {"id":"b","kind":"entity_ref","external_ref":"demo:pump","labels":{"en":"pump"}},
        {"id":"c","kind":"entity_ref","external_ref":"demo:bob","labels":{"en":"Bob"}},
        {"id":"v","kind":"concept_ref","concept_ref":"demo:repair"},
        {"id":"x","kind":"concept_ref","concept_ref":"demo:class"},
    ]
    data = {
        "schema_version":"1.0",
        "semantic_graph":{"graph_id":"g","nodes":nodes,"statements":[{
            "id":"s","predicate_ref":"demo:event","polarity":polarity,
            "arguments":[{"role_ref":r,"value_id":v} for r,v in roles],
        }]},
        "obligations": obligations or [{"obligation_id":"o","semantic_refs":["s"],"force":force}],
        "supporting_context": supporting_context or [],
        "context":{"target_language":"en"},
        "constraints": constraints or {"allowed_block_kinds":["utterance","question"]},
        "capability_profile":"sa-core-1",
    }
    if deadline is not None:
        data["deadline"] = deadline
    return CommunicationRequest.from_dict(data)


def expect_code(fn, code):
    try:
        fn()
    except SemantikArchitectError as exc:
        return exc.envelope.code == code, exc.envelope.code
    except Exception as exc:
        return False, type(exc).__name__ + ":" + str(exc)
    return False, "no-error"


def plan(req):
    RequestValidator().validate(req)
    cp = CommunicationPlanner().plan(req)
    lp = GenericLanguagePlanner().plan(req, cp, LexicalPlanningContext(req.context.target_language, {}))
    CoverageValidator().validate_plan(req, lp)
    return lp

cases = {}

# Duplicate obligation IDs must be rejected.
dup = request(obligations=[
    {"obligation_id":"o","semantic_refs":["s"],"force":"ASSERT"},
    {"obligation_id":"o","semantic_refs":["s"],"force":"ASSERT"},
])
cases["duplicate_obligation_ids"] = expect_code(lambda: RequestValidator().validate(dup), "SA-REQ-001")

# Missing semantic references must be rejected.
missing = request(obligations=[{"obligation_id":"o","semantic_refs":["missing"],"force":"ASSERT"}])
cases["missing_semantic_ref"] = expect_code(lambda: RequestValidator().validate(missing), "SA-REQ-001")

# Unknown supporting-context subjects must be rejected.
support = request(supporting_context=[{"subject_id":"ghost","property_ref":"sa:operation","value":"clause.transitive_event"}])
cases["unknown_support_subject"] = expect_code(lambda: RequestValidator().validate(support), "SA-REQ-001")

# Required framing cannot be requested if utterances are forbidden.
opening = request(constraints={"allowed_block_kinds":["question"],"opening_policy":"required"})
cases["impossible_required_opening"] = expect_code(lambda: RequestValidator().validate(opening), "SA-CON-001")

# Deadline is checked before any runtime access.
expired = request(deadline="2000-01-01T00:00:00Z")
renderer = RenderCommunication(
    runtime_catalog=object(), capabilities=object(), lexical_knowledge=object(),
    lexical_binding=object(), realizer=object()
)
cases["expired_deadline"] = expect_code(lambda: renderer.execute(expired), "SA-OPS-001")

# Coverage must reject both missing and unknown obligation IDs.
base = request()
lp = plan(base)
missing_unit = RealizationUnit("um", lp.units[0].operation_id, lp.units[0].role_bindings, lp.units[0].feature_bindings, lp.units[0].lexical_slots, (), ("s",), "bm")
bad_missing = LanguagePlan("missing", "en", None, (LanguageBlockPlan("bm","utterance",("um",),()),), (missing_unit,), "sa-core-1")
cases["coverage_missing"] = expect_code(lambda: CoverageValidator().validate_plan(base, bad_missing), "SA-SEM-002")
bad_unit = RealizationUnit("ux", "clause.transitive_event", {}, {}, {}, ("unknown",), ("s",), "bx")
bad_unknown = LanguagePlan("bad", "en", None, (LanguageBlockPlan("bx","utterance",("ux",),("unknown",)),), (bad_unit,), "sa-core-1")
cases["coverage_unknown"] = expect_code(lambda: CoverageValidator().validate_plan(base, bad_unknown), "SA-SEM-002")

# Negative polarity is semantic and must survive planning.
neg = plan(request(polarity="negative"))
cases["negative_polarity_preserved"] = (neg.units[0].feature_bindings.get("polarity") == "negative", neg.units[0].feature_bindings.get("polarity"))

# Operation-selection matrix for canonical semantic-role shapes.
matrix = [
    ([('semantic-role:agent','a'),('semantic-role:event_type','v')], 'ASSERT', 'clause.intransitive_event'),
    ([('semantic-role:agent','a'),('semantic-role:patient','b'),('semantic-role:event_type','v')], 'ASSERT', 'clause.transitive_event'),
    ([('semantic-role:agent','a'),('semantic-role:patient','b'),('semantic-role:recipient','c'),('semantic-role:event_type','v')], 'ASSERT', 'clause.ditransitive_event'),
    ([('semantic-role:possessor','a'),('semantic-role:possessed','b')], 'ASSERT', 'clause.possession'),
    ([('semantic-role:agent','a'),('semantic-role:class','x')], 'ASSERT', 'clause.copular_classification'),
    ([('semantic-role:agent','a'),('semantic-role:attribute','x')], 'ASSERT', 'clause.copular_attribute'),
    ([('semantic-role:agent','a'),('semantic-role:location','b')], 'ASSERT', 'clause.locative'),
    ([('semantic-role:entity','a')], 'ASSERT', 'clause.existential'),
    ([('semantic-role:agent','a'),('semantic-role:patient','b'),('semantic-role:event_type','v')], 'DIRECT', 'directive.action'),
    ([('semantic-role:agent','a'),('semantic-role:patient','b'),('semantic-role:event_type','v')], 'ASK', 'question.polar'),
]
ops = []
for roles, force, expected in matrix:
    actual = plan(request(roles=roles, force=force)).units[0].operation_id
    ops.append({"expected":expected,"actual":actual,"ok":actual==expected})
cases["operation_matrix"] = (all(x["ok"] for x in ops), ops)

# Unknown explicit operation hints must fail with the stable SA language-planning envelope.
# A raw Python ValueError is a contract leak and must make the diagnostic fail.
hinted = request(supporting_context=[{"subject_id":"s","property_ref":"sa:operation","value":"unknown.operation"}])
cases["unknown_operation_hint"] = expect_code(lambda: plan(hinted), "SA-LANG-003")

print(json.dumps({"cases":cases,"passed":all(v[0] for v in cases.values())}, default=str))
'''
    result = run_target_python(cfg, ["-c", script], timeout=120)
    data = json_from_stdout(result)
    passed = result.get("exit_code") == 0 and isinstance(data, dict) and data.get("passed") is True
    report.add(
        "semantik.deep.adversarial_semantics",
        "PASS" if passed else "FAIL",
        "adversarial_semantics",
        "Adversarial semantic, constraint, deadline, operation-selection and coverage probes all fail closed as required."
        if passed else "One or more adversarial semantic/faithfulness probes exposed a contract violation.",
        evidence=data if isinstance(data, dict) else result,
        recommendation=None if passed else "Inspect the failing case(s); do not weaken the invariant to make the probe pass.",
    )
