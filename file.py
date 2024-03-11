import os
from tkinter import filedialog
import tkinter as tk
import sys

dirname = os.path.split(__file__)[0]

def _choose_dir() -> tuple[str, str]: 
	root = tk.Tk()
	root.withdraw()
	dir1 = filedialog.askdirectory(
		mustexist=True, initialdir='E:\CACHE\Hardcore-SK\Mods\Core_SK\Defs\CombatExtended\Ammo', title="Choose Folder"
	)
	dir2 = filedialog.askdirectory(
		mustexist=True, initialdir='D:\SteamLibrary\steamapps\common\RimWorld\Mods\CombatExtended\Defs\Ammo', title="Choose Folder"
	)
	if os.path.isdir(dir1) and os.path.isabs(dir1) and os.path.isdir(dir2) and os.path.isabs(dir2): 
		return (dir1, dir2)
	else:
		print('Invalid path!')
		sys.exit(-1)
	
def choose_files() -> tuple[str, str]:
	root = tk.Tk()
	root.withdraw()
	left = filedialog.askopenfilename(defaultextension="xml", initialdir=dirname)
	right = filedialog.askopenfilename(defaultextension="xml", initialdir=dirname)
	if left != right and os.path.isfile(left) and os.path.isfile(right):
		return (left, right)
	else:
		sys.exit(-1)