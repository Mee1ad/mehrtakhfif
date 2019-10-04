from marshmallow import Schema, fields
from mehr_takhfif.settings import HOST, MEDIA_URL


class BaseSchema(Schema):

    def get_peyk(self, obj):
        if obj.peyk is not None:
            return PeykSchema().dump(obj.peyk)
        return None

    def get_mission(self, obj):
        if obj.mission is not None:
            return MissionSchema().dump(obj.mission)
        return None


class PeykSchema(Schema):
    class Meta:
        additional = ('id', 'phone', 'verified', 'vehicle')


class MissionSchema(BaseSchema):
    class Meta:
        additional = ('id', 'customer', 'phone', 'address', 'status')

    # peyk = fields.Method("get_peyk")
    # image = fields.Method("get_file")
    image = fields.Function(lambda o:"")

    def get_file(self, obj):
        return HOST + obj.image.url


class BoxLocation(BaseSchema):
    point = fields.Function(lambda o: (float(o.point[0]), float(o.point[1])))
    created_at = fields.DateTime()
    mission = fields.Method("get_mission")

