"""Helpers for reading/writing the Nuxt payload (<script id="__NUXT_DATA__">) in index.html.

Nuxt serialises state with `devalue`: a flat JSON array where objects/arrays hold indices
into that same array. `resolve()` turns it back into plain Python data for reading.
"""
import json, re

PAYLOAD_RE = re.compile(r'(<script[^>]*id="__NUXT_DATA__"[^>]*>)(.*?)(</script>)', re.S)
WRAPPERS = {'Reactive', 'ShallowReactive', 'Ref', 'ShallowRef', 'EmptyRef', 'EmptyShallowRef'}


def load(html):
    m = PAYLOAD_RE.search(html)
    return json.loads(m.group(2))


def dump(html, arr):
    text = json.dumps(arr, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return PAYLOAD_RE.sub(lambda m: m.group(1) + text + m.group(3), html, count=1)


def resolve(arr, i=0, seen=None):
    seen = seen or {}
    if not isinstance(i, int) or i < 0:
        return None
    if i in seen:
        return seen[i]
    v = arr[i]
    if isinstance(v, list):
        if v and isinstance(v[0], str) and v[0] in WRAPPERS:
            return resolve(arr, v[1], seen)
        if v and isinstance(v[0], str) and v[0] in ('Date', 'Set', 'Map', 'BigInt', 'RegExp', 'undefined'):
            return v
        out = []
        seen[i] = out
        out.extend(resolve(arr, x, seen) for x in v)
        return out
    if isinstance(v, dict):
        out = {}
        seen[i] = out
        for k, x in v.items():
            out[k] = resolve(arr, x, seen)
        return out
    return v
