# Mem Manip Beginner Tutorial
_This tutorial is intended to teach basic usage  or Mem Manip.  It will demonstrate how to find a value in memory, change it and freeze that value._

The game that we will use in this tutorial is [_Terraria_](https://store.steampowered.com/app/105600/Terraria/).  We will use Mem Manip to search for character life and freeze that life so that the character cannot die.

If you do not  own _Terraria_, you can still follow along and learn how Mem Manip works.

## Finding the code for life
1. Start Mem Manip.  If Mem Manip is installed as a service, it is already running.
2. Run _Terraria_ and start a game.
3. Open your browser to Mem Manip.  I have Mem Manip running on my PC at `http://192.168.1.3:5000.`  If Mem Manip is installed on a Steam Deck, you may find it at `http://steamdeck:5000`
4. Tap on the Search item on the toolbar.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/search_toolbar.jpg" alt="search_toolbar" width="500"/>

5. This is your Search tool.  The first thing we need to do is open the _Terraria_ process.  Click on the dropdown and select the correct process.  On my PC that is `Terraria.exe`
6. Next, you are presented with several search options:

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/search_process.jpg" alt="search_process" width="500"/>

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

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/in_game01.jpg" alt="ingame01" width="700"/>

8. In Mem Manip, select Search Type `EQUAL TO`, Search Size `4 BYTES` and Value `100` then click `SEARCH`
9. Mem Manip should process a search and return all addresses with values of 100.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/search_results.jpg" alt="search_results" width="500"/>

10. Next, we have to filter those addresses further so that we can find our code.  To do this we must change our life points in the game.  Do this now.
11. _Ouch_, I lost some life points.  Now my life points are at 96.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/in_game02.jpg" alt="ingame02" width="700"/>

12. Back in Mem Manip, we will modify our value from 100 to 96 (which is our current life points.)  Click `SEARCH` again.
13. For me, this narrowed my list of possible codes to 2.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/search_round2.jpg" alt="search_round2" width="500"/>

At this point we can run steps 10-13 again to narrow the list to one result, or we can just lose some life again in the game and monitor our search result list in Mem Manip to see which result reflects the life point change.

I'll do the  later.
14. I lost some more life.  Now I'm down to 84 life points.  If I look at my result list, I can see on item updated to 87.  This will be the item I want.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/search_next.jpg" alt="search_next" width="500"/>

15. You've successfully found the value you want to modify!
## Adding your value to the code list 
Now that you found the value that you want to modify, we need to place that address on the code list.

1. While still on the Search screen, press the `COPY` button next to the result that we found.  That will copy the address of the value so that we can paste it in other areas of Mem Manip.
2. Navigate to the Codes section of Mem Manip.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/search_copy.jpg" alt="search_copy" width="500"/>

3. On this screen we will select the _Terraria_ process like we did in step 5 of our last tutorial.
4. After selecting the process, you are presented with a few options:

#### Load
This will load any previously saved code lists.
#### Save
This will save the current code list as whatever name you define.
#### Delete
This will delete the currently loaded code list.

You should also see a :heavy_plus_sign: floating button at the bottom right.  This button will manually add a code to your code list.

Finally, there also should be a clipboard floating button on the bottom right.  This button is visible if you've copied an item somewhere in Mem Manip.

5. Click on the clipboard button.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/code-list_paste.jpg" alt="code-list_paste" width="500"/>

This will paste the address that you've previously copied from the Search screen into your codelist.  You should then see the new code applied to your list.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/code-list_item.jpg" alt="code-list_item" width="500"/>

Other than the value itself, a code in the code list has a `Code Name` that can be changed, a `Code Menu`, and a `Freeze` toggle.

#### Code Name

This can be any descriptive name that you'd like. 

#### Freeze

Toggling this button will continuously write the value specified (freeze the value.) 

#### Code Menu

Clicking this will open a menu that will allow you to edit the code, make a copy of the code, or delete the code. 

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/code-list_menu.jpg" alt="code-list_menu" width="500"/>

###### Edit

This will bring up a dialog that allows you to change the address of the code.

###### Copy

This works just like the edit feature.  However, instead of changing the address of the code, it creates a new code instead.

###### Delete

This removes the selected code from the list.

_Lets get back_

6. Change the value of the code from 84 back to 100.  Pressing return or enter on the keyboard or phone touch screen should change that value in the game back to 100.
7. Click on the freeze toggle.  The value should not remain at 100.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/code-list_freeze.jpg" alt="code-list_freeze" width="500"/>

8. Return to _Terraria_ and verify that the life points are back to 100, and that taking damage will not decrease the value.

<img src="https://github.com/primetime00/memory_hack/raw/master/docs/tutorial/images/search/in_game03.jpg" alt="in_game03" width="700"/>

You should now have a valid code for the game!

The next tutorial will describe how to find a more permanent code as this code will change to another address on game restart.