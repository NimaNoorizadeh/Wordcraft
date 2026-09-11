import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import default_database_path


class AppPathTests(unittest.TestCase):
    def test_default_database_uses_current_users_local_app_data(self):
        with patch.dict(os.environ, {'LOCALAPPDATA': r'C:\Users\Example\AppData\Local'}, clear=True):
            self.assertEqual(
                default_database_path(),
                Path(r'C:\Users\Example\AppData\Local\Wordcraft\vocabulary.db'),
            )

    def test_database_directory_can_be_overridden(self):
        with patch.dict(os.environ, {'WORDCRAFT_DATA_DIR': r'E:\My Wordcraft Data'}, clear=True):
            self.assertEqual(
                default_database_path(),
                Path(r'E:\My Wordcraft Data\vocabulary.db'),
            )


if __name__ == '__main__':
    unittest.main()
