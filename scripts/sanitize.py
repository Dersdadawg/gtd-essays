"""Build a draft-free Quartz content folder from the Obsidian college-essay notes."""
import os, re, sys, shutil, datetime as dt

SRC = sys.argv[1]   # staged vault root (contains 200_PROJECTS, 000_INBOX)
OUT = sys.argv[2]   # quartz content dir
CARDS = os.path.join(SRC, '200_PROJECTS', '"College Essays"', 'Essay Cards')
INBOX = os.path.join(SRC, '000_INBOX')
PROJ = os.path.join(SRC, '200_PROJECTS')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan import SCHOOLS, COMMON_APP_DONE, DONE, PLAN
D = lambda x: dt.date.fromisoformat(x)
fmt = lambda x: D(x).strftime('%b %-d, %Y')
short = lambda x: D(x).strftime('%-m/%-d')
def key(school):
    return 'Cornell' if school.startswith('Cornell') else school
def days_worked(k):
    return ', '.join(short(d) for d, ss, _ in DONE if k in ss) or '—'
GDOC_LINK = '[Master Question List (Google Doc)](https://docs.google.com/document/d/1HgrO45v8nDYPUwoz0eBR0dgdfUxdrJf-7kCIJ1MtlG8/edit?usp=sharing)'

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(os.path.join(OUT, 'Essay Cards'))
os.makedirs(os.path.join(OUT, 'Schools'))

DEADLINES = {
    'Harvard': 'Nov 1, 2026 (REA)', 'UIUC': 'Nov 1, 2026 (EA)', 'UC': 'Nov 30, 2026',
    'Columbia': 'Jan 1, 2027', 'Northwestern': 'Jan 1, 2027', 'Princeton': 'Jan 1, 2027',
    'Yale': 'Jan 2, 2027', 'Dartmouth': 'Jan 2, 2027', 'Cornell': 'Jan 2, 2027',
    'MIT': 'Jan 4, 2027', 'CMU': 'Jan 4, 2027', 'Stanford': 'Jan 5, 2027', 'UPenn': 'Jan 5, 2027',
    'Brown': 'Jan 5, 2027', 'NYU': 'Jan 5, 2027', 'Georgetown': 'Jan 10, 2027', 'Common App': 'Nov 1, 2026',
}
GDOC = 'https://docs.google.com/document/d/1HgrO45v8nDYPUwoz0eBR0dgdfUxdrJf-7kCIJ1MtlG8/edit?usp=sharing'

# --- kanban stage per card ---
kanban = open(os.path.join(PROJ, 'College Essays Kanban.md')).read()
stage = {}
col = None
for line in kanban.splitlines():
    if line.startswith('## '):
        col = line[3:].strip()
    m = re.search(r'\[\[([^\]|]+)\]\]', line)
    if m and col:
        stage[m.group(1)] = col

def frontmatter(t):
    m = re.match(r'---\n(.*?)\n---\n', t, re.S)
    fm = {}
    if m:
        for l in m.group(1).splitlines():
            if ':' in l:
                k, v = l.split(':', 1)
                fm[k.strip()] = v.strip().strip('"')
        t = t[m.end():]
    return fm, t

def sections(body):
    """split on '## ' headings -> list of (heading or None, text)"""
    parts = re.split(r'(?m)^## ', body)
    out = [(None, parts[0])]
    for p in parts[1:]:
        h, _, rest = p.partition('\n')
        out.append((h.strip(), rest))
    return out

