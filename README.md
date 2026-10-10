# Desktop User Service AI Agent

An AI-powered desktop assistant that interacts with a computer through its graphical user interface, much like a human using a mouse and keyboard. It understands natural-language instructions, observes the screen, determines the next action, executes it, and verifies the result before proceeding.

Built with Python and PySide6, the application combines multimodal large language models (LLMs), screenshot analysis, desktop automation, voice input, and an autonomous observe–act–verify loop to perform multi-step computer tasks with minimal human intervention.

The application provides two primary modes: **Auto Summarizer** for intelligent screen analysis and **Service Agent** for autonomous task execution. It supports configurable integrations with Anthropic Claude, Google Gemini, and OpenAI.

## Features

### 1. Auto Summarizer

Analyze the current screen and generate contextual summaries using a vision-capable LLM.

- **On-demand summarization:** Capture and summarize the current screen with a button or global hotkey.
- **Automatic summarization:** Run at configurable time intervals.
- **Screen-change detection:** Optionally skip processing when the screen has not changed significantly.
- **Custom focus:** Specify what to extract, such as action items, important information, error messages, or a summary of the current application.
- **Adjustable detail:** Configure the level of detail in generated summaries.
- **Multimodal analysis:** Send a downscaled screenshot to the selected LLM for visual understanding.

### 2. Autonomous Service Agent

Give the agent a task through chat or voice, and it will interact with desktop applications to complete the requested workflow.

Example commands:

- "Open Chrome and search for the latest developments in AI."
- "Create a folder named Project Reports on my desktop."
- "Open this document and summarize its main points."
- "Fill out the form using the information I provide."
- "Navigate to my email and prepare a leave request."
- "Find a particular file and move it into the appropriate folder."

The agent follows an iterative execution process:

1. **Understand:** Interpret the user's instruction and identify the intended outcome.
2. **Observe:** Capture a screenshot of the current desktop.
3. **Reason:** Send the screenshot and task context to the selected LLM to determine the next single action.
4. **Execute:** Perform the action through the DesktopController using mouse and keyboard inputs.
5. **Verify:** Capture a fresh screenshot to determine whether the action succeeded.
6. **Recover:** Retry unsuccessful actions using an alternative approach, within configured limits.
7. **Clarify:** Ask the user for additional information when the interface or instruction is ambiguous.
8. **Continue:** Repeat the process until the task is completed, fails, or requires user intervention.

The agent does not simply generate a sequence of clicks and execute it blindly. Each action is followed by a new observation, allowing subsequent decisions to account for changes in the interface.

### 3. Human-Like Mouse and Keyboard Control

The `DesktopController` provides the computer interaction layer.

Supported actions include:

- Single-click and double-click
- Right-click and pointer movement
- Drag-and-drop
- Text entry
- Keyboard keys and shortcuts
- Scrolling
- Waiting for an application or interface to respond
- Asking the user questions
- Reporting completion or failure

Screenshots are downscaled to a configurable maximum dimension, with a default of 1280 pixels. Coordinates returned by the model are mapped back to the actual screen dimensions, including HiDPI displays.

### 4. Voice Interaction

Interact with the agent without typing every instruction.

- Record commands through the microphone button or global hotkey.
- Detect the end of speech using silence detection.
- Convert speech into text using supported speech-to-text integrations.
- Execute the resulting instruction through the same Service Agent workflow.
- Display clarification questions in chat when additional information is needed.

Available speech recognition options depend on the configured provider and installed dependencies.

### 5. Live Status Window

A separate status window provides visibility into the agent's current activity.

It can display stages such as:

- Capturing the screen
- Sending context to the LLM
- Waiting for a model response
- Executing mouse or keyboard actions
- Verifying the result
- Retrying a failed action
- Waiting for user clarification
- Completing or failing a task

The status window helps users monitor autonomous execution without needing to keep the main chat interface in the foreground.

### 6. Glassmorphism Desktop Interface

The application uses a translucent, glass-inspired desktop UI built with PySide6 and QtAwesome.

- Frameless window with a custom title bar and controls.
- Configurable appearance and theme.
- Resizable interface panels.
- System-tray integration.
- Main chat window and separate live status window.
- Settings for model providers, API keys, voice, hotkeys, and agent behavior.
- Configurable window visibility and screen-capture behavior.

### 7. Global Hotkeys

The following default shortcuts provide quick access to common operations.

| Shortcut | Action |
|---|---|
| `Ctrl + Alt + S` | Summarize the current screen |
| `Ctrl + Alt + Space` | Show or hide the main window |
| `Ctrl + Alt + V` | Start voice input |
| `Ctrl + Alt + X` | Emergency stop |

Hotkeys can be changed through Settings, subject to platform permissions and shortcut validation.

### 8. Window Visibility and Capture Exclusion

The application includes options to reduce its visibility during normal desktop use and screen capture.

