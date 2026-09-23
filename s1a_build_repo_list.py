#!/usr/bin/env python3
"""
Stage 1a - Build a LARGE, DIVERSE candidate repo list.

Why this differs from study 1:
  - Study 1 took ~30 top-starred repos. Popular, well-maintained apps are
    plausibly MORE accessible than average, which biased issue counts down.
  - Here we cast a wider net and deliberately include MID-TIER repos
    (fewer stars, still real apps), where accessibility defects are more common.
  - Two sources: F-Droid (real shipping FOSS Android apps) + GitHub search.

Output: repos_candidates.csv  (full candidate pool - NOT yet filtered)

Usage:
    export GITHUB_TOKEN=ghp_xxx        # needed for GitHub search rate limits
    python3 s1a_build_repo_list.py --target 400
"""
import argparse, csv, os, re, sys, time
import requests

UA = {"User-Agent": "compose-a11y-study"}
GH = "https://api.github.com"


def gh_headers():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    h = dict(UA)
    h["Accept"] = "application/vnd.github+json"
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def fdroid_repos(limit=600):
    """F-Droid index -> source-code URLs. Real shipping FOSS Android apps."""
    out = []
    url = "https://f-droid.org/repo/index-v2.json"
    try:
        r = requests.get(url, headers=UA, timeout=120)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [warn] F-Droid fetch failed ({e}); skipping this source.")
        return out
    pkgs = data.get("packages", {})
    for pkg_name, pkg in pkgs.items():
        meta = pkg.get("metadata", {})
        src = meta.get("sourceCode") or ""
        lic = (meta.get("license") or "").strip()
        if not src:
            continue
        m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", src)
        if not m:
            continue
        owner, name = m.group(1), m.group(2).replace(".git", "")
        out.append({
            "full_name": f"{owner}/{name}",
            "source": "fdroid",
            "fdroid_pkg": pkg_name,
            "license_hint": lic,
        })
        if len(out) >= limit:
            break
    print(f"  F-Droid: {len(out)} repos with GitHub source URLs")
    return out


def github_search(target=400):
    """
    GitHub repo search across STAR BANDS so we don't only get famous apps.
    Mid/low bands are where accessibility defects actually live.
    """
    bands = [
        ("stars:>2000", 60),
        ("stars:500..2000", 90),
        ("stars:100..500", 120),
        ("stars:30..100", 130),   # mid-tier: most valuable for finding real issues
    ]
    queries = [
        "jetpack compose android app language:kotlin",
        "compose material3 android language:kotlin",
    ]
    seen, out = set(), []
    for band, want in bands:
        got = 0
        for q in queries:
            page = 1
            while got < want and page <= 10:
                params = {"q": f"{q} {band}", "sort": "updated",
                          "order": "desc", "per_page": 100, "page": page}
                try:
                    r = requests.get(f"{GH}/search/repositories",
                                     headers=gh_headers(), params=params, timeout=60)
                    if r.status_code == 403:
                        print("  [rate limit] sleeping 60s...")
                        time.sleep(60)
                        continue
                    r.raise_for_status()
                    items = r.json().get("items", [])
                except Exception as e:
                    print(f"  [warn] search failed: {e}")
                    break
                if not items:
                    break
                for it in items:
                    fn = it["full_name"]
                    if fn in seen:
                        continue
                    seen.add(fn)
                    out.append({
                        "full_name": fn,
                        "source": f"github:{band}",
                        "stars": it.get("stargazers_count", 0),
                        "license_hint": ((it.get("license") or {}).get("spdx_id") or ""),
                        "pushed_at": it.get("pushed_at", ""),
                        "archived": it.get("archived", False),
                    })
                    got += 1
                    if got >= want:
                        break
                page += 1
                time.sleep(1.5)
        print(f"  GitHub {band}: {got} repos")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=400,
                    help="rough GitHub target before dedup/filtering")
    ap.add_argument("--out", default="repos_candidates.csv")
    ap.add_argument("--skip-fdroid", action="store_true")
    args = ap.parse_args()

    if not os.environ.get("GITHUB_TOKEN"):
        print("[!] No GITHUB_TOKEN set. Search will be heavily rate-limited.")
        print("    Create one at github.com/settings/tokens (public_repo scope).\n")

    rows = []
    if not args.skip_fdroid:
        print("Source 1: F-Droid")
        rows += fdroid_repos()
    print("Source 2: GitHub search (star bands)")
    rows += github_search(args.target)

    # dedup by full_name, keep first occurrence
    seen, dedup = set(), []
    for r in rows:
        fn = r["full_name"].lower()
        if fn in seen:
            continue
        seen.add(fn)
        dedup.append(r)

    cols = ["full_name", "source", "stars", "license_hint", "pushed_at",
            "archived", "fdroid_pkg"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in dedup:
            w.writerow(r)

    print(f"\nCandidate pool: {len(dedup)} unique repos -> {args.out}")
    print("Next: python3 s1b_filter_and_fetch.py")


if __name__ == "__main__":
    main()
