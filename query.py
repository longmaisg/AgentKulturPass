# query.py — explore the KulturPass database
# Run: uv run python query.py
# Edit the QUERY variable at the bottom to try different queries.

import sqlite3

DB = "data/kulturpass.db"

def run(sql: str, title: str = "") -> None:
    """Run a SQL query and print results in a readable table."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql).fetchall()
    conn.close()

    if title:
        print(f"\n{'─'*60}")
        print(f"  {title}")
        print(f"{'─'*60}")

    if not rows:
        print("  (no results)")
        return

    # Print column names
    cols = rows[0].keys()
    col_w = {c: max(len(c), max(len(str(r[c] or "")) for r in rows)) for c in cols}
    col_w = {c: min(w, 40) for c, w in col_w.items()}  # cap width at 40

    header = "  " + "  ".join(c.ljust(col_w[c]) for c in cols)
    print(header)
    print("  " + "  ".join("-" * col_w[c] for c in cols))

    for row in rows:
        line = "  " + "  ".join(str(row[c] or "")[:col_w[c]].ljust(col_w[c]) for c in cols)
        print(line)

    print(f"\n  → {len(rows)} row(s)")


# ── QUERIES — uncomment one block at a time and run ──────────────────────────

# 1. How many rows are in each table?
run("SELECT 'categories' as table_name, COUNT(*) as total FROM categories UNION ALL "
    "SELECT 'partners',                  COUNT(*)          FROM partners  UNION ALL "
    "SELECT 'news',                      COUNT(*)          FROM news      UNION ALL "
    "SELECT 'logs',                      COUNT(*)          FROM logs",
    "ROW COUNTS PER TABLE")

# 2. All 9 categories with partner counts
run("SELECT id, name, count FROM categories ORDER BY count DESC",
    "ALL CATEGORIES")

# 3. Top 10 family-friendly partners (★ = Young Audiences category)
run("""
    SELECT
        p.name,
        p.family_score,
        CASE WHEN p.category_ids LIKE '%9%' THEN 'YES' ELSE '' END AS young_audiences,
        p.link
    FROM partners p
    WHERE p.family_score > 0
    ORDER BY young_audiences DESC, p.family_score DESC
    LIMIT 10
""", "TOP 10 FAMILY PARTNERS")

# 4. Count partners per category
run("""
    SELECT c.name, COUNT(p.wp_id) as total
    FROM categories c
    JOIN partners p ON p.category_ids LIKE '%' || c.id || '%'
    GROUP BY c.name
    ORDER BY total DESC
""", "PARTNERS PER CATEGORY")

# 5. Latest log entries
run("SELECT step, message, created_at FROM logs ORDER BY id DESC LIMIT 10",
    "LATEST LOGS")

# 6. All news titles
run("SELECT title, date FROM news ORDER BY date DESC",
    "ALL NEWS ITEMS")

# ── TRY YOUR OWN ─────────────────────────────────────────────────────────────
# Uncomment and edit:
#
# run("SELECT name, link FROM partners WHERE name LIKE '%music%'",
#     "SEARCH: music in name")
#
# run("SELECT * FROM partners WHERE family_score >= 6",
#     "HIGH FAMILY SCORE (6+)")
#
# run("SELECT * FROM progress",
#     "PROGRESS TABLE")
