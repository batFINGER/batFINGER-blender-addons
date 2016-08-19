---
<img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/anim.gif"  width="100%" height="150" padding="10" align="center" >
<h1 padding="10">Sound Drivers</h1>
**Blender Addon Drive animation with sound**

[install](#install)
[bake](#bake)
[normalize](#normalize)
[visualize](#visualize)
[midi](#midi)
---

---
**Install the Addon<a name="install"></a>**

---

Open the zip file from github in your favourite archive program.  Move the `sound_drivers` folder into your blender  "scripts/addons/folder"

<a href="https://github.com/batFINGER/sound-bake-drivers/wiki/images/install_addon.png"><img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/install_addon.png" height="200" ></a>

---
**Bake to multiple frequencies<a name="bake"></a>**

---

Only need to select the start and end frequencies to bake across a range.  By default bakes to 16 channels from 1 to 40,000 Hz (the audible spectrum) using a log base.  
<a href="https://github.com/batFINGER/sound-bake-drivers/wiki/images/bake.png"><img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/bake.png" height="200" ></a>

---
**Normalize Actions<a name="normalize"></a>**

---

Automatically makes the range of the action [0, 1] after baking using fcurve modifiers.  Setting normalize type to `CHANNEL` will normalize each channel from its min, max to [0, 1], or whatever range you choose.  Reverse ranges will invert the fcurves

<a href="https://github.com/batFINGER/sound-bake-drivers/wiki/images/normalize.png"><img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/normalize.png" height="200" ></a>



---
**UI Visualise with BGL<a name="visualize"></a>**

---

Display a visualiser using properties in the UI or with a BGL overlay on the UI. 

<a href="https://github.com/batFINGER/sound-bake-drivers/wiki/images/visualizer.png"><img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/visualizer.png" height="200" ></a>


---
**Make Visualisers Quickly<a name="visualize"></a>**

---

Create and drive an object or set of objects with channel 0 of a sound bake, and the automatically produce a grid of objects, each driven by the corresponding channel.


<a href="https://github.com/batFINGER/sound-bake-drivers/wiki/images/visquick.png"><img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/visquick.png" height="200" ></a>

<span text-size="-1" margin="0" padding="0">
_Default Cylinder, array modifier with count driven by channel 0 of AA bake._
</span>

---
**MIDI file support<a name="midi"></a>**

---

<a href="https://github.com/batFINGER/sound-bake-drivers/wiki/images/install_addon.png"><img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/midi_icon.png" align="left" height="40" ></a> Bake a corresponding  midi file to fcurves.  Not sure what instrument is making that sound, well with an associated midi bake we can tell.


<a href="https://github.com/batFINGER/sound-bake-drivers/wiki/images/midi2.png"><img src="https://github.com/batFINGER/sound-bake-drivers/wiki/images/midi2.png" height="200" ></a> 


# mocap-madness
Extended tools for bvh mocap files.
Still very much in testing.
Multiple file import
One rig with multiple actions.
Rig only
Action only
Rescale action to rig
Use CMU names if applicable
Change rest pose.
Pose matching : make cycle animations or branch to others.

