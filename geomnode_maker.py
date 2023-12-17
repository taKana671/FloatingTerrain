import array
import math

from panda3d.core import Vec3, Point3
from panda3d.core import NodePath
from panda3d.core import Geom, GeomNode, GeomTriangles
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexArrayFormat


class GeomRoot(NodePath):

    def __init__(self, name):
        geomnode = self.create_geomnode(name)
        super().__init__(geomnode)
        self.set_two_sided(True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'create_vertices' not in cls.__dict__:
            raise NotImplementedError('Subclasses should implement create_vertices.')

    def create_format(self):
        arr_format = GeomVertexArrayFormat()
        arr_format.add_column('vertex', 3, Geom.NTFloat32, Geom.CPoint)
        arr_format.add_column('color', 4, Geom.NTFloat32, Geom.CColor)
        arr_format.add_column('normal', 3, Geom.NTFloat32, Geom.CColor)
        arr_format.add_column('texcoord', 2, Geom.NTFloat32, Geom.CTexcoord)
        fmt = GeomVertexFormat.register_format(arr_format)
        return fmt

    def create_geomnode(self, name):
        fmt = self.create_format()
        vdata_values = array.array('f', [])
        prim_indices = array.array('H', [])

        vertex_count = self.create_vertices(vdata_values, prim_indices)

        vdata = GeomVertexData(name, fmt, Geom.UHStatic)
        vdata.unclean_set_num_rows(vertex_count)
        vdata_mem = memoryview(vdata.modify_array(0)).cast('B').cast('f')
        vdata_mem[:] = vdata_values

        prim = GeomTriangles(Geom.UHStatic)
        prim_array = prim.modify_vertices()
        prim_array.unclean_set_num_rows(len(prim_indices))
        prim_mem = memoryview(prim_array).cast('B').cast('H')
        prim_mem[:] = prim_indices

        node = GeomNode('geomnode')
        geom = Geom(vdata)
        geom.add_primitive(prim)
        node.add_geom(geom)
        return node


class Sphere(GeomRoot):
    """Create a geom node of sphere.
       Args:
            radius (int): the radius of sphere;
            segments (int): the number of surface subdivisions;
    """

    def __init__(self, radius=1.5, segments=22):
        self.radius = radius
        self.segments = segments
        super().__init__('sphere')

    def create_bottom_pole(self, vdata_values, prim_indices):
        # the bottom pole vertices
        normal = (0.0, 0.0, -1.0)
        vertex = (0.0, 0.0, -self.radius)
        color = (1, 1, 1, 1)

        for i in range(self.segments):
            u = i / self.segments
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 0.0))

            # the vertex order of the pole vertices
            prim_indices.extend((i, i + self.segments + 1, i + self.segments))

        return self.segments

    def create_quads(self, index_offset, vdata_values, prim_indices):
        delta_angle = 2 * math.pi / self.segments
        color = (1, 1, 1, 1)
        vertex_count = 0

        # the quad vertices
        for i in range((self.segments - 2) // 2):
            angle_v = delta_angle * (i + 1)
            radius_h = self.radius * math.sin(angle_v)
            z = self.radius * -math.cos(angle_v)
            v = 2.0 * (i + 1) / self.segments

            for j in range(self.segments + 1):
                angle = delta_angle * j
                c = math.cos(angle)
                s = math.sin(angle)
                x = radius_h * c
                y = radius_h * s
                normal = Vec3(x, y, z).normalized()
                u = j / self.segments

                vdata_values.extend((x, y, z))
                vdata_values.extend(color)
                vdata_values.extend(normal)
                vdata_values.extend((u, v))

                # the vertex order of the quad vertices
                if i > 0 and j <= self.segments:
                    px = i * (self.segments + 1) + j + index_offset
                    prim_indices.extend((px, px - self.segments - 1, px - self.segments))
                    prim_indices.extend((px, px - self.segments, px + 1))

            vertex_count += self.segments + 1

        return vertex_count

    def create_top_pole(self, index_offset, vdata_values, prim_indices):
        vertex = (0.0, 0.0, self.radius)
        normal = (0.0, 0.0, 1.0)
        color = (1, 1, 1, 1)

        # the top pole vertices
        for i in range(self.segments):
            u = i / self.segments
            vdata_values.extend(vertex)
            vdata_values.extend(color)
            vdata_values.extend(normal)
            vdata_values.extend((u, 1.0))

            # the vertex order of the top pole vertices
            x = i + index_offset
            prim_indices.extend((x, x + 1, x + self.segments + 1))

        return self.segments

    def create_vertices(self, vdata_values, prim_indices):
        vertex_count = 0

        # create vertices of the bottom pole, quads, and top pole
        vertex_count += self.create_bottom_pole(vdata_values, prim_indices)
        vertex_count += self.create_quads(vertex_count, vdata_values, prim_indices)
        vertex_count += self.create_top_pole(vertex_count - self.segments - 1, vdata_values, prim_indices)

        return vertex_count