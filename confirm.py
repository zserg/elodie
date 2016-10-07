import os

def confirm_place(file_path):
    """
    param: ([dest,date,location,name], [aliases])
    returns: ([dest,date,location,name], [aliases])
    """
    dest_path = os.path.join(*file_path[0])
    aliases = file_path[1]

    while True:
        print('Photo destinanation path is:')
        print('"%s"'%dest_path)
        print('Is it OK?')
        print("  1 - It's OK (default)")
        print("  2 - Set Unknown Location")
        print("  3 - Change location")
        a = raw_input('? (Enter for default)')
        if a in ('', '1', '2', '3'):
            break

    if a == '' or a == '1':
        print('Destination: %s'%dest_path)
    else:
        if a == '2':
            location = 'Unknown Location'
        else:
            print('Existing aliases for this location:')
            for e in aliases:
                if e == aliases[0]:
                    print('"%s" (default)'%e)
                else:
                    print('"%s"'%e)
            a = raw_input('? (Enter for default)')
            if a == '':
                location = aliases[0]
            else:
                location = a
                if a in aliases:
                    i = aliases.index(a)
                    aliases[0],aliases[i] = a,aliases[0]
                else:
                    aliases = [a]+aliases

        file_path[0][2] = location
        dest_path = os.path.join(*file_path[0])
        print('Destination: %s, aliases: %s'%(dest_path, aliases))







file_path = (['/tmp','2015','Moscow','file.jpg'], ['Nice place', 'Home'])

confirm_place(file_path)
