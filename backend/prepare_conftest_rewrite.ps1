import codecs
import re

file_path = 'conftest.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

# We can completely remove TestingSessionLocal and override_get_db, but we still need setup_test_db to run create_all and drop_all on the engine from session.py.
# Let's replace the whole conftest.py with a much simpler one.
