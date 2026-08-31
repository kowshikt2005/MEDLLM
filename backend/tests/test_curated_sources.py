import importlib.util
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_DIR / "scripts" / "build_curated_index.py"


def _load_builder_module():
    spec = importlib.util.spec_from_file_location("build_curated_index", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_main_text_omits_navigation_and_normalizes_whitespace():
    builder = _load_builder_module()

    html = """
    <html><body>
      <nav>Navigation text</nav>
      <main><h1>Diabetes Basics</h1><p>First paragraph.</p><p>Second paragraph.</p></main>
      <footer>Footer text</footer>
    </body></html>
    """

    assert builder.extract_main_text(html) == "Diabetes Basics\n\nFirst paragraph.\n\nSecond paragraph."


def test_manifest_declares_three_attributed_cdc_sources():
    builder = _load_builder_module()

    sources = builder.load_manifest(BACKEND_DIR / "data" / "curated_sources" / "manifest.json")

    assert [source["source_id"] for source in sources] == [
        "cdc-diabetes-basics",
        "cdc-diabetes-symptoms",
        "cdc-high-blood-pressure-basics",
    ]
    assert all(source["publisher"] == "Centers for Disease Control and Prevention" for source in sources)
    assert all(source["url"].startswith("https://www.cdc.gov/") for source in sources)

def test_cdc_request_uses_browser_compatible_accept_headers():
    builder = _load_builder_module()

    request = builder.build_source_request("https://www.cdc.gov/diabetes/about/")

    assert request.headers["User-agent"].startswith("Mozilla/")
    assert "text/html" in request.headers["Accept"]