#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    if 'test' not in sys.argv:
        print 'this is here only for testing'
        sys.exit(1)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test.test_settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
