"""The isolated demo export: only UI and edition JSON, bound to localhost only."""
import unittest

from tests.fixtures import temporary_directory
from tools import export_demo


class ExportDemoTests(unittest.TestCase):
    def test_export_writes_only_site_and_data_files(self):
        with temporary_directory() as workspace:
            result = export_demo.export(workspace / "export")
            export_dir = workspace / "export"
            self.assertTrue((export_dir / "index.html").exists())
            self.assertTrue((export_dir / "app.js").exists())
            self.assertTrue((export_dir / "data" / "index.json").exists())
            self.assertGreater(result["data_files"], 0)

    def test_serve_command_binds_127_0_0_1_only(self):
        with temporary_directory() as workspace:
            result = export_demo.export(workspace / "export")
            self.assertIn("127.0.0.1", result["serve_command"])
            self.assertNotIn("0.0.0.0", result["serve_command"])

    def test_export_carries_no_evaluator_or_git_content(self):
        with temporary_directory() as workspace:
            export_demo.export(workspace / "export")
            export_dir = workspace / "export"
            names = {p.name for p in export_dir.rglob("*")}
            self.assertNotIn(".git", names)
            for path in export_dir.rglob("*"):
                if path.is_dir():
                    continue
                self.assertNotEqual(path.suffix, ".csv")  # labels/registries are never exported
            self.assertFalse((export_dir / "runtime_state.json").exists())


if __name__ == "__main__":
    unittest.main()
