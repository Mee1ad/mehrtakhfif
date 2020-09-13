import boto3

from mehr_takhfif.settings_var import STORAGE_ACCESS_KEY, STORAGE_SECRET_KEY

access_key = STORAGE_ACCESS_KEY
secret_key = STORAGE_SECRET_KEY
endpoint = 'https://s3.ir-thr-at1.arvanstorage.com'
session = boto3.session.Session()

s3_client = session.client(
    service_name='s3',
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    endpoint_url=endpoint,
)

bucket_name = 'mtbackup'
upload_testfile = '/home/ubuntu/backup/done'


def list_buckets():
    response = s3_client.list_buckets()
    buckets = []
    for bucket in response['Buckets']:
        buckets.append(bucket["Name"])
    return buckets


# List of contents in bucket
def get_bucket_keys(bucket):
    """Get a list of keys in an S3 bucket."""
    keys = []
    resp = s3_client.list_objects_v2(Bucket=bucket)
    for obj in resp['Contents']:
        keys.append(obj['Key'])
    return keys


def upload_file(filename, bucket_name, name_in_bucket):
    s3_client.upload_file(filename, bucket_name, name_in_bucket)

# s3_client.generate_presigned_url('get_object', Params={'Bucket': 'newnew', 'Key': 'boyo.py-test'})

# s3_client.delete_object(Bucket='newnew', Key='s3-test2')
