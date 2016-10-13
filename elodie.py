#!/usr/bin/env python

from __future__ import print_function
import os
import re
import sys
from datetime import datetime

import click
from send2trash import send2trash

# Verify that external dependencies are present first, so the user gets a
# more user-friendly error instead of an ImportError traceback.
from elodie.dependencies import verify_dependencies
if not verify_dependencies():
    sys.exit(1)

from elodie import constants
from elodie import geolocation
from elodie.media.base import Base
from elodie.media.media import Media
from elodie.media.text import Text
from elodie.media.audio import Audio
from elodie.media.photo import Photo
from elodie.media.video import Video
from elodie.filesystem import FileSystem
from elodie.localstorage import Db


DB = Db()
FILESYSTEM = FileSystem()


def import_file(_file, destination, album_from_folder, trash, allow_duplicates,
                from_gui=False, mode='normal', file_path = []):
    """Set file metadata and move it to destination.
        param: mode str : one of 'normal', 'get_path' or 'place_file'
                          'normal' - normal file process
                          'get_path' - only get destination path without copying
                          'place_file'- copy file to the destination
        param: file_path [str] : file path for place_file mode
                                [date, location, file_name]
    """

    if not os.path.exists(_file):
        if constants.debug:
            print('Could not find %s' % _file)
        print('{"source":"%s", "error_msg":"Could not find %s"}' % \
            (_file, _file))
        return

    media = Media.get_class_by_file(_file, [Text, Audio, Photo, Video])
    if not media:
        if constants.debug:
            print('Not a supported file (%s)' % _file)
        print('{"source":"%s", "error_msg":"Not a supported file"}' % _file)
        return

    if media.__name__ == 'Video':
        FILESYSTEM.set_date_from_path_video(media)

    if album_from_folder:
        media.set_album_from_folder()

    dest_path = FILESYSTEM.process_file(_file, destination,
        media, allowDuplicate=allow_duplicates, move=False,
        mode=mode, file_path=file_path)

    if mode == 'get_path':
        if from_gui:
            print('path=%s'%dest_path[1])
        return dest_path
    else:
        if dest_path:
            print('%s -> %s' % (_file, dest_path[0]))
        if trash:
            send2trash(_file)

        return dest_path[0] if dest_path else None

def confirm_place(file_path, default=None):
    """
    param: {'destination':destination,'date':date,'location':location,
            'file_name':file_name,'aliases':[aliases]}
    returns: {'destination':destination,'date':date,'location':location,
            'file_name':file_name,'aliases':[aliases]}
    """
    if not default:
        default = {'num':'1'}
        default['alias'] = file_path['aliases'][0] if file_path['aliases'] else None

    dest_path = os.path.join(file_path['destination'],
                             file_path['date'],
                             file_path['location'],
                             file_path['file_name'])
    options = ['','1','2','3']
    while True:
        print('Photo destinanation path is:')
        print('"%s"'%dest_path)
        print('Is it OK?')

        default_str = '(default)' if default['num'] == '1' else ''
        print("  1 - It's OK {}".format(default_str))

        default_str = '(default)' if default['num'] == '2' else ''
        print("  2 - Set Unknown Location {}".format(default_str))

        default_str = '(default)' if default['num'] == '3' else ''
        print("  3 - Enter new location {}".format(default_str))

        if default['alias']:
            default_str = '(default)' if default['num'] == '4' else ''
            options.append('4')
            print("  4 - Change location to '{}' {}".format(default['alias'],default_str))

        a = raw_input('? (Enter for default)')
        if a in options:
            break

    if a == '':
        a = default['num']
        location = file_path['location']

    if a == '1':
        print('Destination: %s'%dest_path)
        default['num'] = '1'
        location = file_path['location']
    elif a == '2':
        location = 'Unknown Location'
        default['num'] = '2'
    elif a == '3':
        if file_path['aliases']:
            print('Existing aliases for this location:')
            i = 1
            for e in file_path['aliases']:
                if e == file_path['aliases'][0]:
                    print('%d- %s" (default)'%(i,e))
                else:
                    print('%d- %s"'%(i,e))
                i+=1

        a = raw_input('? ("Enter" for default or type new location )')
        if a == '':
            location = file_path['aliases'][0]
        elif a in ('1','2','3','4','5'):
            location = file_path['aliases'][int(a)-1]
        else:
            location = a

        default['alias'] = location
        default['num'] = '4'
        if location in file_path['aliases']:
            i = file_path['aliases'].index(location)
            file_path['aliases'][0],file_path['aliases'][i] = location,file_path['aliases'][0]
        else:
            file_path['aliases'] = [location]+file_path['aliases']

    else:
        location = default['alias']
        default['num'] = '4'
        if location in file_path['aliases']:
            i = file_path['aliases'].index(location)
            file_path['aliases'][0],file_path['aliases'][i] = location,file_path['aliases'][0]
        else:
            file_path['aliases'] = [location]+file_path['aliases']

    file_path['new_location'] = location
    dest_path = os.path.join(file_path['destination'],
                             file_path['date'],
                             file_path['new_location'],
                             file_path['file_name'])
    #print('Destination: %s, aliases: %s'%(dest_path, file_path['aliases']))
    return file_path,default

@click.command('import')
@click.option('--destination', type=click.Path(file_okay=False),
              required=True, help='Copy imported files into this directory.')
@click.option('--source', type=click.Path(file_okay=False),
              help='Import files from this directory, if specified.')
@click.option('--file', type=click.Path(dir_okay=False),
              help='Import this file, if specified.')
@click.option('--album-from-folder', default=False, is_flag=True,
              help="Use images' folders as their album names.")
@click.option('--trash', default=False, is_flag=True,
              help='After copying files, move the old files to the trash.')
