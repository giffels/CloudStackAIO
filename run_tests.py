#!/usr/bin/env python3.6
import fnmatch
import os
import unittest


def get_test_names(search_path, search_pattern, base_dir):
    excluded_files = []
    module_names = []

    for root, dirs, files in os.walk(search_path):
        for test_file in files:
            if fnmatch.fnmatch(test_file, search_pattern) and files not in excluded_files:
                filename = os.path.join(root, test_file)
                # Figure out the module name
                module_name = os.path.relpath(filename, base_dir).split('/')
                del module_name[-1]  # remove filename from list
                module_name.append(os.path.splitext(test_file)[0])  # add class name
                module_names.append('.'.join(module_name))

    return module_names


def create_test_suite(search_path, search_pattern, base_dir, reverse_order=True):
    test_suite = unittest.TestSuite()
    module_names = get_test_names(search_path, search_pattern, base_dir)
    loaded_tests = unittest.TestLoader().loadTestsFromNames(sorted(module_names, reverse=reverse_order))
    test_suite.addTests(loaded_tests)

    return test_suite


def main():
    base_dir = os.path.dirname(os.path.realpath(__file__))
    test_dir = os.path.join(base_dir, 'tests')

    test_suite = unittest.TestSuite()
    test_suite.addTests(create_test_suite(test_dir, '*_t.py', base_dir))

    unittest.TextTestRunner(verbosity=2).run(test_suite)


if __name__ == '__main__':
    main()
