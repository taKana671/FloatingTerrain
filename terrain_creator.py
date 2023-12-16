import itertools
import random

import cv2
import numpy as np

from panda3d.bullet import BulletSphereShape, BulletRigidBodyNode
from panda3d.bullet import BulletCylinderShape, BulletSphereShape

from panda3d.bullet import BulletHeightfieldShape, ZUp
from panda3d.core import NodePath, PandaNode
from panda3d.core import Vec3, Point3, BitMask32, LColor, Vec2
from panda3d.core import Filename
from panda3d.core import PNMImage
from panda3d.core import ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState
from panda3d.core import CardMaker, TextureStage, Texture
from panda3d.core import TransparencyAttrib, TransformState
from panda3d.core import GeoMipTerrain

from heightfield_tiles import HeightfieldTiles
from utils import create_line_node


class Tree(NodePath):

    def __init__(self, pos, angle, parent):
        super().__init__(BulletRigidBodyNode('tree'))
        model = base.loader.loadModel('models/plant6/plants6')
        # model = base.loader.load_model('models/Tree/tree.')
        model.set_scale(0.5)
        self.set_h(angle)
        # model.set_scale(10)
        end, tip = model.get_tight_bounds()
        height = (tip - end).z
        shape = BulletCylinderShape(1, height, ZUp)
        self.node().add_shape(shape)
        # self.node().add_shape(shape, TransformState.make_pos(Point3(0, 0, 10)))
        model.set_transform(TransformState.make_pos(Vec3(0, 0, -10)))
        self.set_collide_mask(BitMask32(1) | BitMask32.bit(2))
        model.reparent_to(self)

        self.set_pos(pos)
        # self.reparent_to(base.render)
        self.reparent_to(parent)


class TerrainBody(NodePath):

    def __init__(self, pos):
        super().__init__(BulletRigidBodyNode('compoundTerrain'))
        self.set_pos(pos)
        self.node().set_mass(0)
        self.set_collide_mask(BitMask32.bit(1))
        # self.node().set_kinematic(True)

    def assemble(self, file_path, height, pos):
        img = PNMImage(Filename(file_path))
        shape = BulletHeightfieldShape(img, height, ZUp)
        shape.set_use_diamond_subdivision(True)
        # new_pos = Point3(pos.x + 128.5, pos.y + 128.5, 0)
        # new_pos = Point3(pos.x + 128, pos.y + 128, 0)
        self.node().add_shape(shape, TransformState.make_pos(pos))


class TerrainCreator:

    def __init__(self, world):
        self.world = world

        self.scene = NodePath('scene')
        self.scene.reparent_to(base.render)

        self.test_shape = BulletSphereShape(3)
        self.angles = [0, 60, 90, 120, 180, 270]

        self.terrains = NodePath('terrains')
        self.terrain_body = TerrainBody(Point3(0, 0, 0))
        self.terrain_body.reparent_to(self.terrains)
        self.world.attach(self.terrain_body.node())
        self.terrains.reparent_to(base.render)

        self.natures = NodePath('natures')
        self.natures.reparent_to(base.render)

        self.terrain_roots = []
        self.heightfield_tiles = HeightfieldTiles()

        self.trees = itertools.chain(
            *[tile.change_pixel_to_cartesian(tile.tree_area) for tile in self.heightfield_tiles._tiles]
        )

    def load_textures(self):
        files = [
            'small_stones.jpg',
            'grass.png',
            'red_ground.jpg',
            'dark_green.jpg'
        ]

        for i, file in enumerate(files):
            ts = TextureStage(f'ts{i}')
            ts.set_sort(i)
            texture = base.loader.load_texture(f'textures/{file}')
            yield ts, texture

    def make_terrain(self):
        textures = [(ts, tex) for ts, tex in self.load_textures()]
        height = 50

        for i, tile in enumerate(self.heightfield_tiles):
            terrain = GeoMipTerrain(f'terrain{i}')
            terrain.set_heightfield(tile.file.path)
            terrain.set_border_stitching(True)
            # terrain.clear_color_map()
            # block_size 8 and min 2, or block_size 16 and min 3 is good.
            terrain.set_block_size(8)
            terrain.set_min_level(2)
            terrain.set_focal_point(base.camera)

            root = terrain.get_root()
            root.set_scale(1, 1, height)
            root.set_pos(Point3(tile.origin.x - 0.5, tile.origin.y - 0.5, -(height / 2)))
            # root.set_two_sided(True) <- opposite side is textured too.

            for ts, tex in textures:
                root.set_texture(ts, tex)

            root.reparent_to(self.terrains)
            terrain.generate()

            # Point3(pos.x + 128.5, pos.y + 128.5, 0)
            pos = Point3(root.get_x() + 128.5, root.get_y() + 128.5, 0)
            self.terrain_body.assemble(tile.file.path, height, pos)

            terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain_v.glsl", "shaders/terrain_f.glsl")
            root.set_shader(terrain_shader)
            root.set_shader_input('camera', base.camera)

            for i in range(4):
                root.set_shader_input(f'tex_ScaleFactor{i}', 10.0)

            self.terrain_roots.append(terrain)

    def find_position(self, x, y):
        pt_from = Point3(x, y, 30)
        pt_to = Point3(x, y, -30)

        ts_from = TransformState.make_pos(pt_from)
        ts_to = TransformState.make_pos(pt_to)

        if not self.world.sweep_test_closest(self.test_shape, ts_from, ts_to, BitMask32.bit(2), 0.0).has_hit():
            result = self.world.ray_test_closest(pt_from, pt_to, mask=BitMask32.bit(1))
            if result.has_hit():
                return result.get_hit_pos()

        return None

    def plant_trees(self, task):
        try:
            x, y = next(self.trees)

            if pos := self.find_position(x, y):
                # self.debug_line_center = create_line_node(Point3(wx, wy, 30), Point3(wx, wy, -30), LColor(1, 0, 0, 1))
                # self.debug_line_center.reparent_to(base.render)
                angle = random.choice(self.angles)
                tree = Tree(pos, angle, self.natures)
                self.world.attach(tree.node())
        except StopIteration:
            return task.done
        else:
            return task.cont
