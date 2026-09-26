with open("backend/tests/test_phase_4a_impact.py", "r") as f:
    content = f.read()

content = content.replace("from sqlalchemy import select", "from sqlalchemy import select, text")
content = content.replace("db = db_session\n    from app.models.communication", "db = db_session\n    await db.execute(text('DELETE FROM impact_decision_history'))\n    await db.execute(text('DELETE FROM production_order_impacts'))\n    await db.commit()\n    from app.models.communication")

with open("backend/tests/test_phase_4a_impact.py", "w") as f:
    f.write(content)
