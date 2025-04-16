class Vector3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__  # Allow scalar * Vector3D as well

    def __repr__(self):
        return f"Vector3D({self.x}, {self.y}, {self.z})"