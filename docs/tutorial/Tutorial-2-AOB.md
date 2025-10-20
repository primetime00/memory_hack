# Memory Hack Tutorial 2 — AOB (Array-of-Bytes)
_This tutorial shows when and how to use AOBs to make codes resilient across restarts/levels by matching a stable byte pattern near your value._

We'll use Terraria as an example again, like in the [search tutorial.](https://github.com/isighless/memory_hack/raw/aob_documentation/docs/tutorial/Tutorial-1-search.md)

## When to use AOB
AOB is useful because usually the addresses you find with an address search will no longer be valid after the game restarts or sometimes even for things in the game like respawning or switching levels.
The goal with AOB is to not have to search for the addresses you are interested in every time something changes.
You use the AOB page to find a unique byte pattern in memory and use an offset from that pattern to compute your target address at runtime. This often survives restarts and level loads because the pattern is stable even when the exact address changes.

## Overview
An AOB search is more complex than the address search from tutorial 1, so for this tutorial we'll break it into 3 phases:
- Phase 1: Capture memory around the current address
- Phase 2: Compare with a new address to produce AOB candidates
- Phase 3: Refine candidates


---

## Phase 1: Find the value and capture memory
1. Use the [search tutorial](https://github.com/isighless/memory_hack/raw/aob_documentation/docs/tutorial/Tutorial-1-search.md) to locate your value in-game (e.g., Terraria health). Copy the address from the Search results.
2. Go to the AOB tab.
3. Select your game process (e.g., Terraria.exe).
4. Type a Name for this AOB set (e.g., Terraria-HP).
5. Search Type: Address.
6. Address/Value: paste the address from Search.
7. Range: leave the default of 65536 unless you have a reason to change it.
8. Repeat: Leave this toggled off for phase 1.
9. Click Search. This reads a snapshot of memory around your address and writes a .aob file under your home folder at memory_hack/.aob.
10. Move on to phase 2.

<img src="https://github.com/isighless/memory_hack/raw/aob_documentation/docs/tutorial/images/aob/aob_phase_1.png" alt="aob_phase_1" width="500"/>

---

## Phase 2: Generate AOB candidates after the address moves
1. Restart the game to invalidate the address you found in phase 1.
2. Use the Search tab to find the new address of the same value.
4. Return to the AOB tab.
5. From the dropdown, select the Name you created earlier (e.g., Terraria-HP). This loads the existing .aob file.
6. Search Type: Address.
7. Address/Value: paste the new address of your value.
8. Click Search. Memory Hack compares the new capture to your saved one and generates candidate AOB patterns. Each result shows:
   - Offset: the hex offset from the pattern's base to your value.
   - AOB: the pattern itself (bytes separated by spaces; ?? means wildcard).

<img src="https://github.com/isighless/memory_hack/raw/aob_documentation/docs/tutorial/images/aob/aob_phase_2.png" alt="aob_phase_2" width="500"/>

Notes
- If you get “No Results,” the memory around the two captures may not overlap enough. Try a larger range in Phase 1 or make sure both addresses are in comparable regions (e.g., after the game is fully loaded). 
- You can repeat this entire phase multiple times with different addresses to reduce the number of candidates you need to look through in phase 3.

---

## Phase 3: Refine candidates
1. Go through the list of AOBs from phase 2 and click **COUNT** on each one. Your goal is to find a pattern with a low count, ideally 1. If you find one, skip to step 3.
_Deleting candidates with a high count may save you time later if you don't luck across a good hit early._

<img src="https://github.com/isighless/memory_hack/raw/aob_documentation/docs/tutorial/images/aob/aob_count.png" alt="aob_count" width="500"/>

2. If the list is too long to go through manually, you can repeat phase 2, or you can try a value search to narrow results. The screenshot above shows a value search.

3. If you find a candidate with a count of one, hit the copy button on it and switch to the codes tab.

4. Click the clipboard button at the bottom right to add the candidate you found to the code list. It will appear on the list just like the value you find in an address search unless you hit the arrow to expand the entry:

<img src="https://github.com/isighless/memory_hack/raw/aob_documentation/docs/tutorial/images/aob/codelist_paste_aob.png" alt="codelist_paste_aob" width="500"/>

5. Make sure to set the type to the type you were searching for. (4 Bytes in the case above)

6. Save your list and test if it's still showing the correct value after restarting the game. Usually it will be, but if it's not, you will need to keep searching the AOBs until you find a candidate that does.

Good luck!



