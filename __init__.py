import bpy
import os
import sys
import time
from .pypresence import pypresence as rpc


bl_info = {
    "name": "Blender Rich Presence",
    "description": "Discord Rich Presence support for Blender",
    "author": "Protinon",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "tracker_url": "https://github.com/Protinon/Blender-rpc",
    "category": "System",
}


# Blender Bot ID
rpcConn = rpc.Presence("674448359850901546")
# Name of Blender icon that has been uploaded to the discord bot
iconBlender = 'blender'
# Get the temp directory of the system based on Blender's temp dir
pidFilePath = os.path.join(os.path.dirname(os.path.normpath(bpy.app.tempdir)), "BlendRpcPid")
# Start time of the Blender session
startTime = None
# Info on a rendering session
renderContext = None

class RenderInfo:
    def __init__(self):
        self.startTime = time.time()
        self.renderedFrames = 0

    @property
    def isAnimation(self):
        return self.renderedFrames > 0


def register():
    global startTime

    bpy.utils.register_class(RpcPreferences)
    startTime = time.time()
    rpcConn.connect()
    writePidFileAtomic()
    bpy.app.timers.register(updatePresenceTimer, first_interval=1.0, persistent=True)
    bpy.app.handlers.save_post.append(writePidHandler)
    # Rendering
    bpy.app.handlers.render_init.append(startRenderJobHandler)
    bpy.app.handlers.render_complete.append(endRenderJobHandler)
    bpy.app.handlers.render_cancel.append(endRenderJobHandler)
    bpy.app.handlers.render_post.append(postRenderHandler)
    bpy.app.handlers.load_post.append(fileLoadHandler)

def unregister():
    global startTime

    startTime = None
    rpcConn.close()
    removePidFile()
    bpy.app.timers.unregister(updatePresenceTimer)
    bpy.app.handlers.save_post.remove(writePidHandler)
    bpy.utils.unregister_class(RpcPreferences)
    # Rendering
    bpy.app.handlers.render_init.remove(startRenderJobHandler)
    bpy.app.handlers.render_complete.remove(endRenderJobHandler)
    bpy.app.handlers.render_cancel.remove(endRenderJobHandler)
    bpy.app.handlers.render_post.remove(postRenderHandler)
    bpy.app.handlers.load_post.remove(fileLoadHandler)

def writePidFileAtomic():
    """Write the process pid to a file
    os.replace is a cross-platform atomic operation
    """
    pid = os.getpid()
    tmpPidFilePath = f"{pidFilePath}-{pid}"
    with open(tmpPidFilePath, "w") as tmpPidFile:
        tmpPidFile.write(str(pid))
        tmpPidFile.flush()
        os.fsync(tmpPidFile.fileno())
    os.replace(tmpPidFilePath, pidFilePath)

def readPidFile():
    """Read a pid from the designated file

    Since this is not important data, it's ok to silently
      fail if the data cannot be read. 
    """
    try:
        with open(pidFilePath, 'r') as pidFile:
            storedPid = int(pidFile.read())
    except OSError:
        return None
    except ValueError:
        return None
    return storedPid

def removePidFile():
    try:
        os.remove(pidFilePath)
    except OSError:
        pass

@bpy.app.handlers.persistent
def writePidHandler(*args):
    writePidFileAtomic()

@bpy.app.handlers.persistent
def startRenderJobHandler(*args):
    """Run when Blender enters Rendering mode"""
    global renderContext
    renderContext = RenderInfo()

@bpy.app.handlers.persistent
def endRenderJobHandler(*args):
    """Run when Blender exits Rendering mode"""
    global renderContext
    renderContext = None

@bpy.app.handlers.persistent
def postRenderHandler(*args):
    """Run when Blender finishes rendering a frame"""
    global renderContext
    renderContext.renderedFrames += 1