@click.option('--allow-duplicates', default=False, is_flag=True,
              help='Import the file even if it\'s already been imported.')
@click.option('--confirm-location', default=False, is_flag=True,
              help='Confirm or change location name.')
@click.argument('paths', nargs=-1, type=click.Path())
def _import(destination, source, file, album_from_folder, trash, paths, allow_duplicates,
            confirm_location):
    """Import files or directories by reading their EXIF and organizing them accordingly.
    """
    destination = os.path.expanduser(destination)

    files = set()
    paths = set(paths)
    if source:
        paths.add(source)
    if file:
        paths.add(file)
    for path in paths:
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            files.update(FILESYSTEM.get_all_files(path, None))
        else:
            files.add(path)

    defaults = None
    for current_file in files:
        if confirm_location:
            import_out = import_file(current_file, destination, album_from_folder,
                                      trash, allow_duplicates, mode='get_path')
            if import_out:
                file_path_mod,defaults = confirm_place(import_out[1],defaults)
                import_file(current_file, destination, album_from_folder,
                            trash, allow_duplicates, mode='place_file',
                            file_path=file_path_mod)
        else:
            import_file(current_file, destination, album_from_folder,
                        trash, allow_duplicates, mode='normal')



def update_location(media, file_path, location_name):
    """Update location exif metadata of media.
    """
    location_coords = geolocation.coordinates_by_name(location_name)

    if location_coords and 'latitude' in location_coords and \
            'longitude' in location_coords:
        location_status = media.set_location(location_coords[
            'latitude'], location_coords['longitude'])
        if not location_status:
            if constants.debug:
                print('Failed to update location')
            print(('{"source":"%s",' % file_path,
                '"error_msg":"Failed to update location"}'))
            sys.exit(1)
    return True


def update_time(media, file_path, time_string):
    """Update time exif metadata of media.
    """
    time_format = '%Y-%m-%d %H:%M:%S'
    if re.match(r'^\d{4}-\d{2}-\d{2}$', time_string):
        time_string = '%s 00:00:00' % time_string
    elif re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\d{2}$', time_string):
        msg = ('Invalid time format. Use YYYY-mm-dd hh:ii:ss or YYYY-mm-dd')
        if constants.debug:
            print(msg)
        print('{"source":"%s", "error_msg":"%s"}' % (file_path, msg))
        sys.exit(1)

    time = datetime.strptime(time_string, time_format)
    media.set_date_taken(time)
    return True


@click.command('update')
@click.option('--album', help='Update the image album.')
@click.option('--location', help=('Update the image location. Location '
                                  'should be the name of a place, like "Las '
                                  'Vegas, NV".'))
@click.option('--time', help=('Update the image time. Time should be in '
                              'YYYY-mm-dd hh:ii:ss or YYYY-mm-dd format.'))
@click.option('--title', help='Update the image title.')
@click.argument('files', nargs=-1, type=click.Path(dir_okay=False),
                required=True)
def _update(album, location, time, title, files):
    """Update a file's EXIF. Automatically modifies the file's location and file name accordingly.
    """
    for file_path in files:
        if not os.path.exists(file_path):
            if constants.debug:
                print('Could not find %s' % file_path)
            print('{"source":"%s", "error_msg":"Could not find %s"}' % \
                (file_path, file_path))
            continue

        file_path = os.path.expanduser(file_path)
        destination = os.path.expanduser(os.path.dirname(os.path.dirname(
                                         os.path.dirname(file_path))))

        media = Media.get_class_by_file(file_path, [Text, Audio, Photo, Video])
        if not media:
            continue

        updated = False
        if location:
            update_location(media, file_path, location)
            updated = True
        if time:
            update_time(media, file_path, time)
            updated = True
        if album:
            media.set_album(album)
            updated = True

        # Updating a title can be problematic when doing it 2+ times on a file.
        # You would end up with img_001.jpg -> img_001-first-title.jpg ->
        # img_001-first-title-second-title.jpg.
        # To resolve that we have to track the prior title (if there was one.
        # Then we massage the updated_media's metadata['base_name'] to remove
        # the old title.
        # Since FileSystem.get_file_name() relies on base_name it will properly
        #  rename the file by updating the title instead of appending it.
        remove_old_title_from_name = False
        if title:
            # We call get_metadata() to cache it before making any changes
            metadata = media.get_metadata()
            title_update_status = media.set_title(title)
            original_title = metadata['title']
            if title_update_status and original_title:
                # @TODO: We should move this to a shared method since
                # FileSystem.get_file_name() does it too.
                original_title = re.sub(r'\W+', '-', original_title.lower())
                original_base_name = metadata['base_name']
                remove_old_title_from_name = True
            updated = True

        if updated:
            updated_media = Media.get_class_by_file(file_path,
                                                    [Text, Audio, Photo, Video])
            # See comments above on why we have to do this when titles
            # get updated.
            if remove_old_title_from_name and len(original_title) > 0:
                updated_media.get_metadata()
                updated_media.set_metadata_basename(
                    original_base_name.replace('-%s' % original_title, ''))

            dest_path = FILESYSTEM.process_file(file_path, destination,
                updated_media, move=True, allowDuplicate=True)
            if constants.debug:
                print(u'%s -> %s' % (file_path, dest_path))
            print('{"source":"%s", "destination":"%s"}' % (file_path,
                dest_path))
            # If the folder we moved the file out of or its parent are empty
            # we delete it.
            FILESYSTEM.delete_directory_if_empty(os.path.dirname(file_path))
            FILESYSTEM.delete_directory_if_empty(
                os.path.dirname(os.path.dirname(file_path)))


@click.group()
def main():
    pass


main.add_command(_import)
main.add_command(_update)


if __name__ == '__main__':
    main()
