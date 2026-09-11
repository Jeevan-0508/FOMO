#!/usr/bin/env python3
"""Inspect the deployed page and report what a picky visitor would notice.

Checks the live URL, not the working copy, because a page that only passes
locally has not been tested. Reports; it never edits anything. Findings are
written to findings.md for the workflow to raise as a single issue.
"""
import io, json, os, re, sys, urllib.error, urllib.request

SITE = os.environ.get('SITE', 'https://jeevan-0508.github.io/FOMO/')
API = 'https://api.github.com'
IMAGE_BUDGET = 150_000      # bytes, per image
PAGE_BUDGET = 500_000       # bytes, everything the page pulls
findings = []


def note(severity, check, detail):
    findings.append({'severity': severity, 'check': check, 'detail': detail})


def fetch(url, method='GET'):
    req = urllib.request.Request(url, method=method, headers={
        'User-Agent': 'jeevan-0508-repo-inspector',
        'Accept': '*/*',
    })
    token = os.environ.get('GITHUB_TOKEN')
    if token and url.startswith(API):
        req.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read(), dict(r.headers)


def status_of(url):
    for method in ('HEAD', 'GET'):
        try:
            return fetch(url, method)[0]
        except urllib.error.HTTPError as e:
            if e.code in (403, 405) and method == 'HEAD':
                continue                       # some hosts refuse HEAD
            return e.code
        except Exception as e:
            return str(e)
    return 'unreachable'


def main():
    try:
        status, body, _ = fetch(SITE)
    except Exception as e:
        note('blocker', 'site reachable', '%s did not respond: %s' % (SITE, e))
        return report()
    if status != 200:
        note('blocker', 'site reachable', '%s returned HTTP %s' % (SITE, status))
        return report()
    html = body.decode('utf-8', 'replace')
    total = len(body)

    # --- structure a visitor and a crawler both depend on ---
    if not re.search(r'<h1[ >]', html):
        note('major', 'has a heading', 'the page has no <h1> element')
    if not re.search(r'<meta name="description" content="[^"]{50,}"', html):
        note('major', 'meta description', 'missing, or shorter than 50 characters')
    for img in re.findall(r'<img [^>]*>', html):
        if 'alt=' not in img:
            note('major', 'image alt text', 'no alt attribute: %s' % img[:70])
    # Checked against visible markup only: a <script> tag routinely embeds
    # JSON/JS with words like TODO or "coming soon" as real data, not a
    # leftover placeholder, and an <input placeholder="..."> attribute is a
    # normal form field, not unfinished prose.
    visible = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    visible = re.sub(r'<style\b[^>]*>.*?</style>', '', visible, flags=re.DOTALL | re.IGNORECASE)
    visible = re.sub(r'''placeholder\s*=\s*("[^"]*"|'[^']*')''', '', visible, flags=re.IGNORECASE)
    for word in ('TODO', 'lorem ipsum', 'coming soon', 'placeholder'):
        if word.lower() in visible.lower():
            note('major', 'no placeholder text', 'the page contains %r' % word)

    # --- weight ---
    assets = set(re.findall(r'(?:href|src)="([^"]+\.(?:css|js|png|jpg|jpeg|svg|webp))"', html))
    for rel in sorted(assets):
        url = rel if rel.startswith('http') else SITE.rsplit('/', 1)[0] + '/' + rel.lstrip('/')
        try:
            _, blob, _ = fetch(url)
        except Exception as e:
            note('major', 'asset loads', '%s failed: %s' % (rel, e))
            continue
        total += len(blob)
        if rel.endswith(('.png', '.jpg', '.jpeg', '.webp')) and len(blob) > IMAGE_BUDGET:
            note('minor', 'image weight', '%s is %d KB (budget %d KB)'
                 % (rel, len(blob) // 1000, IMAGE_BUDGET // 1000))
    if total > PAGE_BUDGET:
        note('minor', 'page weight', 'the page pulls %d KB (budget %d KB)'
             % (total // 1000, PAGE_BUDGET // 1000))

    # --- link rot ---
    for url in sorted(set(re.findall(r'href="(https?://[^"]+)"', html))):
        if 'news.google.com' in url:
            continue                            # syndicated redirectors, expected to churn
        if 'linkedin.com' in url:
            continue                            # LinkedIn answers bots with 999, never 200
        if 'eur-lex.europa.eu' in url:
            continue                            # EUR-Lex answers bots with 202, never 200
        code = status_of(url)
        if code != 200:
            note('major', 'link resolves', '%s -> %s' % (url, code))

    # --- the repositories the page links back to ---
    for repo in sorted(set(re.findall(r'https://github\.com/Jeevan-0508/([A-Za-z0-9._-]+)', html))):
        full = 'Jeevan-0508/' + repo
        try:
            meta = json.loads(fetch('%s/repos/%s' % (API, full))[1])
        except Exception as e:
            note('major', 'repo reachable', '%s: %s' % (full, e))
            continue
        desc = (meta.get('description') or '').strip()
        if not desc:
            note('major', 'repo description', '%s has no description' % full)
        elif desc.lower() == repo.lower().replace('-', ' ') or desc.lower() == repo.lower():
            note('major', 'repo description',
                 '%s describes itself as %r, which says nothing' % (full, desc))
        try:
            topics = json.loads(fetch('%s/repos/%s/topics' % (API, full))[1]).get('names') or []
        except Exception:
            topics = []
        if len(topics) < 3:
            note('minor', 'repo topics', '%s has %d topics; 3+ makes it findable' % (full, len(topics)))

    return report()


def report():
    order = {'blocker': 0, 'major': 1, 'minor': 2}
    findings.sort(key=lambda f: (order[f['severity']], f['check']))
    lines = ['Inspected %s' % SITE, '']
    if not findings:
        lines.append('No findings. Nothing to approve.')
    else:
        counts = {s: sum(1 for f in findings if f['severity'] == s) for s in order}
        lines.append('**%d findings** — %d blocker, %d major, %d minor.'
                     % (len(findings), counts['blocker'], counts['major'], counts['minor']))
        lines.append('')
        lines.append('| | Check | Detail |')
        lines.append('|---|---|---|')
        for f in findings:
            lines.append('| %s | %s | %s |' % (f['severity'], f['check'], f['detail']))
        lines += ['', 'Nothing has been changed. Each row is a decision for you.']
    text = '\n'.join(lines) + '\n'
    io.open('findings.md', 'w', encoding='utf-8', newline='\n').write(text)
    print(text)
    return 1 if any(f['severity'] == 'blocker' for f in findings) else 0


if __name__ == '__main__':
    sys.exit(main())
