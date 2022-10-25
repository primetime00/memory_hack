# Mem Manip Beginner Tutorial
_This tutorial is intended to teach basic usage  or Mem Manip.  It will demonstrate how to find a value in memory, change it and freeze that value._

The game that we will use in this tutorial is [_Terraria_](https://store.steampowered.com/app/105600/Terraria/).  We will use Mem Manip to search for character life and freeze that life so that the character cannot die.

If you do not  own _Terraria_, you can still follow along and learn how Mem Manip works.

## Finding the code for life
1. Start Mem Manip.  If Mem Manip is installed as a service, it is already running.
2. Run _Terraria_ and start a game.
3. Open your browser to Mem Manip.  I have Mem Manip running on my PC at `http://192.168.1.3:5000.`  If Mem Manip is installed on a Steam Deck, you may find it at `http://steamdeck:5000`
4. Tap on the Search item on the toolbar.
5. This is your Search tool.  The first thing we need to do is open the _Terraria_ process.  Click on the dropdown and select the correct process.  On my PC that is `Terraria.exe`
6. Next, you are presented with several search options:
#### Search Type
This option determines how the search will happen.  Initially, the options are `EQUAL TO`, `GREATER THAN`, `LESS THAN`, `UNKNOWN`, and `UNKNOWN NEAR`

- `EQUAL TO` Searches for all values that are exactly the value specified.
- `GREATER THAN` Searches for all values that higher or more than the value specified.
- `LESS THAN` Searches for all values that lower or less than the value specified.
- `UNKNOWN` Captures a snapshot of memory to compare with later searches.  This is used for unknown values (life bars)
- `UNKNOWN NEAR` Same as `UNKNOWN`, but only captures a small amount of memory around a specified address.
#### Search Size
This option defines how the values that you are searching for are stored.  The options are `BYTE`, `2 BYTES`, `4 BYTES`, `FLOAT`, and `ARRAY`
- `BYTE` Values in  the range of 0-255 or -128-127.
- `2 BYTES` Values in  the range of 0-65535 or --32768-32767.
- `4 BYTES` Values in  the range of 0-4294967295 or -2147483648-2147483647.
- `FLOAT` Values that are fractions (1.5, 6.25, etc...)
- `ARRAY` An array of hexidecimal bytes seperated by spaces (01 02 0A FF)

Generally if your value can fall within a range specified above, use that search size.
#### Value / Address
This is the value or address that will be used in the search selected above.  Options `EQUAL TO`, `GREATER THAN`, and `LESS THAN` will utilize this value.  Option `UKNOWN NEAR` will use this field as the hexidecimal address to search around.

_Now back to the tutorial_
7. In _Terraria_  examine your life points.  Since I started a new game, I have 100.
8. In Mem Manip, select Search Type `EQUAL TO`, Search Size `4 BYTES` and Value `100` then click `SEARCH`
9. Mem Manip should process a search and return all addresses with values of 100.
10. Next, we have to filter those addresses further so that we can find our code.  To do this we must change our life points in the game.  Do this now.
11. _Ouch_, I lost some life points.  Now my life points are at 94.
12. Back in Mem Manip, we will modify our value from 100 to 94 (which is our current life points.)  Click `SEARCH` again.
13. For me, this narrowed my list of possible codes to 2.

At this point we can run steps 10-13 again to narrow the list to one result, or we can just lose some life again in the game and monitor our search result list in Mem Manip to see which result reflects the life point change.

I'll do the  later.
14. I lost some more life.  Now I'm down to 87 life points.  If I look at my result list, I can see on item updated to 87.  This will be the item I want.
15. You've successfully found the value you want to modify!
## Adding your value to the code list 
Now that you found the value that you want to modify, we need to place that address on the code list.