"""Bindings to SK03/SK04/SK06; all arguments are trusted backend dependencies.

snapshot denotes an independently established shared corpus revision. Do not
invent a common label for unrelated Genie and retrieval data to bypass checks.
"""
from copy import deepcopy
from sbs.comparison import compare
from sbs.retrieval import retrieve
from . import Tool


def retrieval_tool(index, scope, *, snapshot, mode, **retrieval_options):
    def call(question, context):
        out=retrieve(index,question,context,scope,**retrieval_options)
        return {**out,'snapshot':snapshot}
    return Tool(call,mode)


def genie_tool(adapter, *, mode):
    # Legacy ask(question) cannot attest family/pair/provision: fail closed.
    def call(question, context):
        scoped=getattr(adapter,'ask_scoped',None)
        if not callable(scoped):
            return {'status':'conflict','limitations':['genie_context_binding_unavailable']}
        out=scoped(question,context=deepcopy(context))
        if not isinstance(out,dict):
            return {'status':'error'}
        if out.get('status') in ('completed','partial','ready') and (
                out.get('context')!=context or out.get('scope_verified') is not True):
            return {'status':'conflict','limitations':['genie_context_mismatch']}
        return out
    return Tool(call,mode)


def comparison_tool(bundles, *, snapshot, mode):
    def call(question, context):
        pair=context['pair']
        sides=[bundles.get((pair[s]['document_id'],pair[s]['version_id'])) for s in ('before','after')]
        if any(b is None for b in sides):
            return {'status':'insufficient','snapshot':snapshot,'limitations':['missing_comparison_counterpart']}
        output=compare(deepcopy(pair),*deepcopy(sides),coverage='partial')
        return {**output,'status':'partial','snapshot':snapshot}
    return Tool(call,mode)
