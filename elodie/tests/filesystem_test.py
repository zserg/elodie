from __future__ import absolute_import
# Project imports
import os
import re
import shutil
import time
import sys
from datetime import datetime
from datetime import timedelta
from shutil import rmtree
import mock
from mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from . import helper
from elodie.filesystem import FileSystem
from elodie.media.media import Media
from elodie.media.photo import Photo
from elodie.media.video import Video
from nose.plugins.skip import SkipTest
from elodie import constants
from elodie import geolocation

os.environ['TZ'] = 'GMT'

class TestMy():
    def setup(self):
        """
        setup hash.json and location.json
        in current directory
        """
        constants.application_directory = 'dot.elodie'
        constants.hash_db = '{}/hash.json'.format(constants.application_directory)
        constants.location_db = '{}/location.json'.format(constants.application_directory)

        self.patcher = mock.patch('elodie.geolocation.requests.get')
        self.mock_get = self.patcher.start()
        mock_response = mock.Mock()
        mock_response.json.return_value = {'address':{'city':'Sunnyvale'}}

        self.mock_get.return_value = mock_response


    def teardown(self):
        self.patcher.stop()

        try:
            rmtree(constants.application_directory)
        except OSError:
            pass

    def test_create_directory_success(self):
        filesystem = FileSystem()
        folder = os.path.join(helper.temp_dir(), helper.random_string(10))
        status = filesystem.create_directory(folder)

        # Needs to be a subdirectory
        assert helper.temp_dir() != folder

        assert status == True
        assert os.path.isdir(folder) == True
        assert os.path.exists(folder) == True

        # Clean up
        shutil.rmtree(folder)


    def test_create_directory_recursive_success(self):
        filesystem = FileSystem()
        folder = os.path.join(helper.temp_dir(), helper.random_string(10), helper.random_string(10))
        status = filesystem.create_directory(folder)

        # Needs to be a subdirectory
        assert helper.temp_dir() != folder

        assert status == True
        assert os.path.isdir(folder) == True
        assert os.path.exists(folder) == True

        shutil.rmtree(folder)

    @mock.patch('elodie.filesystem.os.makedirs')
    def test_create_directory_invalid_permissions(self,mock_makedirs):
        if os.name == 'nt':
           raise SkipTest("It isn't implemented on Windows")

        # Mock the case where makedirs raises an OSError because the user does
        # not have permission to create the given directory.
        mock_makedirs.side_effect = OSError()

        filesystem = FileSystem()
        status = filesystem.create_directory('/apathwhichdoesnotexist/afolderwhichdoesnotexist')

        assert status == False

    def test_delete_directory_if_empty(self):
        filesystem = FileSystem()
        folder = os.path.join(helper.temp_dir(), helper.random_string(10))
        os.makedirs(folder)

        assert os.path.isdir(folder) == True
        assert os.path.exists(folder) == True

        filesystem.delete_directory_if_empty(folder)

        assert os.path.isdir(folder) == False
        assert os.path.exists(folder) == False

    def test_delete_directory_if_empty_when_not_empty(self):
        filesystem = FileSystem()
        folder = os.path.join(helper.temp_dir(), helper.random_string(10), helper.random_string(10))
        os.makedirs(folder)
        parent_folder = os.path.dirname(folder)

        assert os.path.isdir(folder) == True
        assert os.path.exists(folder) == True
        assert os.path.isdir(parent_folder) == True
        assert os.path.exists(parent_folder) == True

        filesystem.delete_directory_if_empty(parent_folder)

        assert os.path.isdir(folder) == True
        assert os.path.exists(folder) == True
        assert os.path.isdir(parent_folder) == True
        assert os.path.exists(parent_folder) == True

        shutil.rmtree(parent_folder)

    def test_get_all_files_success(self):
        filesystem = FileSystem()
        folder = helper.populate_folder(5)
        files = filesystem.get_all_files(folder)
        shutil.rmtree(folder)

        length = len(files)
        assert length == 5, length


    def test_get_all_files_by_extension(self):
        filesystem = FileSystem()
        folder = helper.populate_folder(5)

        files = filesystem.get_all_files(folder)
        length = len(files)
        assert length == 5, length

        files = filesystem.get_all_files(folder, 'jpg')
        length = len(files)
        assert length == 3, length

        files = filesystem.get_all_files(folder, 'txt')
        length = len(files)
        assert length == 2, length

        files = filesystem.get_all_files(folder, 'gif')
        length = len(files)
        assert length == 0, length

        shutil.rmtree(folder)

    def test_get_current_directory(self):
        filesystem = FileSystem()
        assert os.getcwd() == filesystem.get_current_directory()

    def test_get_file_name_plain(self):
        filesystem = FileSystem()
        media = Photo(helper.get_file('plain.jpg'))
        file_name = filesystem.get_file_name(media)

        assert file_name == helper.path_tz_fix('2015-12-05_00-59-26-plain.jpg'), file_name

    def test_get_file_name_with_title(self):
        filesystem = FileSystem()
        media = Photo(helper.get_file('with-title.jpg'))
        file_name = filesystem.get_file_name(media)

        assert file_name == helper.path_tz_fix('2015-12-05_00-59-26-with-title-some-title.jpg'), file_name

    def test_get_folder_name_by_date(self):
        filesystem = FileSystem()
        time_tuple = (2010, 4, 15, 1, 2, 3, 0, 0, 0)
        folder_name = filesystem.get_folder_name_by_date(time_tuple)

        assert folder_name == '2010-04-Apr', folder_name

        time_tuple = (2010, 9, 15, 1, 2, 3, 0, 0, 0)
        folder_name = filesystem.get_folder_name_by_date(time_tuple)

        assert folder_name == '2010-09-Sep', folder_name

    def test_get_folder_path_plain(self):
        filesystem = FileSystem()
        media = Photo(helper.get_file('plain.jpg'))
        path = filesystem.get_folder_path(media.get_metadata())

        assert path == os.path.join('2015-12-Dec','Unknown Location'), path

    def test_get_folder_path_with_title(self):
        filesystem = FileSystem()
        media = Photo(helper.get_file('with-title.jpg'))
        path = filesystem.get_folder_path(media.get_metadata())

        assert path == os.path.join('2015-12-Dec','Unknown Location'), path

    def test_get_folder_path_with_location(self):
        filesystem = FileSystem()
        media = Photo(helper.get_file('with-location.jpg'))
        path = filesystem.get_folder_path(media.get_metadata())

        assert path == os.path.join('2015-12-Dec','Sunnyvale'), path

    def test_get_folder_path_with_location_and_title(self):
        filesystem = FileSystem()
        media = Photo(helper.get_file('with-location-and-title.jpg'))
        path = filesystem.get_folder_path(media.get_metadata())

        assert path == os.path.join('2015-12-Dec','Sunnyvale'), path

    def test_process_file_invalid(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'photo.jpg')
        shutil.copyfile(helper.get_file('invalid.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        assert destination is None

    def test_process_file_plain(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'photo.jpg')
        shutil.copyfile(helper.get_file('plain.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        origin_checksum = helper.checksum(origin)
        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum == destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-12-Dec','Unknown Location','2015-12-05_00-59-26-photo.jpg')) in destination, destination

    def test_process_file_with_title(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = '%s/photo.jpg' % folder
        shutil.copyfile(helper.get_file('with-title.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        origin_checksum = helper.checksum(origin)
        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum == destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-12-Dec','Unknown Location','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

    def test_process_file_with_location(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'photo.jpg')
        shutil.copyfile(helper.get_file('with-location.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        origin_checksum = helper.checksum(origin)
        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum == destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-12-Dec','Sunnyvale','2015-12-05_00-59-26-photo.jpg')) in destination, destination

    def test_process_file_with_location_and_title(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'photo.jpg')
        shutil.copyfile(helper.get_file('with-location-and-title.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        origin_checksum = helper.checksum(origin)
        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum == destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-12-Dec','Sunnyvale','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

    def test_process_file_with_album(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'photo.jpg')
        shutil.copyfile(helper.get_file('with-album.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        origin_checksum = helper.checksum(origin)
        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum == destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-12-Dec','Test Album','2015-12-05_00-59-26-photo.jpg')) in destination, destination

    def test_process_file_with_album_and_title(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'photo.jpg')
        shutil.copyfile(helper.get_file('with-album-and-title.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        origin_checksum = helper.checksum(origin)
        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum == destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-12-Dec','Test Album','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

    def test_process_file_with_album_and_title_and_location(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'photo.jpg')
        shutil.copyfile(helper.get_file('with-album-and-title-and-location.jpg'), origin)

        media = Photo(origin)
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        origin_checksum = helper.checksum(origin)
        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum == destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-12-Dec','Test Album','2015-12-05_00-59-26-photo-some-title.jpg')) in destination, destination

    # gh-89 (setting album then title reverts album)
    def test_process_video_with_album_then_title(self):
        filesystem = FileSystem()
        temporary_folder, folder = helper.create_working_folder()

        origin = os.path.join(folder,'movie.mov')
        shutil.copyfile(helper.get_file('video.mov'), origin)

        origin_checksum = helper.checksum(origin)

        media = Video(origin)
        media.set_album('test_album')
        media.set_title('test_title')
        destination = filesystem.process_file(origin, temporary_folder, media, allowDuplicate=True)

        destination_checksum = helper.checksum(destination)

        shutil.rmtree(folder)
        shutil.rmtree(os.path.dirname(os.path.dirname(destination)))

        assert origin_checksum is not None, origin_checksum
        assert origin_checksum != destination_checksum, destination_checksum
        assert helper.path_tz_fix(os.path.join('2015-01-Jan','test_album','2015-01-19_12-45-11-movie-test_title.mov')) in destination, destination
