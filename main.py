from fastmcp import FastMCP
import os
# import sqlite3 => not asynchronous

import aiosqlite
import tempfile

# making writable using claude-desktop
TEMP_DIR=tempfile.gettempdir()

DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP(name="ExpenseTracker")

def init_db():
    try:
        import sqlite3
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")
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
    except Exception as e:
        print(f"Database initialization error: {e}")

init_db()

@mcp.tool
async def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry to the database"""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )

            expense_id=cur.lastrowid
            await c.commit()
            return {"status": "success", "id": expense_id, "message": "Expense added successfully"}
    
    except Exception as e:
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode. Check file-permissions"}
        
        return {"status":"error", "message": f"Database error: {str(e)}"}
    

# adding more tools
@mcp.tool
async def edit_expense(id, date, amount, category, subcategory, note):
    """Edit previous expense entries of the database"""
    
    try:
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

        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(query, values)
            await c.commit()
            if cur.rowcount == 0:
                return {"error": "Expenses not found"}

            return {"status": "success", "message": "Edited successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Error editing expenses: {str(e)}"}


@mcp.tool
async def delete_expenses(expense_ids: list[int]):
    """Delete expense entries from the database"""

    try:
        if not expense_ids:
            return {"error": "No expense Ids provided"}
    
        placeholder = ", ".join(["?"] * len(expense_ids))

        query = f"""
            DELETE FROM expenses
            WHERE id IN ({placeholder})
        """

        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(query, expense_ids)
            await c.commit()
            if cur.rowcount == 0:
                return {"error": "No matching expenses found"}

            return {"status": "success", "deleted_count": cur.rowcount}
        
    except Exception as e:
        return {"status": "error", "message": f"Error deleting expenses: {str(e)}"}

    
@mcp.tool
async def list_expenses(start_date, end_date):
    """List all expense entries from the database"""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "SELECT id, date, amount, category, subcategory, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY id ASC",
                (start_date, end_date)
            )

            cols = [d[0] for d in cur.description]
            rows=await cur.fetchall()
            return [dict(zip(cols, r)) for r in rows]
            # cols = ['date', 'amount', 'category', 'subcategory', 'note']
            # {
            #     'date': '2026-01-01',
            #     'amount': 500,
            #     'category': 'Food',
            #     'subcategory': 'Lunch',
            #     'note': 'Biriyani'
            # }
    
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}
    
@mcp.tool
async def summary(start_date, end_date, category=None):
    """Summarize expenses by category within an inclusive data range"""
    try:
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

        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(query, params)
            cols = [d[0] for d in cur.description]
            rows=await cur.fetchall()
            return [dict(zip(cols, r)) for r in rows]
        
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}


@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    try:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'
    

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=5000)
