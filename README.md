
# Installation:
In this page:
- The green `<> Code` button at the top of the page -> `Download Zip`

In Blender:
- Go to `Edit` > `Preferences`
- Go to the `Add-ons` tab
- Click `Install...` in the top-right of the window
- Select the `AutoMDL-main.zip`, then click `Install Add-on`
- Enable the checkbox to the left of the addon name

<br />    

# Fast iteration thanks to Hammer++'s hotloading ability:

<img src="https://cdn.discordapp.com/attachments/1131362438227431428/1236395804013494414/automdl_showcase.gif?ex=6637dad2&is=66368952&hm=a88cf810cc26153735a8a61439ee54dc1736b43c5bf9b169d2c4cc1602cfa3cd&" width="850"/>

<br />

# Simplify workflow, as if the engine reads .blend files:

![compiling_showcase](https://github.com/NvC-DmN-CH/AutoMDL/assets/56874047/08823113-c867-47f7-a8df-f83e307508d4)

---

# Where the addon appears:
The AutoMDL tab will appear in the Sidebar (press N)


<br />

# How to use:

- Save .blend file anywhere in `models`

- Select a visual mesh and hit `Update MDL`


![e](https://github.com/NvC-DmN-CH/AutoMDL/assets/56874047/a3b37051-b459-4b11-a4c1-29990f4305c9)

<br />

By default, the materials search path mirrors the blend path:

- if blend is `models/c17/post.blend`
- mdl compiles at `models/c17/post.mdl`
- engine will look for materials in `materials/models/c17/`

Lists exactly where the VMTs are expected:

![image](https://github.com/NvC-DmN-CH/AutoMDL/assets/56874047/a7fc3ac1-bd89-43dd-b2e6-a8ac54b2c22c)

(the model has 1 material called `metal`)

<br />

<br />

You can also define a different search path if needed (or multiple):

![image](https://github.com/NvC-DmN-CH/AutoMDL/assets/56874047/426fa106-a894-4d1e-90b6-0ec98f02fc13)


---


## Misc:
- It's fine to compile without a collision model
- Automatically detects whether the collision is $concave or not, and counts loose parts to set the correct amount of $maxconvexpieces
- Should automatically detect all source engine games installed in steam, and put them in the dropdown to easily choose a compiler from. But if that detection fails it will prompt you to manually input the path to a bin folder containing studiomdl.exe
- For convenience, it also makes the appropriate folders and placeholder VMTs if they don't exist, this can be disabled in the addon preferences

<br />

## Todo:
<sub>This is my first addon and my first time coding in python so the code is so so bad</sup>

- I couldn't figure out how to add linux support
- Currently exporting freezes the UI because it waits for studiomdl.exe to finish
- No support for skins, bodygroups, lods, or anything else yet really

<br />

## Note
- I made this for environment props in mind, for now anything else is beyond the scope of this addon, sorry!

Hopefully this addon inspires change in other more sophisticated tools to do things in a similar way