included = set()
cards = []
for fn in sorted(os.listdir(CARDS)):
    if not fn.endswith('.md'):
        continue
    name = fn[:-3]
    fm, body = frontmatter(open(os.path.join(CARDS, fn)).read())
    school = fm.get('school', name.split(' — ')[0])
    etype = fm.get('essay-type', '')
    secs = sections(body)
    head = secs[0][1]
    title = re.search(r'(?m)^# (.+)$', head)
    title = title.group(1).strip() if title else name
    prompt = re.search(r'(?ms)^> \[!question\][^\n]*\n((?:>.*(?:\n|$))*)', head)
    prompt_txt = prompt.group(0).replace('[!question]-', '[!question]') if prompt else ''
    feedback = next((t.strip() for h, t in secs if h and h.lower() == 'feedback'), '')
    has_draft = any(h and h.lower() not in ('feedback', 'notes / brainstorm') and
                    len(re.sub(r'\*\(.*?\)\*', '', t).split()) > 5 for h, t in secs)
    st = stage.get(name, '—')
    limit = re.search(r'\(([^()]*(?:words?|characters?|max|maximum)[^()]*)\)', prompt_txt, re.I)
    cards.append(dict(name=name, school=school, etype=etype, stage=st,
                      limit=limit.group(1) if limit else '—'))
    included.add(name)
    sk = 'Cornell' if school.startswith('Cornell') else school
    k = key(school)
    complete = st == 'Submitted' or name.startswith('Georgetown — Personal')
    if k == 'Common App':
        ca, cdate, dl = 'Yes · done ✅', COMMON_APP_DONE, 'Nov 1, 2026'
    else:
        plan_, dl_, is_ca, sdate, _ = SCHOOLS[k]
        ca = ('Yes · Common App done ✅' if is_ca else 'No (own application)')
        cdate = COMMON_APP_DONE if (complete and k in ('Harvard', 'UIUC') or name.startswith('Georgetown — Personal')) else sdate
        dl = fmt(dl_) + f' ({plan_})'
    cards[-1].update(complete=complete, cdate=cdate)
    when = f'{fmt(cdate)} ({"actual" if complete else "projected"})'
    school_cell = ("[[" + k + " Supplementals\\|" + school + "]]") if k != "Common App" else school
    rows = [('School', school_cell), ('Application deadline', dl), ('Common App school?', ca),
            ('Essay type', etype or '—'), ('Word limit', cards[-1]['limit']), ('Stage', f'**{st}**'),
            ('Complete?', '✅ Yes' if complete else '⬜ No'), ('Completion date', when),
            ('Days worked on', days_worked(k) + ' (see [[College Essays Work Log]])'),
            ('Working document', GDOC_LINK)]
    out = [f'---\ntitle: "{title}"\ntags: [essays, {k.lower().replace(" ", "-")}]\n---\n',
           '| | |\n|---|---|\n' + ''.join(f'| **{a}** | {b} |\n' for a, b in rows),
           '## Prompt\n', prompt_txt.strip() + '\n',
           '## Feedback\n', (feedback or '*(none yet)*') + '\n',
           '> [!note] Draft text is kept private. This page shows the prompt, status and feedback; the essay itself lives in the working document.\n']
    cards[-1]['body'] = '\n'.join(out)

# --- school index pages (replace dataview with static tables) ---
SCHOOL_FILES = {f[:-3]: f for f in os.listdir(INBOX) if f.endswith('Supplementals.md') or f == 'UC PIQs.md'}
for page, fn in SCHOOL_FILES.items():
    t = open(os.path.join(INBOX, fn)).read()
    t = t.split('## Art Statement')[0]  # Stanford page holds a draft below this
    m = re.search(r'WHERE school = "([^"]+)"', t)
    school = m.group(1) if m else page.replace(' Supplementals', '')
    rows = [c for c in cards if c['school'] == school]
    table = '| Essay | Type | Word limit | Stage |\n|---|---|---|---|\n' + ''.join(
        f'| [[{c["name"]}]] | {c["etype"] or "—"} | {c["limit"]} | {c["stage"]} |\n' for c in rows)
    t = re.sub(r'```dataview.*?```', table, t, flags=re.S)
    t = t.replace('#essays', '').strip() + '\n'
    target = 'Schools/' + (page if page != 'UC PIQs' else 'UC PIQs')
    open(os.path.join(OUT, target + '.md'), 'w').write(t)
    included.add(page)
# card table links point at "<School> Supplementals"; make UC + Cornell resolve
open(os.path.join(OUT, 'Schools/UC Supplementals.md'), 'w').write(
    '---\ntitle: UC Supplementals\n---\nSee [[UC PIQs]].\n')
included.add('UC Supplementals')

for c in cards:
    open(os.path.join(OUT, 'Essay Cards', c['name'] + '.md'), 'w').write(c['body'])

# --- hub ---
hub = open(os.path.join(PROJ, 'Essay Hub.md')).read().replace('#essays\n', '')
master = '| School | Essay (action item) | Word limit | Stage | Complete? | Completion date |\n|---|---|---|---|---|---|\n' + ''.join(
    f'| {c["school"]} | [[{c["name"]}]] | {c["limit"]} | {c["stage"]} | {"✅" if c["complete"] else "⬜"} | '
    f'{short(c["cdate"])} {"" if c["complete"] else "(proj.)"} |\n'
    for c in sorted(cards, key=lambda c: (c['school'], c['name'])))
hub = re.sub(r'```dataview.*?```', master, hub, flags=re.S)
hub = hub.replace('# Essay Hub\n', '')
dash = ['| School | Deadline | Common App school? / done? | Essays done | Complete? | Completion date | Days worked on |',
        '|---|---|---|---|---|---|---|']
sd = lambda x: D(x).strftime('%b %-d')
for k, (plan_, dl_, is_ca, sdate, comp) in sorted(SCHOOLS.items(), key=lambda kv: (kv[1][1], kv[0])):
    mine = [c for c in cards if key(c['school']) == k]
    n_done = sum(c['complete'] for c in mine)
    page = 'UC PIQs' if k == 'UC' else f'{k} Supplementals'
    dash.append(f'| [[{page}\\|{k}]] | {sd(dl_)} ({plan_}) | {"Yes / ✅ done" if is_ca else "No (own app)"} | '
                f'{n_done}/{len(mine)} | {"✅ Yes" if comp else "⬜ No"} | {sd(sdate)} {"✅" if comp else "(projected)"} | {days_worked(k)} |')
