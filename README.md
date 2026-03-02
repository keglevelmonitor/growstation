## 💻 GrowStation Project
 
The **GrowStation Project** allows the user to control lights, heaters, fans, or other small appliances for a home plant growing station. 

Currently tested only on the Raspberry Pi 3B running Trixie and Bookworm. Should work with RPi4 and RPi5 running the same OS's but not yet tested.

Please **donate $$** if you use the app. See "Support the app" on the Settings menu. 

![Support QR Code](src/assets/support.gif)

## 💻 I have also deployed a suite of Apps for the Home Brewer
**🔗 [KettleBrain Project](https://github.com/keglevelmonitor/kettlebrain)** An electric brewing kettle control system

**🔗 [FermVault Project](https://github.com/keglevelmonitor/fermvault)** A fermentation chamber control system

**🔗 [KegLevel Lite Project](https://github.com/keglevelmonitor/keglevel_lite)** A keg level monitoring system

**🔗 [BatchFlow Project](https://github.com/keglevelmonitor/batchflow)** A homebrew batch management system

**🔗 [TempMonitor Project](https://github.com/keglevelmonitor/tempmonitor)** A temperature monitoring and charting system


## To Install the App

Open **Terminal** and run this command. Type carefully and use proper uppercase / lowercase because it matters:

```bash
bash <(curl -sL bit.ly/install-growstation)
```

That's it! You will now find the app in your application menu under **Other**. You can use the "Check for Updates" function inside the app to install future updates.

## To TEST the App in the Windows Environment

On a Windows 10+ computer, open **Command Prompt** and run this command. Type carefully and use proper uppercase / lowercase because it matters:

```bash
curl -sL bit.ly/growstation-win -o setup.bat && setup.bat
```

## 🔗 Detailed installation instructions

👉 (placeholder for detailed installation instructions)

## ⚙️ Summary hardware requirements

Required
* Raspberry Pi 3B (should work on RPi 4 but not yet tested)
* Debian Trixie OS (not tested on any other OS)

## To uninstall the app

To uninstall, open **Terminal** and run this command. Type carefully and use proper uppercase / lowercase because it matters:

```bash
bash <(curl -sL https://bit.ly/install-growstation)
```
then select the UNINSTALL option from the menu. 

## ⚙️ For reference
Installed file structure:

```
~/batchflow/
|-- utility files...
|-- src/
|   |-- application files...
|   |-- assets/
|       |-- supporting files...
|-- venv/
|   |-- python3 & dependencies
~/batchflow-data/
|-- user data...
    
Required system-level dependencies are installed via sudo apt outside of venv.

```
