import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
    cloud_name="soheil",
    api_key="731441955578472",
    api_secret="zzmHvzSyepsksrmdS6uUZxXprxg")

api_endpoint = 'https://api.cloudinary.com/v1_1/soheil'

cloudinary.utils.cloudinary_url("sample.jpg",
                                width=100,
                                height=150,
                                crop="fill")
