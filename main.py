from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP(name="ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            note TEXT DEFAULT ''      
            )
        """)

init_db()

@mcp.tool
def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to the database"""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )

        return {"status": "ok", "id": cur.lastrowid}
    

# adding more tools
@mcp.tool
def edit_expense(id, date, amount, category, subcategory, note):
    """Edit previous expense entries of the database"""
    fields = []
    values = []

    if date is not None:
        fields.append("date = ?")
        values.append(date)
    
    if amount is not None:
        fields.append("amount = ?")
        values.append(amount)

    if category is not None:
        fields.append("category = ?")
        values.append(category)

    if subcategory is not None:
        fields.append("subcategory = ?")
        values.append(subcategory)

    if note is not None:
        fields.append("note = ?")
        values.append(note)

    if not fields:
        return {"error": "No fields provided to update"}

    query = f"""
        UPDATE expenses
        SET {", ".join(fields)}
        WHERE id = ?
    """

    values.append(id)

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, values)
        if cur.rowcount == 0:
            return {"error": "Expenses not found"}
        
        return {"success": True}


@mcp.tool
def delete_expenses(expense_ids: list[int]):
    """Delete expense entries from the database"""

    if not expense_ids:
        return {"error": "No expense Ids provided"}
    
    placeholder = ", ".join(["?"] * len(expense_ids))
    
    query = f"""
        DELETE FROM expenses
        WHERE id IN ({placeholder})
    """

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, expense_ids)

        if cur.rowcount == 0:
            return {"error": "No matching expenses found"}

        return {"success": True, "deleted_count": cur.rowcount}

    
@mcp.tool
def list_expenses(start_date, end_date):
    """List all expense entries from the database"""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "SELECT id, date, amount, category, subcategory, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY id ASC",
            (start_date, end_date)
        )

        cols = [d[0] for d in cur.description]
        # cols = ['date', 'amount', 'category', 'subcategory', 'note']
        # {
        #     'date': '2026-01-01',
        #     'amount': 500,
        #     'category': 'Food',
        #     'subcategory': 'Lunch',
        #     'note': 'Biriyani'
        # }
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    
@mcp.tool
def summary(start_date, end_date, category=None):
    """Summarize expenses by category within an inclusive data range"""
    query = (
        """
        SELECT category, SUM(amount) AS total_amount FROM expenses
        WHERE date BETWEEN ? AND ?
        """
    )
    params = [start_date, end_date]

    if category is not None:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY category ORDER BY category ASC"

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()
    

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=5000)
