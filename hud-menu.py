#!/usr/bin/env python3
import subprocess
import os

# -------------------------------------------------
# Utility functions
# -------------------------------------------------

def run_dmenu(options, prompt="Run:"):
    """
    Show a dmenu with Adwaita colors and return the chosen option.
    """
    dmenu_cmd = [
        "dmenu",
        "-l", "20",
        "-i",
        "-fn", "Sans-10",
        "-nb", "#f8f8f8",
        "-nf", "#2e3436",
        "-sb", "#3465a4",
        "-sf", "#ffffff",
        "-p", prompt
    ]
    try:
        proc = subprocess.Popen(
            dmenu_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        stdout, _ = proc.communicate("\n".join(options))
        return stdout.strip()
    except Exception:
        return None


def get_executables_in_path():
    """
    Collect all executables available in the PATH.
    """
    execs = set()
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.isdir(path_dir):
            for f in os.listdir(path_dir):
                fp = os.path.join(path_dir, f)
                if os.access(fp, os.X_OK) and not os.path.isdir(fp):
                    execs.add(f)
    return sorted(execs)


def get_open_windows():
    """
    Retrieve open windows using wmctrl and return a dictionary {title: wid}.
    """
    win_dict = {}
    try:
        output = subprocess.check_output(["wmctrl", "-l"], text=True)
        for line in output.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4:
                wid, _, _, title = parts
                win_dict[title] = wid
    except Exception:
        pass
    return win_dict


def run_or_raise(cmd):
    """
    Run an executable or raise the existing window if it is already open.
    """
    win_dict = get_open_windows()
    for title, wid in win_dict.items():
        if cmd.lower() in title.lower():
            subprocess.Popen(["wmctrl", "-ia", wid])
            return
    subprocess.Popen([cmd])


# -------------------------------------------------
# File search with fdfind
# -------------------------------------------------

def search_file_with_fd():
    """
    Search for files in the home directory (non-hidden) using fdfind.
    Results are shown in dmenu and the chosen file is opened with xdg-open.
    """
    try:
        results = subprocess.check_output(
            ["fdfind", ".", os.path.expanduser("~"), "--type", "f"],
            text=True
        ).splitlines()

        if not results:
            run_dmenu(["No results"], prompt="Find:")
            return

        results = sorted(results, key=lambda s: s.lower())
        choice = run_dmenu(results, prompt="Find:")

        if choice:
            subprocess.Popen(["xdg-open", choice])
    except Exception as e:
        run_dmenu([f"Error: {e}"], prompt="Find:")


# -------------------------------------------------
# Menu wrappers
# -------------------------------------------------

def run_extended_dmenu(exec_keys, win_dict, extra_keys=None, prompt="Run:"):
    """
    Show a combined dmenu with executables, open windows and extra entries.
    - Executables are marked with a leading '*'
    - Extra entries (like file search) always appear on top
    """
    marked_execs = ["*" + e for e in exec_keys]
    baseKeys = []
    if extra_keys:
        baseKeys = extra_keys + baseKeys
    baseKeys += marked_execs + sorted(win_dict.keys())
    return run_dmenu(baseKeys, prompt)


def fallback_menu():
    """
    Fallback menu shown when no appmenu/global menu is available.
    """
    win_dict = get_open_windows()
    execs = get_executables_in_path()
    extra = ["🔎 Search file"]
    menu_result = run_extended_dmenu(execs, win_dict, extra_keys=extra)

    if menu_result == "🔎 Search file":
        search_file_with_fd()
    elif menu_result and menu_result.startswith("*"):
        run_or_raise(menu_result.lstrip("*"))
    elif menu_result in win_dict:
        subprocess.Popen(["wmctrl", "-ia", win_dict[menu_result]])
    elif menu_result:
        subprocess.Popen(["xdg-open", menu_result])


def try_appmenu_interface():
    """
    Placeholder for AppMenu/DBus global menu integration.
    Currently falls back to the fallback menu.
    """
    fallback_menu()


def try_gtk_interface():
    """
    Placeholder for GTK HUD menu integration.
    Currently falls back to the fallback menu.
    """
    fallback_menu()


# -------------------------------------------------
# Entry point
# -------------------------------------------------

if __name__ == "__main__":
    # By default, run the AppMenu interface (can be changed to fallback_menu())
    try_appmenu_interface()
        
