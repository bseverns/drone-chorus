# Repository Evaluation: Drone Chorus

Drone Chorus is an innovative project bridging FPV drone telemetry (MSP protocol) to MIDI CCs for live synthesizer modulation (VCV Rack). It serves as both a performance tool and a teaching aid.

While the project is generally well-structured and prioritizes safety, legibility, and reproducibility, there are several areas that could use reinforcement or expansion to better achieve its goals.

## Areas for Reinforcement and Expansion

### 1. Testing and CI/CD Pipeline
- **Missing CI/CD Pipeline:** The repository lacks automated continuous integration (e.g., GitHub Actions). For a project intended for live performance, preventing regressions is paramount. A CI pipeline should automatically run tests, lint code, and build documentation on pull requests.
- **Test Environment & Dependencies:** The repository contains tests (`software/midi-bridge/test_msp_bridge.py`), but running them fails out-of-the-box because test dependencies (like `pytest` and the main requirements like `mido` for the testing environment) are not bundled in a dedicated `requirements-dev.txt` or equivalent.
- **Test Coverage Expansion:** While core logic in `msp_bridge.py` has some coverage, testing should be expanded to cover the CLI parsing logic (`msp_to_midi.py`, `msp_multi_to_midi.py`) and potentially the GUI backend state management (`gui_backend.py`).

### 2. Error Handling and Robustness
- **Silent Failures:** The core threading loops in `msp_multi_to_midi.py` and `BridgeWorker.run` (in `gui_backend.py`) catch exceptions but either swallow them or exit silently. During a live show or rehearsal, silent failures are difficult to diagnose.
- **Logging Infrastructure:** The project relies primarily on standard output (`print` statements) or GUI widget updates. Implementing a centralized, robust `logging` module (writing to the `logs/` directory) would greatly improve post-performance debriefs (as referenced in `docs/LIVE_WORKFLOW.md`).

### 3. Configuration Validation
- **Lack of Schema Validation:** The YAML configuration files (`config/multi.yaml`, `config/mapping.yaml`) govern crucial mapping and smoothing behaviors. Currently, if a user misspells a parameter (e.g., `rolll` instead of `roll`) or provides an invalid type, the system might fail obscurely at runtime. Implementing robust schema validation (e.g., using `jsonschema` or `Cerberus`) upon loading the YAML would provide clear, actionable feedback to the user.

### 4. Code Style, Linting, and Type Hinting
- **Incomplete Type Hints and Pragmas:** The codebase uses type hints, but some complex areas rely on `# type: ignore` or lack them entirely. Similarly, there are `# noqa` and `# pylint: disable` pragmas.
- **Consistent Formatting:** Enforcing strict formatting (e.g., `black`, `ruff`) and type checking (e.g., `mypy`) as part of the CI pipeline would reinforce the project's goal of being "teaching-first" by providing a consistently styled codebase for students to read.

### 5. Packaging and Accessibility
- **GUI Distribution:** The GUI application (`gui_app.py`) is a great entry point, especially for non-coders (as noted in `docs/SETUP_FOR_NONCODERS.md`). However, it still requires installing Python and `pip` dependencies. Packaging the GUI into a standalone executable (e.g., using `PyInstaller` or `cx_Freeze`) would significantly lower the barrier to entry.
- **WebMIDI Integration:** The `WebMidiStreamer` in `gui_backend.py` is currently wrapped in an optional `try...except` block for `websockets`. Making this a core, robust feature could allow audience members to view real-time telemetry on their phones, expanding the "Audience UX" goals outlined in `docs/UX_MAP.md`.

### 6. Documentation Consolidation
- **Scattered Playbooks:** The documentation is thorough and written in a great "zine/punk-rock" tone, but it is somewhat scattered across `docs/` and various `README.md` files. Consolidating this into a unified documentation site (e.g., using MkDocs or Sphinx) would make it easier to navigate the playbooks, ledgers, and technical references.
- **Expand Assumption Ledger:** The `ASSUMPTION_LEDGER.md` is quite sparse. It would benefit from more technical assumptions regarding hardware behavior (e.g., specific Betaflight versions tested, expected serial baud rates, handling of MSP disconnects).