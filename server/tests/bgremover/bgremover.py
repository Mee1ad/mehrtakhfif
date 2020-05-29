from removebg import RemoveBg
from PIL import Image
import requests
import logging
import os
import shutil
import pysnooper

API_ENDPOINT = "https://api.remove.bg/v1.0/removebg"
directory = None


class CostumeRemoveBg(RemoveBg):
    def __init__(self, api_key, error_log_file, directory):
        self.__api_key = api_key
        self.directory = directory
        logging.basicConfig(filename=error_log_file)

    def remove_background_from_img_file(self, img_file_path, size="regular"):
        """
        Removes the background given an image file and outputs the file as the original file name with "no_bg.png"
        appended to it.
        :param img_file_path: the path to the image file
        :param size: the size of the output image (regular = 0.25 MP, hd = 4 MP, 4k = up to 10 MP)
        """
        # Open image file to send information post request and send the post request
        img_file = open(img_file_path, 'rb')
        response = requests.post(
            API_ENDPOINT,
            files={'image_file': img_file},
            data={'size': size},
            headers={'X-Api-Key': self.__api_key})

        filename = get_filename_without_extension(img_file.name)
        self.__output_file__(response, self.directory + '\\' + filename + ".png")

        # Close original file
        img_file.close()


sizes = {'thumbnail': (600, 372), 'media': (1280, 794), 'category': (800, 500)}
# #  soheilravasani@gmail.com - heraldo00@redtopgames.com - dacia94@redtopgames.com
api_keys = ['RNknKooBRiKS5BXEBZ5RcZf1', '7tctuRXzG9Z1pq95mDGrmNwt', 'sQNsATrrCYKTKey7wS6z9Wtq']


def get_filename(file_path):
    return file_path[::-1].split('\\', 1)[0][::-1]


def get_filename_without_extension(file_path):
    return file_path[::-1].split('\\', 1)[0][::-1].split('.', 1)[0]


def crop(directory):
    files = os.listdir(directory + '\\jpg')[:1]
    rmbg = CostumeRemoveBg(api_keys[1], "error.log", directory + '\\media')
    for file in files:
        rmbg.remove_background_from_img_file(directory + '\\jpg\\' + file,
                                             size='4k')  # regular = 0.25 MP, hd = 4 MP, 4k = up to 10 MP


def make_thumbnail(directory):
    input_directory = directory + '\\media'
    files = os.listdir(input_directory)
    output_directory = directory + '\\thumbnail'
    for file in files:
        with Image.open(input_directory + '\\' + file) as img:
            width, height = sizes['thumbnail']
            img = img.resize((width, height), Image.ANTIALIAS)
            img.save(output_directory + file)


def reduce_image_quality(files, directory):
    for file in files:
        file = directory + '\\images\\' + file
        name = get_filename_without_extension(file)
        im = Image.open(file)
        rgb_im = im.convert('RGB')
        rgb_im.save(directory + '\\jpg\\' + name + '.jpg')


def make_folders(directory):
    try:
        os.mkdir(directory + '\\images')
        quit()
    except Exception:
        pass
    try:
        shutil.rmtree(directory + '\\jpg')
        os.mkdir(directory + '\\jpg')
    except FileNotFoundError:
        os.mkdir(directory + '\\jpg')
    try:
        shutil.rmtree(directory + '\\media')
        os.mkdir(directory + '\\media')
    except FileNotFoundError:
        os.mkdir(directory + '\\media')
    try:
        shutil.rmtree(directory + '\\thumbnail')
        os.mkdir(directory + '\\thumbnail')
    except FileNotFoundError:
        os.mkdir(directory + '\\thumbnail')


if __name__ == '__main__':
    directory = os.getcwd()
    make_folders(directory)
    files = os.listdir(directory + '\\images')
    reduce_image_quality(files, directory)
    crop(directory)
    make_thumbnail(directory)
