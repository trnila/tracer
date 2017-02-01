class Frame:
    def __init__(self, ip, location):
        self.ip = ip
        self.location = location

    def __repr__(self):
        return self.location

    def to_json(self):
        return {
            'ip': self.ip,
            'location': self.location
        }
