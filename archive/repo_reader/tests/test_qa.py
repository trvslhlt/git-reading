import unittest
from pathlib import Path
from datetime import datetime

from repo_reader.models import CommitChange, CommitInfo, FileSnapshot, RepositorySnapshot
from repo_reader.qa import RepositoryIndex


class RepositoryIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        file_snapshot = FileSnapshot(path=Path("src/main.py"), content="def add(a, b):\n    return a + b\n")
        commit = CommitInfo(
            sha="abc123",
            author_name="Test User",
            author_email="test@example.com",
            authored_at=datetime.now(),
            summary="Add simple add helper",
            changes=[
                CommitChange(
                    file_path=Path("src/main.py"),
                    patch="@@ -0,0 +1,2 @@\n+def add(a, b):\n+    return a + b",
                )
            ],
        )
        snapshot = RepositorySnapshot(root=Path("."), files=[file_snapshot], commits=[commit])
        self.index = RepositoryIndex(snapshot)

    def test_keyword_search(self) -> None:
        answers = self.index.query("How do we add numbers?", limit=3)
        self.assertTrue(answers)
        self.assertIn("src/main.py", answers[0].location)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
