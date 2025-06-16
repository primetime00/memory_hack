# Memory Hack
## _Cross-platform memory editor for games_

Memory Hack is a cross-platform memory editor with a web based front-end.

- Search and modify memory regions.
- Save and load codes for use in games.
- Create scripts to enable trainer-like abilities.

## Features

- Memory searcher that can find 1, 2, 4, 8 byte values as well as floating point values.
- Unknown value scanner to search for values not represented as numeric (life bars, timers, etc...)
- AOB (Array of bytes) heap scanner to help narrow down dynamic values.
- Code list that can store memory addresses and AOB values for reuse.
- Python script importer that can load scripts to enable trainer-like abilities.
- Web-based front-end that can be accessed from PC or phone.

## Requirements
- Python >= 3.11

## Screenshots

|                                             Code List                                             |                                              Search                                              |
|:-------------------------------------------------------------------------------------------------:|:------------------------------------------------------------------------------------------------:|
| ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_codes.png) | ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_search.png) | 

&NewLine;
&NewLine;

|                                                AOB                                                |                                              Scripts                                              |
|:-------------------------------------------------------------------------------------------------:|:-------------------------------------------------------------------------------------------------:|
| ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_aob.png) | ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_scripts.png) | 

Memory Hack uses a number of open source projects to work properly:

- [Falcon] - Minimalist ASGI/WSGI framework for building mission-critical REST APIs.
- [OnsenUI] - A rich variety of UI components specially designed for mobile apps.
- [jQuery] - Fast, small, and feature-rich JavaScript library.
- [mem_edit] - Multi-platform memory editing library written in Python.

## Installation
### Windows
From Windows, a powershell command can be run to download the installer script.  This script will grab the code from the repository and optionally set up Memory Hack as a service.
1. Create a directory where Memory Hack should be installed.
2. Run the powershell command to get the code.
```
powershell -Command "(new-object System.Net.WebClient).DownloadFile('https://github.com/primetime00/memory_hack/raw/master/app/patches/win_install.py','install.py')"
```
3. Once the installation script is downloaded install the code:
```
python install.py
```
During installation, you will be asked if Memory Hack can be installed as a service.  If Memory Hack is run as a service, it will always be running.  Otherwise, Memory Hack must be manually started.
> **_NOTE:_**  Service installation for Windows uses [Non-Sucking Service Manager] to make service installation easier.
4. Run Memory Hack if it was not installed as a service.
```
run.bat
```
5. Test Memory Hack by opening a browser windows and pointing it to [localhost:5000](http://localhost:5000)

#### Uninstall
To uninstall Memory Hack, navigate to the installation directory and run the installation script again.
```
python install.py
```
The script should detect the installation and ask if you would like to uninstall Memory Hack.

### Linux
Like Windows, Linux will download the installation script and install, optionally setting up Memory Hack as a service.
1. Create a directory where Memory Hack should be installed.
2. Run the following command to download and install.
```
python3 <(wget -qO- https://github.com/primetime00/memory_hack/raw/master/app/patches/install.py)
```
During installation, you will be asked if Memory Hack can be installed as a service.  If Memory Hack is run as a service, it will always be running.  Otherwise, Memory Hack must be manually started.
3. Run Memory Hack if it was not installed as a service.
```
./run.sh
```
4. Test Memory Hack by opening a browser window and pointing it to [localhost:5000](http://localhost:5000)

#### Uninstall
To uninstall Memory Hack, navigate to the installation directory and run the installation script again.
```
python install.py
```
The script should detect the installation and ask if you would like to uninstall Memory Hack.
### Steam Deck
Steam Deck installation follows the Linux installation.  However, you must have a password set on the Steam Deck to install Memory Hack. Those instructions can be found [here](https://steamdecktips.com/blog/how-to-set-a-password-for-your-steam-deck-user-in-desktop-mode)

1. Create a directory where Memory Hack should be installed.
2. Run the following command to download and install.
```
python3 <(wget -qO- https://github.com/primetime00/memory_hack/raw/master/app/patches/install.py)
```
During installation, you will be asked if Memory Hack can be installed as a service.  If Memory Hack is run as a service, it will always be running.  Otherwise, Memory Hack must be manually started.
3. Run Memory Hack if it was not installed as a service.
```
./run.sh
```
4. Test Memory Hack by opening a browser window and pointing it to [localhost:5000](http://localhost:5000)

#### Uninstall
To uninstall Memory Hack, navigate to the installation directory and run the installation script again.
```
python install.py
```
The script should detect the installation and ask if you would like to uninstall Memory Hack.

## Usage
Memory Hack is controlled through your browser.  Ideally, Memory Hack can be accessed through your phone.  To do this, your PC/Stream Deck must have a known IP address or host name.  For example, the Steam Deck has a default host name of `steamdeck`

You would access Memory Hack by opening your phone's browser and navigating to `http://steamdeck:5000`

You would then see the UI for Memory Hack.

Here are instructions for setting up a hostname in [Linux](https://www.tecmint.com/set-hostname-permanently-in-linux/) and [Windows](https://tecadmin.net/change-windows-hostname/) 

## Tutorial
A basic tutorial on usage can be found [here.](https://github.com/primetime00/memory_hack/blob/master/docs/tutorial/TUTORIAL.md)

## License

MIT

**It's Free**

## Donate
Only if you want

<a href="https://www.buymeacoffee.com/ryankegel" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

[//]: #

   [Non-Sucking Service Manager]: <https://nssm.cc/>
   [mem_edit]: <https://mpxd.net/code/jan/mem_edit>
   [OnsenUI]: <https://onsen.io/>
   [Falcon]: <https://github.com/falconry/falcon>
   [jQuery]: <http://jquery.com>
