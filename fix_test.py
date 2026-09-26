with open("backend/tests/test_phase_3g_verification.py", "r") as f:
    c = f.read()
c = c.replace("is_active=True,", "is_active=True, role=\"ADMIN\",")
with open("backend/tests/test_phase_3g_verification.py", "w") as f:
    f.write(c)
