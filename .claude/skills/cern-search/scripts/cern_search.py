#!/usr/bin/env python3
"""Search CERN Indico and GitLab using tokens from ./.env (stdlib only)."""
import argparse, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

INDICO = 'https://indico.cern.ch'
GITLAB = 'https://gitlab.cern.ch/api/v4'


def load_env():
    for d in [Path.cwd(), *Path.cwd().parents]:
        f = d / '.env'
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
            return d
    sys.exit('no .env found')


ROOT = load_env()


def _get(url, headers, raw=False):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read() if raw else json.load(r)


def indico(path, raw=False):
    return _get(INDICO + path, {'Authorization': 'Bearer ' + os.environ['TOKEN']}, raw)


def gitlab(path):
    return _get(GITLAB + path, {'PRIVATE-TOKEN': os.environ['GITLAB_TOKEN']})


def me():
    u = indico('/api/user/')
    return f"{u['first_name']} {u['last_name']}"


def search(q, typ, pages=None):
    p = 1
    while True:
        d = indico('/search/api/search?' + urllib.parse.urlencode({'q': q, 'type': typ, 'page': p}))
        yield from d.get('results', [])
        if p >= d.get('pages', 1) or (pages and p >= pages):
            break
        p += 1


def is_mine(r, name):
    return any((x.get('name') or '').lower() == name.lower() for x in r.get('persons', []))


def my_contribs():
    name = me()
    return name, [r for r in search(name, 'contribution') if is_mine(r, name)]


def fmt(r):
    who = ', '.join(x.get('name', '') for x in r.get('persons', []))[:50]
    return f"{(r.get('start_dt') or '')[:10]:10} | {r.get('title') or r.get('filename')} | {who} | {INDICO}{r['url']}"


def cmd_indico(a):
    mine_ids = None
    if a.mine:
        _, mc = my_contribs()
        mine_ids = {r['url'].split('/')[4] for r in mc if '/contributions/' in r['url']}
    n = 0
    for r in search(a.query, a.type, a.pages):
        parts = r['url'].split('/')
        if mine_ids is not None and not (len(parts) > 4 and parts[3] == 'contributions' and parts[4] in mine_ids):
            continue
        print(fmt(r)); n += 1
    print(f'-- {n} results', file=sys.stderr)


def cmd_mytalks(a):
    name, mc = my_contribs()
    pat = re.compile(a.grep, re.I) if a.grep else None
    mc = sorted(mc, key=lambda r: r.get('start_dt') or '')
    for r in mc:
        if not pat or pat.search((r.get('title') or '') + ' ' + (r.get('description') or '')):
            print(fmt(r))
    print(f'-- {len(mc)} contributions by {name}', file=sys.stderr)


def cmd_download(a):
    path = a.url.replace(INDICO, '')
    out = Path(a.out_dir or ROOT / 'materials'); out.mkdir(parents=True, exist_ok=True)
    f = out / urllib.parse.unquote(path.rstrip('/').split('/')[-1])
    f.write_bytes(indico(path, raw=True))
    print(f)


def cmd_gitlab_projects(a):
    user = os.environ.get('GITLAB_USER') or gitlab('/user')['username']
    projs = {}
    s = ('&search=' + urllib.parse.quote(a.search)) if a.search else ''
    for q in ['/projects?membership=true', f'/users/{user}/projects', f'/users/{user}/contributed_projects']:
        for pg in range(1, 20):
            r = gitlab(f'{q}{"&" if "?" in q else "?"}per_page=100&simple=true&page={pg}{s}')
            if not r: break
            for p in r: projs[p['id']] = p
    for p in sorted(projs.values(), key=lambda p: p['last_activity_at'], reverse=True):
        if a.search and a.search.lower() not in (p['path_with_namespace'] + ' ' + (p.get('description') or '')).lower():
            continue
        print(f"{p['last_activity_at'][:10]} | {p['path_with_namespace']} | {p['web_url']}")


def cmd_gitlab_code(a):
    pid = urllib.parse.quote(a.project, safe='')
    for r in gitlab(f'/projects/{pid}/search?scope=blobs&per_page=50&search=' + urllib.parse.quote(a.term)):
        line = (r.get('data') or '').strip().splitlines()
        print(f"{r['path']}:{r.get('startline')} | {line[0][:120] if line else ''}")


p = argparse.ArgumentParser()
sp = p.add_subparsers(dest='cmd', required=True)
x = sp.add_parser('indico'); x.add_argument('query'); x.add_argument('--type', default='contribution')
x.add_argument('--mine', action='store_true'); x.add_argument('--pages', type=int, default=5); x.set_defaults(f=cmd_indico)
x = sp.add_parser('mytalks'); x.add_argument('--grep'); x.set_defaults(f=cmd_mytalks)
x = sp.add_parser('download'); x.add_argument('url'); x.add_argument('out_dir', nargs='?'); x.set_defaults(f=cmd_download)
x = sp.add_parser('gitlab-projects'); x.add_argument('--search'); x.set_defaults(f=cmd_gitlab_projects)
x = sp.add_parser('gitlab-code'); x.add_argument('term'); x.add_argument('--project', required=True); x.set_defaults(f=cmd_gitlab_code)
a = p.parse_args(); a.f(a)
