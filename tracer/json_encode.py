import ipaddress
import json


class AppJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ipaddress.IPv4Address):
            return str(o)
        elif isinstance(o, ipaddress.IPv6Address):
            return str(o)

        if getattr(o, "to_json", None):
            return o.to_json()

        return json.JSONEncoder.default(self, o)
