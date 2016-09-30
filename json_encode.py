import ipaddress
import json


class AppJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ipaddress.IPv4Address):
            return str(obj)

        if getattr(obj, "to_json", None):
            json = obj.to_json()
            if json:
                return json

        return json.JSONEncoder.default(self, obj)