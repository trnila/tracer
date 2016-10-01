import ipaddress
import json


class AppJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ipaddress.IPv4Address):
            return str(obj)
        elif isinstance(obj, ipaddress.IPv6Address):
            return str(obj)

        if getattr(obj, "to_json", None):
            out = obj.to_json()
            if out:
                return out

        return json.JSONEncoder.default(self, obj)