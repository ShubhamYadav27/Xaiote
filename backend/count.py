import os
import ast

def count_tests(prefix):
    count = 0
    for file in os.listdir('tests'):
        if file.startswith(prefix) and file.endswith('.py'):
            with open(os.path.join('tests', file), 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        count += 1
    return count

print("3f", count_tests('test_phase_3f'))
print("3g", count_tests('test_phase_3g'))
print("4a", count_tests('test_phase_4a'))
print("4b", count_tests('test_phase_4b'))
print("4c", count_tests('test_phase_4c'))
print("4d", count_tests('test_phase_4d'))
print("4e.1", count_tests('test_phase_4e_1'))
print("4e.2", count_tests('test_phase_4e_2'))
print("4e.3", count_tests('test_phase_4e_3'))
