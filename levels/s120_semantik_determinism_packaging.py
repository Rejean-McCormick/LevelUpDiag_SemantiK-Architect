from __future__ import annotations

from levelupdiag_core.semantik import json_from_stdout, run_target_python


def run(cfg, report):
    script = r'''
import concurrent.futures, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import semantik_architect
from semantik_architect.bootstrap import build_container
from semantik_architect.adapters.realization.gf import GfBridgeRealizer
from semantik_architect.domain.communication.request import CommunicationRequest

class FakePgfRuntime:
    def __init__(self,path): self.path=path
    def linearize(self,expr,concrete_language): return f'{concrete_language}:{expr}'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,data): Path(path).write_text(json.dumps(data),encoding='utf-8')

def make_runtime(root):
    r=Path(root)/'r1'; r.mkdir(parents=True)
    grammar=r/'grammar.pgf'; grammar.write_bytes(b'fake-pgf')
    bridge=r/'bridge.json'; dump(bridge, {'schema_version':'1.0','contract_version':'1.0','operations':{
      'clause.transitive_event':{'requires':['agent','predicate','patient'],'expression':'Do {agent} {predicate} {patient}','consumes_features':['polarity']}}})
    lex=r/'lexicon.json'; dump(lex, {'schema_version':'1.0','lexicon_id':'lex-en-1','entries':[
      {'semantic_ref':'demo:repair','language':'en','lexical_ref':'repair_V2','binding_kind':'gf_expr'}]})
    profile=r/'profile.json'; dump(profile, {'schema_version':'1.0','profile_id':'sa-core','profile_version':1,
      'required_operations':['clause.transitive_event'],'required_features':[],'required_block_kinds':['utterance'],'test_suite_ref':'suite:sa-core-1'})
    evidence=r/'evidence.json'; dump(evidence, {'passed':True})
    cap=r/'capabilities.json'; dump(cap, {'schema_version':'1.0','manifest_id':'cap1','runtime_set_id':'rt1','languages':{
      'en':{'status':'RELEASED','concrete':'SAGrammarEng','profiles':[{'profile_id':'sa-core-1','status':'RELEASED','evidence_ref':'evidence.json'}]}}})
    manifest={'schema_version':'1.0','runtime_set_id':'rt1','sa_version_range':'>=1.0,<2.0','sa_gf_contract_version':'1.0','artifacts':[
      {'artifact_type':'grammar','artifact_id':'grammar-en','sha256':sha(grammar),'path':'grammar.pgf'},
      {'artifact_type':'lexical','artifact_id':'lex-en','sha256':sha(lex),'path':'lexicon.json'},
      {'artifact_type':'other','artifact_id':'sa-gf-bridge-v1','sha256':sha(bridge),'path':'bridge.json'},
      {'artifact_type':'other','artifact_id':'capability-profile-sa-core-1','sha256':sha(profile),'path':'profile.json'}],
      'capability_manifest_ref':'capabilities.json','capability_manifest_sha256':sha(cap),
      'conformance_evidence_refs':['evidence.json'],'conformance_evidence_sha256':{'evidence.json':sha(evidence)},'status':'RELEASED'}
    dump(r/'runtime.manifest.json',manifest)

def request():
    return CommunicationRequest.from_dict({'schema_version':'1.0','request_id':'det',
      'semantic_graph':{'graph_id':'g','nodes':[
        {'id':'a','kind':'entity_ref','external_ref':'demo:alice','labels':{'en':'Alice'}},
        {'id':'b','kind':'entity_ref','external_ref':'demo:pump','labels':{'en':'pump'}},
        {'id':'v','kind':'concept_ref','concept_ref':'demo:repair'}],
        'statements':[{'id':'s','predicate_ref':'demo:event','polarity':'positive','arguments':[
          {'role_ref':'semantic-role:agent','value_id':'a'},{'role_ref':'semantic-role:patient','value_id':'b'},{'role_ref':'semantic-role:event_type','value_id':'v'}]}]},
      'obligations':[{'obligation_id':'o','semantic_refs':['s'],'force':'ASSERT'}],
      'context':{'target_language':'en'},'constraints':{'allowed_block_kinds':['utterance']},'capability_profile':'sa-core-1'})

cases={}
expected_version=semantik_architect.__version__
with tempfile.TemporaryDirectory() as td:
    make_runtime(td)
    app=build_container(td,realizer=GfBridgeRealizer(runtime_factory=FakePgfRuntime))
    req=request()
    seq=[app.render.execute(req) for _ in range(20)]
    ids={x.deterministic_result_id for x in seq}; texts={x.plain_text for x in seq}
    cases['sequential_determinism']=(len(ids)==1 and len(texts)==1, {'ids':list(ids),'texts':list(texts)})
    def one(_):
      x=app.render.execute(req); return x.deterministic_result_id,x.plain_text
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
      parallel=list(ex.map(one,range(32)))
    cases['parallel_determinism']=(len(set(parallel))==1, {'unique_results':len(set(parallel))})
    # Operational timing may differ but must not perturb deterministic identity.
    cases['operational_metadata_excluded']=(all(x.deterministic_result_id==seq[0].deterministic_result_id for x in seq), [x.operational for x in seq[:3]])

# Build/import a wheel from a temporary source copy so the target checkout stays untouched.
with tempfile.TemporaryDirectory() as td:
    td=Path(td); source=td/'source'; wheelhouse=td/'wheelhouse'; install=td/'install'; wheelhouse.mkdir(); install.mkdir()
    ignore=shutil.ignore_patterns('.git','.levelupdiag','__pycache__','.pytest_cache','.mypy_cache','build','dist','*.egg-info','*.pyc')
    shutil.copytree(Path.cwd(), source, ignore=ignore)
    pip_env={**os.environ,'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    build=subprocess.run([sys.executable,'-m','pip','wheel',str(source),'--no-deps','--no-build-isolation','--no-index','-w',str(wheelhouse)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=pip_env)
    wheels=list(wheelhouse.glob('*.whl'))
    if build.returncode!=0 or len(wheels)!=1:
      cases['wheel_build_isolated']=(False, {'exit_code':build.returncode,'stdout':build.stdout[-4000:],'stderr':build.stderr[-4000:],'wheels':[str(x) for x in wheels]})
      cases['wheel_import_isolated']=(False,'wheel-not-built')
    else:
      cases['wheel_build_isolated']=(True,wheels[0].name)
      inst=subprocess.run([sys.executable,'-m','pip','install',str(wheels[0]),'--no-deps','--no-index','--target',str(install)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=pip_env)
      code="import sys; sys.path.insert(0, %r); import semantik_architect; print(semantik_architect.__version__)" % str(install)
      imp=subprocess.run([sys.executable,'-I','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
      cases['wheel_import_isolated']=(inst.returncode==0 and imp.returncode==0 and imp.stdout.strip()==expected_version, {'install_code':inst.returncode,'import_code':imp.returncode,'stdout':imp.stdout.strip(),'stderr':imp.stderr[-2000:]})

print(json.dumps({'cases':cases,'passed':all(v[0] for v in cases.values())}, default=str))
'''
    result = run_target_python(cfg, ["-c", script], timeout=420)
    data = json_from_stdout(result)
    if result.get("timed_out"):
        verdict = "INFRA_ERROR"
    elif result.get("exit_code") == 0 and isinstance(data, dict) and data.get("passed") is True:
        verdict = "PASS"
    else:
        verdict = "FAIL"
        if isinstance(data, dict):
            build_case = (data.get("cases") or {}).get("wheel_build_isolated")
            detail = str(build_case).lower() if build_case is not None else ""
            if "setuptools" in detail and ("no module named" in detail or "backend" in detail):
                verdict = "BLOCKED"
    report.add(
        "semantik.deep.determinism_packaging",
        verdict,
        "determinism_packaging",
        "Repeated sequential/parallel renders are deterministic and a wheel built from a temporary clean copy imports in isolation."
        if verdict == "PASS" else "Determinism, concurrency or isolated packaging/import probing exposed a failure.",
        evidence=data if isinstance(data, dict) else result,
        recommendation=None if verdict == "PASS" else "Inspect the failing subcase. Packaging is performed only on a temporary copy; do not disable the check to avoid fixing package metadata/imports.",
    )
