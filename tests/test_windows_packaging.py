"""Check the release-critical dependency traversal without needing Windows."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts/package_windows.py"
spec = importlib.util.spec_from_file_location("package_windows", MODULE)
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


class RuntimeDependencyTests(unittest.TestCase):
    def test_transitive_case_insensitive_imports_and_system_exclusions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, system = root / "runtime", root / "system"
            runtime.mkdir()
            system.mkdir()
            exe = root / "powerlaunch.exe"
            exe.touch()
            for filename in ["libraylib.dll", "glfw3.dll", "libwinpthread-1.dll"]:
                (runtime / filename).touch()
            (system / "KERNEL32.dll").touch()
            graph = {
                "powerlaunch.exe": ["LIBRAYLIB.dll", "kernel32.DLL", "api-ms-win-crt-runtime-l1-1-0.dll"],
                "libraylib.dll": ["glfw3.dll", "libwinpthread-1.dll"],
                "glfw3.dll": ["libwinpthread-1.dll"],
                "libwinpthread-1.dll": ["KERNEL32.dll", "libraylib.dll"],
            }
            found = packaging.runtime_dependencies(exe, runtime, system, lambda path: graph[path.name])
            self.assertEqual([path.name for path in found], ["glfw3.dll", "libraylib.dll", "libwinpthread-1.dll"])

    def test_missing_transitive_dependency_fails_instead_of_uploading_broken_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, system = root / "runtime", root / "system"
            runtime.mkdir()
            system.mkdir()
            exe = root / "powerlaunch.exe"
            exe.touch()
            (runtime / "libraylib.dll").touch()
            with self.assertRaisesRegex(RuntimeError, "missing.dll"):
                packaging.runtime_dependencies(exe, runtime, system,
                    lambda path: ["libraylib.dll"] if path == exe else ["missing.dll"])

    def test_parse_pe_import_table(self):
        with patch.object(packaging.subprocess, "check_output", return_value=
            "\tDLL Name: KERNEL32.dll\n\tDLL Name: libraylib.dll\n"):
            self.assertEqual(packaging.imports(Path("game.exe"), Path("objdump")),
                ["KERNEL32.dll", "libraylib.dll"])


if __name__ == "__main__":
    unittest.main()