dash = ('## Application Dashboard\n\nOne row per school (each school is a project). Common App submitted ' + fmt(COMMON_APP_DONE) +
        ' with my early apps, so every Common App school only has supplementals left. Dates worked come from the [[College Essays Work Log]].\n\n' + '\n'.join(dash) + '\n\n')
hub = '---\ntitle: Essay Hub\n---\n' + dash + hub.strip() + '\n'


# --- kanban -> readable board ---
k = re.sub(r'(?s)^---.*?---\n', '', kanban)
k = re.sub(r'(?s)%% kanban:settings.*?%%', '', k)
k = re.sub(r' #essays/\S+', '', k)
counts = []
for h, t in sections(k)[1:]:
    n = len(re.findall(r'\[\[', t))
    if h != 'Key Dates':
        counts.append(f'| {h} | {n} |')
summary = '| Column | Essays |\n|---|---|\n' + '\n'.join(counts) + '\n\n'
k = '---\ntitle: College Essays Kanban\n---\n' + \
    '> [!info] Read-only view of my Obsidian kanban board. Each column is a stage; each card links to the essay page.\n\n' + \
    summary + k.strip() + '\n'
k = re.sub(r'(?m)^## (Brainstorming|Final Review)\n\s*\n(?=## )', r'## \1\n\n*(empty)*\n\n', k)

# --- other notes ---
misc = {}
for f in ['Essay Themes', 'Ps Feedback']:
    t = open(os.path.join(INBOX, f + '.md')).read().replace('#essays', '').strip()
    if f == 'Essay Themes':
        t = '\n'.join(l for l in t.splitlines() if not l.startswith('Something about'))
    misc[f] = t
    included.add(f)

included |= {'Essay Hub', 'College Essays Kanban', 'College Essays Work Log'}
def page_of(k):
    return 'Common App' if k == 'Common App' else f"[[{'UC PIQs' if k == 'UC' else k + ' Supplementals'}\\|{k}]]"
wl = ['---\ntitle: College Essays Work Log\n---\n',
      'One line per work session. **Done** = sessions I actually worked; **Planned** = my schedule to finish every essay by Dec 20. Planned rows move up to Done as I go.\n',
      '## Done\n', '| Date | Schools | What I did |\n|---|---|---|']
wl += [f'| {fmt(d)} | {", ".join(page_of(x) for x in ss)} | {w} |' for d, ss, w in DONE]
wl += ['\n## Planned\n', '| Date | Schools | Plan |\n|---|---|---|']
wl += [f'| {fmt(d)} | {", ".join(page_of(x) for x in ss)} | {w} |' for d, ss, w in PLAN]
misc['College Essays Work Log'] = '\n'.join(wl[1:])

def unlink_missing(t):
    def rep(m):
        target, alias = m.group(1), m.group(2)
        base = target.split('#')[0].rstrip('\\')
        if base in included or base.startswith(('UC PIQ', 'Common App —')):
            return m.group(0)
        return f'{alias or base} *(private)*'
    return re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', rep, t)

open(os.path.join(OUT, 'Essay Hub.md'), 'w').write(unlink_missing(hub))
open(os.path.join(OUT, 'College Essays Kanban.md'), 'w').write(unlink_missing(k))
for f, t in misc.items():
    open(os.path.join(OUT, f + '.md'), 'w').write(f'---\ntitle: {f}\n---\n' + unlink_missing(t) + '\n')
for root, _, files in os.walk(OUT):
    for f in files:
        p = os.path.join(root, f)
        txt = open(p).read()
        open(p, 'w').write(unlink_missing(txt))

done = sum(1 for c in cards if c['stage'] == 'Submitted')
today = dt.date.today().strftime('%b %-d, %Y')
open(os.path.join(OUT, 'index.md'), 'w').write(f'''---
title: Anders's College Essays — GTD Dashboard
---
A read-only view of the Obsidian system I use to run my college applications.

- **[[Essay Hub]]**: application dashboard (deadline, Common App status, completion per school) + every essay\n- **[[College Essays Work Log]]**: days worked and the plan through Dec 20
- **[[College Essays Kanban]]**: the board: each essay moves Not Started → Drafting → Revising → Final Review → Submitted

**{done} of {len(cards)}** essay cards submitted · last updated {today}

> [!note] Drafts are kept private. Essay pages show the prompt, word limit, status, dates and feedback only.
''')
print(len(cards), 'cards;', len(SCHOOL_FILES), 'school pages')
