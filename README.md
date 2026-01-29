# PVZ Sun Autoclicker

A Python-based autoclicker for Plants vs. Zombies that automatically detects and collects suns using computer vision.

## Features

- **Auto-collection**: Automatically clicks on suns as they fall.
- **Multi-monitor support**: Works across multiple monitors (cycle through them).
- **Control Interface**: Simple keyboard shortcuts to control the bot.
- **Debug View**: Visual feedback showing what the bot sees and detects.

## Prerequisites

- [Python 3.x](https://www.python.org/downloads/)

## Installation

1.  Clone this repository or download the source code.
2.  Install the required Python packages:

    ```bash
    pip install opencv-python numpy pyautogui keyboard mss pillow
    ```

## Usage

1.  Ensure you have the `sun.png` template image in the same directory as the script.
2.  Run the script:

    ```bash
    python sunClicker.py
    ```

3.  **Controls**:
    - `p`: **Pause/Resume** the autoclicker.
    - `m`: **Cycle Monitor** (if you have multiple screens and the game is on a secondary one).
    - `d`: **Toggle Debug View** (show/hide computer vision output).
    - `q`: **Quit** the program.

## Troubleshooting

-   **Sun not detected**: Make sure the `sun.png` image matches the suns in your version of the game. You may need to take a fresh screenshot and crop it if the resolution differs.
-   **Clicks offset**: If the bot detects the sun but clicks in the wrong place on a multi-monitor setup, try cycling the monitor selection with `m`.

## License

This project is open source.
