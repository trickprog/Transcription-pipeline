"""One-click setup script for the transcription pipeline."""

import subprocess
import shutil
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
ENV_FILE = os.path.join(BACKEND, ".env")


def run(cmd, cwd=None):
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(1)


def find_ffmpeg():
    """Find ffmpeg on the system and return its directory path."""
    # Check if already on PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return os.path.dirname(os.path.abspath(ffmpeg_path))

    # Common install locations
    search_paths = []
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            # winget install location
            winget_dir = os.path.join(local, "Microsoft", "WinGet", "Packages")
            if os.path.isdir(winget_dir):
                for folder in os.listdir(winget_dir):
                    if "FFmpeg" in folder:
                        bin_path = os.path.join(winget_dir, folder)
                        for root, dirs, files in os.walk(bin_path):
                            if "ffmpeg.exe" in files:
                                return root
        search_paths += ["C:\\ffmpeg\\bin", "C:\\Program Files\\ffmpeg\\bin"]
    else:
        search_paths += ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin"]

    for p in search_paths:
        if os.path.isfile(os.path.join(p, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")):
            return p

    return None


def write_env(ffmpeg_dir):
    """Write or update the .env file with discovered paths."""
    env_vars = {}

    # Read existing .env
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f.readlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

    # Update ffmpeg path
    if ffmpeg_dir:
        env_vars["FFMPEG_PATH"] = ffmpeg_dir

    env_vars.setdefault("WHISPER_MODEL", "base")

    # Write .env
    with open(ENV_FILE, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")


def main():
    print("=" * 50)
    print("TRANSCRIPTION PIPELINE SETUP")
    print("=" * 50)

    # Step 0: Find ffmpeg
    print("\n[0/6] Looking for ffmpeg...")
    ffmpeg_dir = find_ffmpeg()
    if ffmpeg_dir:
        print(f"Found ffmpeg at: {ffmpeg_dir}")
        write_env(ffmpeg_dir)
    else:
        print("ffmpeg not found! Install it:")
        if sys.platform == "win32":
            print("  winget install ffmpeg")
        else:
            print("  brew install ffmpeg  (macOS)")
            print("  sudo apt install ffmpeg  (Linux)")
        sys.exit(1)

    # Step 1: Create Python virtual environment
    venv_path = os.path.join(BACKEND, "venv")
    if not os.path.exists(venv_path):
        print("\n[1/6] Creating Python virtual environment...")
        run(f'"{sys.executable}" -m venv venv', cwd=BACKEND)
    else:
        print("\n[1/6] Virtual environment already exists — skipping")

    # Determine pip and python paths inside venv
    if sys.platform == "win32":
        pip = os.path.join(venv_path, "Scripts", "pip.exe")
        python = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        pip = os.path.join(venv_path, "bin", "pip")
        python = os.path.join(venv_path, "bin", "python")

    # Step 2: Install Python dependencies
    print("\n[2/6] Installing Python dependencies...")
    run(f'"{python}" -m pip install --upgrade pip', cwd=BACKEND)
    run(f'"{pip}" install -r requirements.txt', cwd=BACKEND)

    # Step 3: Download Whisper model
    print("\n[3/6] Downloading Whisper base model...")
    run(f'"{python}" -c "import whisper; whisper.load_model(\'base\')"', cwd=BACKEND)

    # Step 4: Install frontend dependencies
    print("\n[4/6] Installing frontend dependencies...")
    run("npm install", cwd=FRONTEND)

    # Step 5: Build frontend
    print("\n[5/6] Building frontend...")
    run("npm run build", cwd=FRONTEND)

    print("\n" + "=" * 50)
    print("SETUP COMPLETE")
    print("=" * 50)

    # Step 6: Start servers
    print("\n[6/6] Starting servers...")
    print("\nStarting backend on http://127.0.0.1:5000 ...")
    backend_proc = subprocess.Popen(
        [python, "server.py"],
        cwd=BACKEND,
    )

    # Start React frontend
    print("Starting frontend on http://localhost:3000 ...")
    frontend_proc = subprocess.Popen(
        ["npm", "start"],
        cwd=FRONTEND,
        shell=True,
    )

    print("\nBoth servers running. Press Ctrl+C to stop.\n")

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()


if __name__ == "__main__":
    main()