- System-tray access and configurable window visibility.
- Tool-window behavior intended to avoid ordinary taskbar and Alt-Tab entries where supported.
- On supported Windows 10 and Windows 11 systems, use of `WDA_EXCLUDEFROMCAPTURE` to request exclusion of application windows from supported screen-capture methods.
- An alternative temporary-hide strategy for platforms where capture exclusion is unavailable.
- Configurable screen and voice settings.

**Platform limitation:** Capture exclusion and window-hiding behavior depend on the operating system and capture method. They do not guarantee invisibility to every screenshot, recording, or monitoring tool.

### 9. Safety and Error Recovery

Because the agent can control the real mouse and keyboard, safety mechanisms are essential.

- Emergency stop through a global hotkey or Stop button.
- Optional emergency activation by moving the mouse to a screen corner.
- Bounded retries for unsuccessful actions.
- User clarification when a task is ambiguous.
- Permission checks for configured risky actions, such as deleting files or making payments.
- Instructions to avoid entering passwords automatically and request manual login where required.
- Live progress monitoring and explicit failure reporting.

The agent should request approval before consequential actions that require confirmation. Users should supervise unfamiliar workflows, especially when interacting with financial accounts, personal information, or irreversible operations.

## Architecture

The application separates its user interface, AI reasoning, screenshot capture, and desktop interaction into modular components.

```text
User
 │
 ├── Chat Input
 ├── Voice Input
 └── Global Hotkeys
       │
       ▼
┌───────────────────────────────┐
│       PySide6 Desktop UI      │
│  Chat · Settings · Status     │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│       Agent Service           │
│ Task Context · Action Loop    │
└───────────────┬───────────────┘
                │
       ┌────────┴─────────┐
       ▼                  ▼
┌──────────────┐  ┌─────────────────┐
│ Screen       │  │ LLM Integration │
│ Capture      │  │ Claude/Gemini/   │
│ & Analysis   │  │ OpenAI           │
└──────┬───────┘  └────────┬────────┘
       │                   │
       └─────────┬─────────┘
                 ▼
       ┌───────────────────┐
       │ Action Parser     │
       │ Validate Action   │
       └─────────┬─────────┘
                 ▼
       ┌───────────────────┐
       │ DesktopController │
       │ Mouse & Keyboard  │
       └─────────┬─────────┘
                 │
                 ▼
          Desktop Interface
                 │
                 └──────► New Screenshot
                            and Verification
```

### Execution Loop

```text
Receive user instruction
          │
          ▼
Capture screenshot
          │
          ▼
Ask LLM for one next action
          │
          ▼
Parse and validate action
          │
          ▼
Check required permissions
          │
          ▼
Execute with DesktopController
          │
          ▼
Wait for interface response
          │
          ▼
Capture a new screenshot
          │
          ▼
Verify the outcome
     ┌────┼─────────┐
     ▼    ▼         ▼
 Verified Retry   Clarification
     │    │         │
     │    └─ Retry  └─ Ask user
     │       within      │
     │       limit       └─ Resume
     ▼
Continue or report completion
```

The LLM proposes actions, while the local application parses, validates, and executes them. Verification is based on subsequent screen observations and model interpretation; it is not a formal guarantee that every operation succeeded.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.10+ |
| Desktop UI | PySide6 |
| UI icons | QtAwesome |
| Mouse and keyboard automation | PyAutoGUI |
| Screenshot capture | MSS |
| Global keyboard shortcuts | pynput |
| AI providers | Anthropic Claude, Google Gemini, OpenAI |
| Voice input | Microphone recording, silence detection, speech-to-text |
| Configuration | JSON |
| Testing | Python `unittest` |
| Windows packaging | PyInstaller-based executable build |

Provider availability and API compatibility depend on the configured client implementation and model.

## Installation

### Prerequisites

- Windows 10/11, macOS, or a supported Linux desktop.
- Python 3.10 or newer.
- An API key for a supported LLM provider.
- Microphone access if voice input is required.
- Appropriate screen-recording and accessibility permissions for the operating system.

### Windows

1. Install Python and enable **Add Python to PATH** during installation.
2. Clone or download the project repository.
3. Open the project directory.
4. Run `install_windows.bat`.
5. Once installation completes, run `run.bat`.
6. Open Settings and select the desired LLM provider.
7. Enter the API key, select a supported model, and use **Test connection**.
8. Save the settings and begin using the summarizer or Service Agent.

```bat
install_windows.bat
run.bat
```

### macOS and Linux

From the project directory, run:

```bash
chmod +x run.sh
./run.sh
```

On macOS, grant the required Screen Recording, Accessibility, and Microphone permissions.

On Linux, synthetic input support depends on the display server and desktop environment. The current implementation targets X11; Wayland may restrict automated input and screen capture.

## Configuration

