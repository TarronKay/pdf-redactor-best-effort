# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Pure state keys and manual-region merge for the streamlined UI."""
import hashlib,json

def clone(value):return json.loads(json.dumps(value))

def page_key(data,page,regions,options,mode):
    boxes=sorted({tuple(r['rect']) for r in regions if r['page']==page})
    return hashlib.sha256(json.dumps(dict(source=hashlib.sha256(data).hexdigest(),page=page,boxes=boxes,options=options,mode=mode),sort_keys=True).encode()).hexdigest()

def merge_manual(suggestions,current):
    result=[];seen=set()
    # Preserve manual ownership when its box duplicates an automatic proposal.
    for region in [r for r in current if r.get('reason')=='manual']+list(suggestions):
        key=(region['page'],tuple(region['rect']))
        if key not in seen:result.append(clone(region));seen.add(key)
    if len(result)>2000:raise ValueError('Too many redactions; review and reduce them before continuing.')
    return result
