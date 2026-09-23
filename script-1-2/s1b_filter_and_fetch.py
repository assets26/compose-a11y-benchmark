#!/usr/bin/env python3
"""
Stage 1b - Filter the candidate pool and download Compose source.

Filters (all recorded, so the paper can state them exactly):
  1. Permissive license (MIT / Apache-2.0 / BSD) -> redistributable
  2. Not archived, pushed within --max-age-days -> actually maintained
  3. Genuinely uses Compose: repo must contain @Composable in Kotlin files
  4. Has a minimum number of composable-bearing files

Writes:
  mined_code/<owner>__<repo>/<path>.kt       (downloaded UI Kotlin files)
  repos_manifest.csv                         (PROVENANCE - cite this in the paper)
  stage1_report.txt                          (funnel counts for the Method section)

Usage:
    export GITHUB_TOKEN=ghp_xxx
    python3 s1b_filter_and_fetch.py --limit 200
"""
import argparse, base64, csv, os, sys, time
from pathlib import Path
import requests

GH = "https://api.github.com"
PERMISSIVE = {"MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "ISC"}


def gh_headers():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    h = {"User-Agent": "compose-a11y-study", "Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def api(path, params=None, retries=3):
    for i in range(retries):
        try:
            r = requests.get(f"{GH}{path}", headers=gh_headers(),
                             params=params, timeout=60)
            if r.status_code == 403 and "rate limit" in r.text.lower():
                print("   [rate limit] sleeping 60s")
                time.sleep(60)
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(3)
    return None


def repo_meta(full_name):
    return api(f"/repos/{full_name}")


def find_compose_files(full_name, default_branch, max_files=40):
    """List Kotlin files via the git tree, then keep ones containing @Composable."""
    tree = api(f"/repos/{full_name}/git/trees/{default_branch}",
               params={"recursive": "1"})
    if not tree or "tree" not in tree:
        return []
    kt = [t for t in tree["tree"]
          if t["type"] == "blob"
          and t["path"].endswith(".kt")
          and t.get("size", 0) < 200_000]
    # Prefer UI-ish paths first - that's where composables live
    def score(p):
        s = 0
        low = p.lower()
        for kw in ("ui/", "screen", "component", "compose", "view", "widget"):
            if kw in low:
                s -= 1
        return s
    kt.sort(key=lambda t: score(t["path"]))
    return kt[:max_files * 3]


def fetch_file(full_name, path):
    j = api(f"/repos/{full_name}/contents/{path}")
    if not j or j.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(j["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="repos_candidates.csv")
    ap.add_argument("--outdir", default="mined_code")
    ap.add_argument("--limit", type=int, default=200,
                    help="how many repos to ACCEPT (study 1 used 30)")
    ap.add_argument("--max-age-days", type=int, default=900)
    ap.add_argument("--min-compose-files", type=int, default=3)
    ap.add_argument("--max-files-per-repo", type=int, default=25)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.candidates, encoding="utf-8")))
    print(f"Candidate pool: {len(rows)} repos")

    outdir = Path(args.outdir); outdir.mkdir(exist_ok=True)
    manifest, funnel = [], {
        "candidates": len(rows), "meta_ok": 0, "license_ok": 0,
        "maintained_ok": 0, "compose_ok": 0, "accepted": 0, "files": 0,
    }

    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    accepted = 0

    for i, row in enumerate(rows, 1):
        if accepted >= args.limit:
            break
        fn = row["full_name"]
        if i % 25 == 0:
            print(f"  [{i}/{len(rows)}] accepted={accepted}")

        meta = repo_meta(fn)
        if not meta:
            continue
        funnel["meta_ok"] += 1

        spdx = ((meta.get("license") or {}).get("spdx_id") or "").upper()
        if spdx not in PERMISSIVE:
            continue
        funnel["license_ok"] += 1

        if meta.get("archived"):
            continue
        pushed = meta.get("pushed_at", "")
        try:
            age = (now - dt.datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days
        except Exception:
            age = 99999
        if age > args.max_age_days:
            continue
        funnel["maintained_ok"] += 1

        branch = meta.get("default_branch", "main")
        cands = find_compose_files(fn, branch, args.max_files_per_repo)
        if not cands:
            continue

        saved, kept_paths = 0, []
        for t in cands:
            if saved >= args.max_files_per_repo:
                break
            txt = fetch_file(fn, t["path"])
            if not txt or "@Composable" not in txt:
                continue
            dest = outdir / fn.replace("/", "__") / t["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(txt, encoding="utf-8")
            kept_paths.append(t["path"])
            saved += 1
            time.sleep(0.2)

        if saved < args.min_compose_files:
            continue
        funnel["compose_ok"] += 1

        accepted += 1
        funnel["accepted"] = accepted
        funnel["files"] += saved
        manifest.append({
            "full_name": fn,
            "source": row.get("source", ""),
            "stars": meta.get("stargazers_count", 0),
            "license": spdx,
            "default_branch": branch,
            "pushed_at": pushed,
            "days_since_push": age,
            "compose_files_saved": saved,
            "url": meta.get("html_url", ""),
            "accessed": now.date().isoformat(),
        })

    with open("repos_manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()) if manifest else
                           ["full_name"], extrasaction="ignore")
        w.writeheader(); w.writerows(manifest)

    report = [
        "STAGE 1 FUNNEL (numbers for the Method section)",
        "=" * 48,
        f"Candidate repos considered      : {funnel['candidates']}",
        f"  metadata retrieved            : {funnel['meta_ok']}",
        f"  permissive license            : {funnel['license_ok']}",
        f"  maintained (<= {args.max_age_days}d, not archived): {funnel['maintained_ok']}",
        f"  >= {args.min_compose_files} files containing @Composable : {funnel['compose_ok']}",
        f"ACCEPTED REPOS                  : {funnel['accepted']}",
        f"Compose files downloaded        : {funnel['files']}",
        "",
        "Star distribution of accepted repos:",
    ]
    if manifest:
        st = sorted(int(m["stars"]) for m in manifest)
        report += [
            f"  min={st[0]}  median={st[len(st)//2]}  max={st[-1]}",
            f"  under 100 stars: {sum(1 for s in st if s < 100)} "
            f"({100*sum(1 for s in st if s<100)//len(st)}%)  <- mid-tier coverage",
        ]
    Path("stage1_report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print("\nNext: python3 s2_prescreen_yield.py")


if __name__ == "__main__":
    main()
