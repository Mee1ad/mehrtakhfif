from removebg import RemoveBg
from PIL import Image



# im = Image.open("1.CR2")
# rgb_im = im.convert('RGB')
# rgb_im.save('img.jpg')

sizes = {'thumbnail': (600, 372)}
#  soheilravasani@gmail.com - heraldo00@redtopgames.com - dacia94@redtopgames.com
api_keys = ['RNknKooBRiKS5BXEBZ5RcZf1', '7tctuRXzG9Z1pq95mDGrmNwt', 'sQNsATrrCYKTKey7wS6z9Wtq']

rmbg = RemoveBg("RNknKooBRiKS5BXEBZ5RcZf1", "error.log")
rmbg.remove_background_from_img_file("img.jpg")  # regular = 0.25 MP, hd = 4 MP, 4k = up to 10 MP