@bpy.app.handlers.persistent
def fileLoadHandler(*args):
    """Run when Blender loads a .blend file"""
    global startTime
    startTime = time.time()
    
def updatePresenceTimer():
    updatePresence()
    return 30.0

def updatePresence():
    """Send data to Discord

    This is the heart of this program, all other functions are 
      gathering data for this function.

    Since this needs to compete with other Blender instances,
      check the current pid in the file, and write if there is 
      nothing there. If other instances delete this file,
      just write this process's pid and continue.

    ------------------------------
    |   ________                 |
    |  |        |  Blender       |
    |  | (Icon) |  (details)     |
    |  |        |  (state)       |
    |  |________|  (startTime)   |
    |                            |
    ------------------------------
    """
    # Pre-Checks
    readPid = readPidFile()
    if readPid is None:
        writePidFileAtomic()
    elif readPid != os.getpid():
        rpcConn.clear()
        return
    
    # Addon Preferences
    prefs = bpy.context.preferences.addons[__name__].preferences

    # Details and State
    if renderContext:
        # Rendering Details (prefs)
        if prefs.renderingDisplay == "DISPLAYFILENAME" and getFileName():
            activityDescription = f"Rendering {getFileName()}"
        else:
            activityDescription = f"Rendering in {getRenderEngineStr()}"
        # Rendering State
        if renderContext.isAnimation:
            frameRange = getFrameRange()
            activityState = f"Frame {frameRange[0]} of {frameRange[1]}"
        else:
            activityState = "Single Frame"
    else:
        # Details
        activityDescription = "Editing a project"
        # State
        activityState = getFileName()
        if not activityState:
            activityDescription = "Editing an unsaved file"

    # Start Time (prefs)
    if prefs.displayTime and not renderContext:
        fStartTime = startTime
    elif prefs.displayTimeRendering and renderContext:
        fStartTime = renderContext.startTime
    else:
        fStartTime = None

    # Large Icon
    largeIcon = iconBlender
    largeIconText = getVersionStr()

    rpcConn.update(
        pid=os.getpid(),
        start=fStartTime,
        state=activityState,
        details=activityDescription,
        large_image=largeIcon,
        large_text=largeIconText,
    )

def getFileName():
    """Name of this .blend file
    If this is an unsaved file, return None
    """
    name = bpy.path.display_name_from_filepath(bpy.data.filepath)
    if name == "":
        return None
    return name

def getVersionStr():
    """Easy-to-read Blender version"""
    verTup = bpy.app.version
    verChar = bpy.app.version_char
    verCycle = {
        "release": "Release",
        "rc": "Release Candidate",
        "beta": "Beta",
        "alpha": "Alpha"
    }.get(bpy.app.version_cycle, "")
    return f"{verTup[0]}.{verTup[1]}{verChar} {verCycle}"

def getRenderEngineStr():
    """Selected render engine"""
    internalName = bpy.context.engine
    internalNameStripped = internalName.replace("BLENDER_", "").replace("_", " ")
    return internalNameStripped.title()

def getFrameRange():
    """Current frame and total remaining frames"""
    start = bpy.context.scene.frame_start
    end = bpy.context.scene.frame_end
    cursor = bpy.context.scene.frame_current
    return (cursor - start + 1, end - start + 1)


class RpcPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    displayTime: bpy.props.BoolProperty(
        name="Elapsed Time",
        default=True,
    )

    displayTimeRendering: bpy.props.BoolProperty(
        name="Elapsed Time while Rendering",
        default=True,
    )

    renderingDisplay: bpy.props.EnumProperty(
        name="Show While Rendering",
        items=(
            ("DISPLAYENGINE", "Render Engine", "ex. Cycles"),
            ("DISPLAYFILENAME", "Filename", "This .blend file name"),
        ),
    )

    def draw(self, context):
        self.layout.prop(self, "displayTime")
        self.layout.prop(self, "displayTimeRendering")
        self.layout.prop(self, "renderingDisplay")