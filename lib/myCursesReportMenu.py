import curses

pad = None
screen = None


def runmenu(menu, parent):
    h = curses.color_pair(1)  # h is the coloring for a highlighted menu option
    n = curses.A_NORMAL  # n is the coloring for a non highlighted menu option

    # work out what text to display as the last menu option
    if parent is None:
        lastoption = "Done selecting graphs!"
    else:
        lastoption = "Back to menu '%s'" % parent['title']

    optioncount = len(menu['options'])  # how many options in this menu

    pos = 0  # pos is the zero-based index of the hightlighted menu option.  Every time runmenu is called, position returns to 0, when runmenu ends the position is returned and tells the program what option has been selected
    oldpos = None  # used to prevent the screen being redrawn every time
    x = None  # control for while loop, let's you scroll through options until return key is pressed then returns pos to program

    # Loop until return key is pressed
    while x != ord('\n'):
        if pos != oldpos or x == 112 or x == 114 or x == 116 or x == 119:
            oldpos = pos
            pad.clear()  # clears previous screen on key press and updates display based on pos
            pad.addstr(2, 2, menu['title'], curses.A_STANDOUT)  # Title for this menu
            pad.addstr(4, 2, menu['subtitle'], curses.A_BOLD)  # Subtitle for this menu

            # Display all the menu items, showing the 'pos' item highlighted
            for index in range(optioncount):
                textstyle = n
                if pos == index:
                    textstyle = h
                if 'graphid' in menu['options'][index]:
                    check = '[' + menu['options'][index]['selected'].replace("0", " ") + ']'
                    pad.addstr(5 + index, 4, "%-50s %s" % (menu['options'][index]['title'], check), textstyle)
                else:
                    pad.addstr(5 + index, 4, "%s" % menu['options'][index]['title'], textstyle)
            # Now display Exit/Return at bottom of menu
            textstyle = n
            if pos == optioncount:
                textstyle = h
            pad.addstr(5 + optioncount, 4, "%s" % lastoption, textstyle)
            y, x = screen.getmaxyx()
            coord = 0, 0, y - 1, x - 1
            if pos >= y - 8:
                pad.refresh(pos - (y - 9), 0, *coord)
            else:
                pad.refresh(0, 0, *coord)
            # finished updating screen

        try:
            x = pad.getch()  # Gets user input
        except KeyboardInterrupt:  # Catch CTRL-C
            x = 0
            pass

        # What is user input?
        if x == 258:  # down arrow
            if pos < optioncount:
                pos += 1
            else:
                pos = 0
        elif x == 259:  # up arrow
            if pos > 0:
                pos += -1
            else:
                pos = optioncount
        elif x == 112:  # p(erformance)
            if 'graphid' in menu['options'][pos]:
                if menu['options'][pos]['selected'] == 'p':
                    menu['options'][pos]['selected'] = '0'
                else:
                    menu['options'][pos]['selected'] = 'p'
            screen.refresh()
        elif x == 116:  # t(rend)
            if 'graphid' in menu['options'][pos]:
                if menu['options'][pos]['selected'] == 't':
                    menu['options'][pos]['selected'] = '0'
                else:
                    menu['options'][pos]['selected'] = 't'
            screen.refresh()
        elif x == 114:  # r (performance and trending)
            if 'graphid' in menu['options'][pos]:
                if menu['options'][pos]['selected'] == 'r':
                    menu['options'][pos]['selected'] = '0'
                else:
                    menu['options'][pos]['selected'] = 'r'
            screen.refresh()
        elif x == 119:  # w(ebcheck)
            if 'graphid' in menu['options'][pos]:
                if menu['options'][pos]['selected'] == 'w':
                    menu['options'][pos]['selected'] = '0'
                else:
                    menu['options'][pos]['selected'] = 'w'
            screen.refresh()
        elif x != ord('\n'):
            curses.flash()

    # return index of the selected item
    return pos


def processmenu(menu, parent=None):
    optioncount = len(menu['options'])
    exitmenu = False
    while not exitmenu:  # Loop until the user exits the menu
        try:
            getin = runmenu(menu, parent)
        except Exception as e:
            curses.endwin()
            print('Something went wrong')
            print('Error: %s' % e)
            raise
        if getin == optioncount:
            exitmenu = True
        elif menu['options'][getin]['type'] == 'MENU':
            processmenu(menu['options'][getin], menu)  # display the submenu


def doMenu(menu_data):
    global screen
    screen = curses.initscr()  # initializes a new window for capturing key presses
    curses.noecho()  # Disables automatic echoing of key presses (prevents program from input each key twice)
    curses.cbreak()  # Disables line buffering (runs each key as it is pressed rather than waiting for the return key to pressed)
    curses.start_color()  # Lets you use colors when highlighting selected menu option
    screen.keypad(1)  # Capture input from keypad

    # Change this to use different colors when highlighting
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Sets up color pair #1, it does black text with white background

    global pad
    pad = curses.newpad(200, 200)
    pad.keypad(1)

    processmenu(menu_data)
    curses.endwin()  # VITAL!  This closes out the menu system and returns you to the bash prompt.
