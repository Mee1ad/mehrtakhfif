cloud_name = 'soheil'
api_key = '731441955578472'
api_secret = 'zzmHvzSyepsksrmdS6uUZxXprxg'
env_var = f'cloudinary://{api_key}:{api_secret}@{cloud_name}/'


def upload_code():
    cloudinary.uploader.upload("sample.jpg", crop="limit", tags="samples", width=3000, height=2000)


def image_manipulation():
    CloudinaryImage("sample").image(transformation={"crop": "fill", "gravity": "faces", "width": 300, "height": 200},
                                    format="jpg")