API keys can be configured through the application Settings or supplied through environment variables.

```text
ANTHROPIC_API_KEY
GEMINI_API_KEY
OPENAI_API_KEY
```

Only configure the key for the provider you intend to use. Keep API keys private and never commit them to the repository.

Configuration is stored locally in the platform's application configuration directory.

| Platform | Configuration location |
|---|---|
| Windows | `%APPDATA%\DesktopAIAgent\config.json` |
| macOS | `~/Library/Application Support/` |
| Linux | `~/.config/` |

The exact configuration filename and directory may depend on the platform-specific implementation.

## Using the Application

### Auto Summarizer

1. Open the desktop assistant.
2. Select Auto Summarizer.
3. Choose the desired summary detail level.
4. Optionally enter a focus instruction, such as "Extract action items."
5. Press the summarize button or use `Ctrl + Alt + S`.
6. To enable periodic summarization, configure the interval and activate the automatic mode.
7. Enable screen-change detection if you want unchanged screens to be skipped.

### Service Agent

1. Open the Service Agent chat.
2. Enter a natural-language task or activate voice input using `Ctrl + Alt + V`.
3. Review the task and let the agent begin its screenshot-based execution loop.
4. Monitor progress in the live status window.
5. Respond to clarification questions when the agent needs more information.
6. Use the Stop button or `Ctrl + Alt + X` to interrupt execution.
7. Verify the final result in the target application.

For consequential actions, supervise the agent and review any requested approvals before proceeding.

## Project Structure

```text
Desktop-User-Service-AI-Agent/
│
├── main.py
├── install_windows.bat
├── run.bat
├── run.sh
├── build_exe_windows.bat
│
├── agent/
│   ├── llm/
│   │   ├── base.py
│   │   ├── claude.py
│   │   ├── gemini.py
│   │   ├── openai_client.py
│   │   └── ...
│   │
│   ├── service.py
│   ├── controller.py
│   ├── summarizer.py
│   ├── screen.py
│   ├── voice.py
│   ├── hotkeys.py
│   ├── prompts.py
│   └── platform_utils.py
│
├── ui/
│   ├── main_window.py
│   ├── status_window.py
│   ├── settings.py
│   └── ...
│
└── tests/
```

### Core Modules

- **`main.py`** — Application entry point and initialization.
- **`agent/service.py`** — Orchestrates the autonomous task execution loop.
- **`agent/controller.py`** — Executes mouse and keyboard actions.
- **`agent/screen.py`** — Captures screenshots and detects screen changes.
- **`agent/summarizer.py`** — Handles AI-powered screen summarization.
- **`agent/voice.py`** — Handles microphone input and speech recognition.
- **`agent/hotkeys.py`** — Registers and manages global shortcuts.
- **`agent/prompts.py`** — Contains prompts and action parsing logic.
- **`agent/platform_utils.py`** — Implements platform-specific window behavior.
- **`agent/llm/`** — Contains provider-specific LLM clients.
- **`ui/`** — Contains the desktop interface, status window, settings, and system-tray integration.
- **`tests/`** — Contains automated tests.

The layout above describes the intended module organization; adjust filenames to match the actual repository.


## Building a Standalone Windows Executable

Run the packaging script:

```bat
build_exe_windows.bat
```

If the build completes successfully, the executable is expected at:

```text
dist/DesktopAIAgent.exe
```

The packaged application should be tested on a clean Windows environment to verify that dependencies, provider integrations, configuration, hotkeys, and platform-specific functionality work correctly.

## Privacy and Security

The agent may capture screens containing emails, documents, browser tabs, account information, or other sensitive material.

- Screenshots submitted for model analysis are sent to the selected provider.
- API usage may incur charges according to the provider's pricing and account limits.
- Keep API keys out of source control and shared logs.
- Avoid capturing screens containing information you do not want to transmit.
- Require confirmation for destructive or consequential actions.
- Never rely on an LLM alone to enforce security policies.
- Keep the emergency-stop shortcut available while the agent is operating.
- Verify actions in the target application, especially when handling personal or financial information.

Capture-exclusion features are operating-system dependent and should not be treated as a privacy or security boundary.


## Future Improvements

Potential areas for further development include:

- Persistent task memory and recovery after application interruptions.
- Better UI element detection and coordinate grounding.
- More robust action verification and confidence scoring.
- Application-specific automation adapters alongside screenshot-based control.
- Improved local speech recognition and text-to-speech.
- Task history, execution logs, and replayable workflows.
- More granular permissions and approval policies.
- Support for additional model providers and local multimodal models.

## License

MIT License

---

**Desktop User Service AI Agent** aims to make everyday computer interaction more accessible by combining visual understanding, natural-language reasoning, and desktop automation in a single assistant. Its central principle is simple: observe the computer, perform one action, verify the result, and repeat until the task is complete or user intervention is required.