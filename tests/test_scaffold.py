import unittest

import local_agent_memory


class ScaffoldTests(unittest.TestCase):
    def test_version_is_declared(self) -> None:
        self.assertRegex(local_agent_memory.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
