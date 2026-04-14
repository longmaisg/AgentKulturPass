# run.py — orchestrator
# Checks current step from DB, runs it, commits to git.
# Safe to run repeatedly — picks up where it left off.

import subprocess
import db
import scraper


def git_commit(msg: str) -> None:
    try:
        subprocess.run(["bash", "scripts/git_push.sh", msg], check=True)
    except Exception as e:
        db.log("git", f"Git push failed: {e}")


def main() -> None:
    db.init_db()
    step = db.get_progress("current_step", default="1")
    db.log("run", f"Resuming at step {step}")

    if step == "1":
        scraper.step1_fetch_index()
        git_commit("step1: fetched partners index")

    elif step == "2":
        done = scraper.step2_fetch_partners()
        git_commit("step2: fetched partner pages batch")
        if not done:
            db.log("run", "More pages to fetch — run again.")

    elif step == "3":
        done = scraper.step3_parse_events()
        git_commit("step3: parsed events batch")
        if not done:
            db.log("run", "More pages to parse — run again.")

    elif step == "4":
        scraper.step4_filter_family()
        git_commit("step4: family events filtered and saved")

    elif step == "done":
        db.log("run", "All steps complete. Check data/processed/family_events.json")

    # Print summary
    with db.connect() as conn:
        n_links  = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        n_pages  = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    db.log("run", f"DB state — links:{n_links} pages:{n_pages} events:{n_events}")


if __name__ == "__main__":
    main()
