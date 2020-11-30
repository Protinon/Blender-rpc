# Blender Rich Presence

If you want to show off what you're doing in Blender, then this is the addon for you! With added options, you can customize it you suit your preference. This is currently only supported on Blender 2.8 and above. See below for install instructions.

![Rich Presence Preview](images/preview.png)

## Features

* **Multi-instance support:** If multiple Blender windows are open, the one that was most recently saved will send data to Discord.
* **Rendering mode:** Will show info about current render, as shown in the above image.
* **Blender Version:** Displays the current Blender version in a nice format when hovering over the Blender icon.
* **Options:** Allows a few settings to be changed on the Blender addon screen, more info below.

## Options

* Show elapsed time
* Show elapsed time while rendering
* What to show while rendering: Filename or Render engine

## How to Install

* Go to the "Releases" tab on this page
* Download the latest .zip
* Install the .zip as a Blender addon
* Enable and modify settings

## Forking

This repository will not work as a Blender addon if cloned, the submodule folder "pypresence" will be empty. To fill the contents of this folder:

* Clone the repository from the Git CLI
* `git submodule init`
* `git submodule update`