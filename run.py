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
        scraper.step1_fetch_all()
        git_commit("step1: fetched all partners and categories via API")

    elif step == "2":
        scraper.step2_fetch_news()
        git_commit("step2: fetched all news/events")

    elif step == "3":
        scraper.step3_export_family()
        git_commit("step3: family partners filtered and exported")

    elif step == "done":
        db.log("run", "All steps complete.")
        db.log("run", "Results: data/processed/family_partners.json")

    # Print DB summary
    with db.connect() as conn:
        n_cat      = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        n_partners = conn.execute("SELECT COUNT(*) FROM partners").fetchone()[0]
        n_news     = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    db.log("run", f"DB — categories:{n_cat} partners:{n_partners} news:{n_news}")


if __name__ == "__main__":
    main()
