from removebg import RemoveBg


# rawData = open("foo.raw" 'rb').read()
# imgSize = (x,y)
# img = Image.fromstring('L', imgSize, rawData, 'raw', 'F;16')
# img.save("foo.png")


# import rawpy
# import imageio
#
# raw = rawpy.imread('image.nef')
# rgb = raw.postprocess()
# imageio.imsave('default.tiff', rgb)


# from PIL import Image
#
# im = Image.open("1.CR2")
# rgb_im = im.convert('RGB')
# rgb_im.save('img.jpg')

sizes = {'thumbnail': (600, 372)}
api_keys = ['RNknKooBRiKS5BXEBZ5RcZf1', ]

rmbg = RemoveBg("RNknKooBRiKS5BXEBZ5RcZf1", "error.log")
rmbg.remove_background_from_img_file("img.jpg")
