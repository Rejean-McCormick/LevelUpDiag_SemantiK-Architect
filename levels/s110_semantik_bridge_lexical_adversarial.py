from __future__ import annotations

from levelupdiag_core.semantik import json_from_stdout, run_target_python


def run(cfg, report):
    script = r'''
import hashlib, json, tempfile
from pathlib import Path
from semantik_architect.adapters.realization.gf import GfBridgeRealizer
from semantik_architect.adapters.lexical.local_lexicon import RuntimeJsonLexiconAdapter
from semantik_architect.application.ports.runtime_catalog import RuntimeArtifact, RuntimeSetDescriptor
from semantik_architect.domain.language.language_plan import LanguagePlan, LanguageBlockPlan
from semantik_architect.domain.language.realization_unit import RealizationUnit
from semantik_architect.domain.language.lexical import LexicalBinding, LexicalBindingSet, LexicalPlanningContext
from semantik_architect.domain.communication.request import CommunicationRequest
from semantik_architect.domain.errors import SemantikArchitectError

class FakePgf:
    def __init__(self,path): self.path=path
    def linearize(self,expr,concrete): return f'{concrete}:{expr}'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d): Path(p).write_text(json.dumps(d),encoding='utf-8')
def errcode(fn):
    try: fn()
    except SemantikArchitectError as exc: return exc.envelope.code
    except Exception as exc: return type(exc).__name__+':'+str(exc)
    return None

def runtime(root, *, contract='1.0', bridge_contract='1.0', concrete='Eng', include_lex=True):
    root=Path(root)
    grammar=root/'g.pgf'; grammar.write_bytes(b'x')
    bridge=root/'bridge.json'; dump(bridge, {'schema_version':'1.0','contract_version':bridge_contract,'operations':{
      'clause.transitive_event':{'requires':['agent','predicate','patient'],
        'expression':'Do {agent} {predicate} {patient}','consumes_features':['polarity']}}})
    arts=[RuntimeArtifact('grammar','g',sha(grammar),grammar),RuntimeArtifact('other','sa-gf-bridge-v1',sha(bridge),bridge)]
    if include_lex:
      lex=root/'lex.json'; dump(lex, {'schema_version':'1.0','lexicon_id':'lex','entries':[
        {'semantic_ref':'demo:repair','language':'en','lexical_ref':'repair_V2','binding_kind':'gf_expr'}]})
      arts.append(RuntimeArtifact('lexical','lex',sha(lex),lex))
    caps={'languages':{'en':{'status':'RELEASED','concrete':concrete,'profiles':[]}}}
    return RuntimeSetDescriptor('rt',contract,'RELEASED',tuple(arts),caps,{},root)

def unit(slots=None, features=None):
    return RealizationUnit('u','clause.transitive_event',{},features or {'polarity':'positive'},slots or {'agent':'a','predicate':'v','patient':'b'},('o',),('s',),'b1')
def plan(u): return LanguagePlan('lp','en',None,(LanguageBlockPlan('b1','utterance',('u',),('o',)),),(u,),'sa-core-1')
def binds(extra=False):
    x=[LexicalBinding('u','agent','Alice','literal'),LexicalBinding('u','predicate','repair_V2'),LexicalBinding('u','patient','pump','literal')]
    if extra: x.append(LexicalBinding('u','deadline','16:00','literal'))
    return LexicalBindingSet('lex',tuple(x))

cases={}
with tempfile.TemporaryDirectory() as td:
    rt=runtime(td); real=GfBridgeRealizer(runtime_factory=FakePgf)
    try:
      text=real.realize(plan(unit()),binds(),rt).units[0].text
      cases['fully_consumed_bridge']=(text.startswith('Eng:'), text)
    except Exception as exc: cases['fully_consumed_bridge']=(False,type(exc).__name__+':'+str(exc))

with tempfile.TemporaryDirectory() as td:
    rt=runtime(td); u=unit({'agent':'a','predicate':'v','patient':'b','deadline':'t'})
    cases['unconsumed_lexical_slot']=(errcode(lambda:GfBridgeRealizer(runtime_factory=FakePgf).realize(plan(u),binds(extra=True),rt))=='SA-GF-001', 'expected SA-GF-001')

with tempfile.TemporaryDirectory() as td:
    rt=runtime(td)
    u=unit(features={'polarity':'positive','register':'formal'})
    cases['unconsumed_feature']=(errcode(lambda:GfBridgeRealizer(runtime_factory=FakePgf).realize(plan(u),binds(),rt))=='SA-GF-001','expected SA-GF-001')

with tempfile.TemporaryDirectory() as td:
    rt=runtime(td,contract='1.0',bridge_contract='2.0')
    cases['bridge_contract_mismatch']=(errcode(lambda:GfBridgeRealizer(runtime_factory=FakePgf).realize(plan(unit()),binds(),rt))=='SA-GF-001','expected SA-GF-001')

with tempfile.TemporaryDirectory() as td:
    rt=runtime(td,concrete='')
    cases['missing_concrete_language']=(errcode(lambda:GfBridgeRealizer(runtime_factory=FakePgf).realize(plan(unit()),binds(),rt))=='SA-LANG-001','expected SA-LANG-001')

# Exact lexical binding: literals/entities may surface from supplied labels, concepts may not be guessed.
req=CommunicationRequest.from_dict({
  'schema_version':'1.0','semantic_graph':{'graph_id':'g','nodes':[
    {'id':'a','kind':'entity_ref','external_ref':'demo:alice','labels':{'en':'Alice'}},
    {'id':'b','kind':'entity_ref','external_ref':'demo:pump','labels':{'en':'pump'}},
    {'id':'v','kind':'concept_ref','concept_ref':'demo:repair'}],
    'statements':[{'id':'s','predicate_ref':'demo:event','polarity':'positive','arguments':[
      {'role_ref':'semantic-role:agent','value_id':'a'},{'role_ref':'semantic-role:patient','value_id':'b'},{'role_ref':'semantic-role:event_type','value_id':'v'}]}]},
  'obligations':[{'obligation_id':'o','semantic_refs':['s'],'force':'ASSERT'}],
  'context':{'target_language':'en'},'constraints':{'allowed_block_kinds':['utterance']},'capability_profile':'sa-core-1'})
with tempfile.TemporaryDirectory() as td:
    rt=runtime(td,include_lex=False)
    adapter=RuntimeJsonLexiconAdapter()
    ctx=LexicalPlanningContext('en',{})
    code=errcode(lambda:adapter.bind(req,plan(unit()),ctx,rt))
    cases['missing_concept_lexeme_not_guessed']=(code=='SA-LEX-002',code)

with tempfile.TemporaryDirectory() as td:
    rt=runtime(td,include_lex=True)
    adapter=RuntimeJsonLexiconAdapter(); ctx=LexicalPlanningContext('en',{})
    try:
      got=adapter.bind(req,plan(unit()),ctx,rt)
      mapping={b.slot_id:b.lexical_ref for b in got.bindings}
      cases['exact_lexical_binding']=(mapping.get('predicate')=='repair_V2' and mapping.get('agent')=='Alice' and mapping.get('patient')=='pump',mapping)
    except Exception as exc: cases['exact_lexical_binding']=(False,type(exc).__name__+':'+str(exc))

print(json.dumps({'cases':cases,'passed':all(v[0] for v in cases.values())}, default=str))
'''
    result = run_target_python(cfg, ["-c", script], timeout=180)
    data = json_from_stdout(result)
    passed = result.get("exit_code") == 0 and isinstance(data, dict) and data.get("passed") is True
    report.add(
        "semantik.deep.bridge_lexical_adversarial",
        "PASS" if passed else "FAIL",
        "bridge_lexical_adversarial",
        "The GF bridge rejects unconsumed semantics/features and incompatible contracts; lexical binding refuses missing concepts instead of guessing."
        if passed else "Bridge or lexical adversarial probes exposed a silent-loss, contract or guessing path.",
        evidence=data if isinstance(data, dict) else result,
    )
