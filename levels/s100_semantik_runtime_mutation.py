from __future__ import annotations

from levelupdiag_core.semantik import json_from_stdout, run_target_python


def run(cfg, report):
    script = r'''
import hashlib, json, tempfile
from pathlib import Path
from semantik_architect.adapters.runtime.filesystem import FilesystemRuntimeCatalog, ManifestCapabilityAdapter
from semantik_architect.conformance import RuntimeReleaseValidator
from semantik_architect.domain.errors import SemantikArchitectError


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, data): Path(p).write_text(json.dumps(data), encoding='utf-8')

def make_runtime(parent, runtime_id='rt1', *, language='en', evidence_passed=True,
                 sa_range='>=1.0,<2.0', include_profile=True):
    r=Path(parent)/runtime_id; r.mkdir(parents=True, exist_ok=True)
    grammar=r/'grammar.pgf'; grammar.write_bytes(b'fake-pgf')
    bridge=r/'bridge.json'; dump(bridge, {
      'schema_version':'1.0','contract_version':'1.0','operations':{
        'clause.transitive_event':{'requires':['agent','predicate','patient'],
          'expression':'Do {agent} {predicate} {patient}','consumes_features':['polarity']}
      }})
    lex=r/'lexicon.json'; dump(lex, {'schema_version':'1.0','lexicon_id':'lex1','entries':[
      {'semantic_ref':'demo:repair','language':language,'lexical_ref':'repair_V2','binding_kind':'gf_expr'}]})
    evidence=r/'evidence.json'; dump(evidence, {'passed':bool(evidence_passed)})
    cap=r/'capabilities.json'; dump(cap, {'schema_version':'1.0','manifest_id':'cap','runtime_set_id':runtime_id,'languages':{
      language:{'status':'RELEASED','concrete':'GrammarEng','profiles':[{'profile_id':'sa-core-1','status':'RELEASED','evidence_ref':'evidence.json'}]}}})
    artifacts=[
      {'artifact_type':'grammar','artifact_id':'grammar-en','sha256':sha(grammar),'path':'grammar.pgf'},
      {'artifact_type':'lexical','artifact_id':'lex-en','sha256':sha(lex),'path':'lexicon.json'},
      {'artifact_type':'other','artifact_id':'sa-gf-bridge-v1','sha256':sha(bridge),'path':'bridge.json'},
    ]
    if include_profile:
      profile=r/'profile.json'; dump(profile, {'schema_version':'1.0','profile_id':'sa-core','profile_version':1,
        'required_operations':['clause.transitive_event'],'required_features':[],
        'required_block_kinds':['utterance'],'test_suite_ref':'suite:sa-core-1'})
      artifacts.append({'artifact_type':'other','artifact_id':'capability-profile-sa-core-1','sha256':sha(profile),'path':'profile.json'})
    manifest={
      'schema_version':'1.0','runtime_set_id':runtime_id,'sa_version_range':sa_range,
      'sa_gf_contract_version':'1.0','artifacts':artifacts,
      'capability_manifest_ref':'capabilities.json','capability_manifest_sha256':sha(cap),
      'conformance_evidence_refs':['evidence.json'],
      'conformance_evidence_sha256':{'evidence.json':sha(evidence)},'status':'RELEASED'}
    dump(r/'runtime.manifest.json', manifest)
    return r


def code_of(fn):
    try: fn()
    except SemantikArchitectError as exc: return exc.envelope.code
    except Exception as exc: return type(exc).__name__ + ':' + str(exc)
    return None

cases={}
with tempfile.TemporaryDirectory() as td:
    make_runtime(td)
    cat=FilesystemRuntimeCatalog(td, sa_version='1.0.0')
    rel=RuntimeReleaseValidator(cat, ManifestCapabilityAdapter()).validate('rt1')
    cases['valid_runtime']=(rel.get('valid') is True, rel)

with tempfile.TemporaryDirectory() as td:
    r=make_runtime(td)
    cat=FilesystemRuntimeCatalog(td, sa_version='1.0.0')
    (r/'lexicon.json').write_text('{"tampered":true}',encoding='utf-8')
    rep=cat.validate('rt1')
    cases['tampered_artifact_hash']=(rep.get('valid') is False and any(str(x).startswith('sha256:lex-en') for x in rep.get('errors',[])), rep)

with tempfile.TemporaryDirectory() as td:
    r=make_runtime(td)
    cat=FilesystemRuntimeCatalog(td, sa_version='1.0.0')
    cat.list_runtime_sets()
    (r/'capabilities.json').write_text('{"tampered":true}',encoding='utf-8')
    rep=cat.validate('rt1')
    cases['tampered_capability_hash']=(rep.get('valid') is False and any('capability_manifest' in str(x) for x in rep.get('errors',[])), rep)

with tempfile.TemporaryDirectory() as td:
    make_runtime(td, evidence_passed=False)
    rep=FilesystemRuntimeCatalog(td, sa_version='1.0.0').validate('rt1')
    cases['failed_conformance_evidence']=(rep.get('valid') is False and any('conformance_not_passed' in str(x) for x in rep.get('errors',[])), rep)

with tempfile.TemporaryDirectory() as td:
    make_runtime(td, include_profile=False)
    cat=FilesystemRuntimeCatalog(td, sa_version='1.0.0')
    rep=RuntimeReleaseValidator(cat, ManifestCapabilityAdapter()).validate('rt1')
    cases['missing_profile_artifact']=(rep.get('valid') is False and any('profile_artifact_missing' in str(x) for x in rep.get('errors',[])), rep)

with tempfile.TemporaryDirectory() as td:
    make_runtime(td,'rt1'); make_runtime(td,'rt2')
    cat=FilesystemRuntimeCatalog(td, sa_version='1.0.0')
    code=code_of(lambda: cat.resolve('en','sa-core-1'))
    cases['ambiguous_runtime_rejected']=(code=='SA-RUN-003', code)
    dump(Path(td)/'activation.json', {'schema_version':'1.0','bindings':{'en|sa-core-1':'rt2'}})
    cat2=FilesystemRuntimeCatalog(td, sa_version='1.0.0')
    try:
      resolved=cat2.resolve('en','sa-core-1').runtime_set_id
      cases['explicit_activation_selects']=(resolved=='rt2', resolved)
    except Exception as exc:
      cases['explicit_activation_selects']=(False, type(exc).__name__+':'+str(exc))

with tempfile.TemporaryDirectory() as td:
    make_runtime(td, sa_range='>=2.0,<3.0')
    code=code_of(lambda: FilesystemRuntimeCatalog(td, sa_version='1.0.0').list_runtime_sets())
    cases['sa_version_mismatch_rejected']=(code=='SA-RUN-003', code)

print(json.dumps({'cases':cases,'passed':all(v[0] for v in cases.values())}, default=str))
'''
    result = run_target_python(cfg, ["-c", script], timeout=180)
    data = json_from_stdout(result)
    passed = result.get("exit_code") == 0 and isinstance(data, dict) and data.get("passed") is True
    report.add(
        "semantik.deep.runtime_mutation",
        "PASS" if passed else "FAIL",
        "runtime_mutation",
        "Synthetic RuntimeSets pass when intact and fail closed under hash, evidence, profile, activation and SA-version mutations."
        if passed else "RuntimeSet mutation testing exposed a release/integrity failure mode that does not fail closed correctly.",
        evidence=data if isinstance(data, dict) else result,
    )
