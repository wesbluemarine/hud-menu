# hud-menu

Provides a way to run or raise executables, run menubar commands, select opened windows, through a searchable list.


## Dependencies
* python-dbus
* dmenu
* fd-find
* xfce4-appmenu-plugin
 

## Setup
1. ror.sh script should be added to $PATH.
2. ```hud-menu-service.py``` should be started (with python 3+) on the session's startup.
3. The following should be added to the user's ```/etc/environment```: 

    ```
    UBUNTU_MENUPROXY=1
    GTK_MODULES=appmenu-gtk-module

   ```
    
4. ```hud-menu.py``` should be bound to run (with python 3+) with a shortcut (such as a keyboard shortcut). 

## Usage
The user should active the shortcut when the window they wish to show the application menu entries for has focus.  This will open the dmenu at the top.
The user can then use the keyboard to search and navigate the entries.
Pressing enter will execute the selected entry and pressing escape will close the dmenu without executing anything.
