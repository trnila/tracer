import ipaddress
import json
import datetime


class AppJSONEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, ipaddress.IPv4Address):
            return str(o)
        elif isinstance(o, ipaddress.IPv6Address):
            return str(o)
        elif isinstance(o, datetime.datetime):
            return o.isoformat()

        if getattr(o, "to_json", None):
            return o.to_json()

        return json.JSONEncoder.default(self, o)
