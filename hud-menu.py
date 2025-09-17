#!/usr/bin/env python3
import dbus
import subprocess
import os
import sys

# -----------------------------
# Utility
# -----------------------------
def run_or_raise(exe):
    ror_path = os.path.expanduser('~/bin/ror.sh')
    subprocess.Popen(f'{ror_path} {exe} &', shell=True, env=os.environ)

def format_label_list(label_list):
    head, *tail = label_list
    result = head
    for label in tail:
        result += " > " + label
    result = result.replace("Root > ", "")
    result = result.replace("_", "")
    return result

def get_executables_in_path():
    executables = set()
    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isdir(path_dir):
            for f in os.listdir(path_dir):
                full_path = os.path.join(path_dir, f)
                if os.access(full_path, os.X_OK) and not os.path.isdir(full_path):
                    executables.add(f)
    return sorted(executables)

def get_open_windows():
    try:
        out = subprocess.check_output(["wmctrl", "-l"]).decode("utf-8").splitlines()
        win_dict = {}
        for line in out:
            parts = line.split(None, 3)
            if len(parts) >= 4:
                wid, desktop, host, title = parts[0], parts[1], parts[2], parts[3]
                if title.strip():
                    win_dict[title] = wid
        return win_dict
    except Exception:
        return {}

# -----------------------------
# Run dmenu
# -----------------------------
def run_dmenu(menuKeys, prompt="Run:"):
    menu_string = "\n".join(menuKeys)
    menu_cmd = subprocess.Popen([
        "dmenu", "-i", "-l", "20",
        "-nb", "#f8f8f8", "-nf", "#2e3436",
        "-sb", "#3465a4", "-sf", "#ffffff",
        "-p", prompt, "-fn", "Sans-10"
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    menu_cmd.stdin.write(menu_string.encode("utf-8"))
    menu_result = menu_cmd.communicate()[0].decode("utf-8").rstrip()
    menu_cmd.stdin.close()
    return menu_result

def run_extended_dmenu(exec_keys, win_dict, extra_keys=None, prompt="Run:"):
    marked_execs = ["*" + e for e in exec_keys]
    baseKeys = []
    if extra_keys:
        baseKeys += extra_keys
    baseKeys += marked_execs + sorted(win_dict.keys())
    choice = run_dmenu(baseKeys, prompt)
    return choice

# -----------------------------
# Fallback menu
# -----------------------------
def fallback_menu():
    win_dict = get_open_windows()
    execs = get_executables_in_path()
    menu_result = run_extended_dmenu(execs, win_dict)
    if menu_result.startswith("*"):
        run_or_raise(menu_result.lstrip("*"))
    elif menu_result in win_dict:
        subprocess.Popen(["wmctrl", "-ia", win_dict[menu_result]])
    elif menu_result:
        subprocess.Popen(["xdg-open", menu_result])

# -----------------------------
# AppMenu interface
# -----------------------------
def try_appmenu_interface(window_id):
    session_bus = dbus.SessionBus()
    try:
        appmenu_registrar_object = session_bus.get_object(
            "com.canonical.AppMenu.Registrar", "/com/canonical/AppMenu/Registrar"
        )
        appmenu_registrar_object_iface = dbus.Interface(
            appmenu_registrar_object, "com.canonical.AppMenu.Registrar"
        )
        dbusmenu_bus, dbusmenu_object_path = appmenu_registrar_object_iface.GetMenuForWindow(window_id)
    except dbus.exceptions.DBusException:
        fallback_menu()
        return

    dbusmenu_object = session_bus.get_object(dbusmenu_bus, dbusmenu_object_path)
    dbusmenu_object_iface = dbus.Interface(dbusmenu_object, "com.canonical.dbusmenu")
    dbusmenu_items = dbusmenu_object_iface.GetLayout(0, -1, ["label"])

    dbusmenu_item_dict = {}
    blacklist = []

    def explore_dbusmenu_item(item, label_list):
        item_id, item_props, item_children = item
        new_label_list = label_list + [item_props["label"]] if "label" in item_props else label_list
        if not item_children:
            if new_label_list not in blacklist:
                dbusmenu_item_dict[format_label_list(new_label_list)] = item_id
        else:
            blacklist.append(new_label_list)
            for child in item_children:
                explore_dbusmenu_item(child, new_label_list)

    explore_dbusmenu_item(dbusmenu_items[1], [])

    win_dict = get_open_windows()
    execs = get_executables_in_path()
    marked_execs = ["*" + e for e in execs]
    menuKeys = sorted(dbusmenu_item_dict.keys()) + marked_execs + sorted(win_dict.keys())
    menu_result = run_dmenu(menuKeys)

    if menu_result in dbusmenu_item_dict:
        action = dbusmenu_item_dict[menu_result]
        dbusmenu_object_iface.Event(action, "clicked", 0, 0)
    elif menu_result.startswith("*"):
        run_or_raise(menu_result.lstrip("*"))
    elif menu_result in win_dict:
        subprocess.Popen(["wmctrl", "-ia", win_dict[menu_result]])
    elif menu_result:
        subprocess.Popen(["xdg-open", menu_result])

# -----------------------------
# GTK interface
# -----------------------------
def try_gtk_interface(gtk_bus_name_cmd, gtk_object_path_cmd):
    try:
        gtk_bus_name = gtk_bus_name_cmd.split(' ')[2].split('\n')[0].split('"')[1]
        gtk_object_path = gtk_object_path_cmd.split(' ')[2].split('\n')[0].split('"')[1]

        session_bus = dbus.SessionBus()
        gtk_menubar_object = session_bus.get_object(gtk_bus_name, gtk_object_path)
        gtk_menubar_object_iface = dbus.Interface(gtk_menubar_object, dbus_interface="org.gtk.Menus")
        gtk_action_object_actions_iface = dbus.Interface(gtk_menubar_object, dbus_interface="org.gtk.Actions")
        gtk_menubar_results = gtk_menubar_object_iface.Start([x for x in range(1024)])

        gtk_menubar_menus = {(r[0], r[1]): r[2] for r in gtk_menubar_results}
        gtk_menubar_action_dict = {}

        def explore_menu(menu_id, label_list):
            if menu_id in gtk_menubar_menus:
                for menu in gtk_menubar_menus[menu_id]:
                    if "label" in menu:
                        menu_label = menu["label"]
                        new_label_list = label_list + [menu_label]
                        formatted_label = format_label_list(new_label_list)
                        if "action" in menu and ":section" not in menu and ":submenu" not in menu:
                            gtk_menubar_action_dict[formatted_label] = menu["action"]
                    if ":section" in menu:
                        section_menu_id = (menu[":section"][0], menu[":section"][1])
                        explore_menu(section_menu_id, label_list)
                    if ":submenu" in menu:
                        submenu_menu_id = (menu[":submenu"][0], menu[":submenu"][1])
                        explore_menu(submenu_menu_id, new_label_list)

        explore_menu((0, 0), [])

        win_dict = get_open_windows()
        execs = get_executables_in_path()
        marked_execs = ["*" + e for e in execs]
        menuKeys = sorted(gtk_menubar_action_dict.keys()) + marked_execs + sorted(win_dict.keys())
        menu_result = run_dmenu(menuKeys)

        if menu_result in gtk_menubar_action_dict:
            action = gtk_menubar_action_dict[menu_result]
            gtk_action_object_actions_iface.Activate(action.replace("unity.", ""), [], dict())
        elif menu_result.startswith("*"):
            run_or_raise(menu_result.lstrip("*"))
        elif menu_result in win_dict:
            subprocess.Popen(["wmctrl", "-ia", win_dict[menu_result]])
        elif menu_result:
            subprocess.Popen(["xdg-open", menu_result])
    except Exception:
        fallback_menu()

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    try:
        window_id_cmd = subprocess.check_output(['xprop', '-root', '-notype', '_NET_ACTIVE_WINDOW']).decode('utf-8')
        window_id = window_id_cmd.split(' ')[4].split(',')[0].strip()
    except Exception:
        window_id = None

    try:
        if not window_id or window_id == "0x0":
            fallback_menu()
        else:
            gtk_bus_name_cmd = subprocess.check_output(['xprop', '-id', window_id, '-notype', '_GTK_UNIQUE_BUS_NAME']).decode('utf-8')
            gtk_object_path_cmd = subprocess.check_output(['xprop', '-id', window_id, '-notype', '_GTK_MENUBAR_OBJECT_PATH']).decode('utf-8')

            if ("not found" in gtk_bus_name_cmd or "no such atom" in gtk_bus_name_cmd or
                "not found" in gtk_object_path_cmd):
                try_appmenu_interface(int(window_id, 16))
            else:
                try_gtk_interface(gtk_bus_name_cmd, gtk_object_path_cmd)
    except Exception:
        fallback_menu()
