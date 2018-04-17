import generic as g


class RayTests(g.unittest.TestCase):

    def test_rays(self):
        meshes = [g.get_mesh(**k) for k in g.data['ray_data']['load_kwargs']]
        rays = g.data['ray_data']['rays']
        names = [m.metadata['file_name'] for m in meshes]

        hit_id = []
        hit_loc = []
        hit_any = []
        for m in meshes:
            name = m.metadata['file_name']
            hit_any.append(m.ray.intersects_any(**rays[name]))
            hit_loc.append(len(m.ray.intersects_location(**rays[name])[0]))
            hit_id.append(m.ray.intersects_id(**rays[name]))
        hit_any = g.np.array(hit_any, dtype=g.np.int)

        for i in g.trimesh.grouping.group(
                g.np.unique(names, return_inverse=True)[1]):
            broken = hit_any[i].astype(g.np.int).ptp(axis=0).sum()
            self.assertTrue(broken == 0)

    def test_rps(self):
        for use_embree in [True, False]:
            dimension = (10000, 3)
            sphere = g.get_mesh('unit_sphere.STL',
                                use_embree=use_embree)

            ray_origins = g.np.random.random(dimension)
            ray_directions = g.np.tile([0, 0, 1], (dimension[0], 1))
            ray_origins[:, 2] = -5

            # force ray object to allocate tree before timing it
            #tree = sphere.ray.tree
            tic = [g.time.time()]
            sphere.ray.intersects_id(ray_origins, ray_directions)
            tic.append(g.time.time())
            sphere.ray.intersects_location(ray_origins, ray_directions)
            tic.append(g.time.time())

            rps = dimension[0] / g.np.diff(tic)

            g.log.info('Measured %s rays/second with embree %d',
                       str(rps),
                       use_embree)

    def test_contains(self):
        scale = 1.5
        for use_embree in [True, False]:
            mesh = g.get_mesh('unit_cube.STL', use_embree=use_embree)
            g.log.info('Contains test ray engine: ' + str(mesh.ray.__class__))

            test_on = mesh.ray.contains_points(mesh.vertices)
            test_in = mesh.ray.contains_points(mesh.vertices * (1.0 / scale))
            assert test_in.all()

            test_out = mesh.ray.contains_points(mesh.vertices * scale)
            assert not test_out.any()

            points_way_out = (
                g.np.random.random(
                    (30, 3)) * 100) + 1.0 + mesh.bounds[1]
            test_way_out = mesh.ray.contains_points(points_way_out)
            assert not test_way_out.any()

            test_centroid = mesh.ray.contains_points([mesh.center_mass])
            assert test_centroid.all()

    def test_on_vertex(self):
        for use_embree in [True, False]:
            m = g.trimesh.primitives.Box(use_embree=False)

            origins = g.np.zeros_like(m.vertices)
            vectors = m.vertices.copy()

            assert m.ray.intersects_any(ray_origins=origins,
                                        ray_directions=vectors).all()

            (locations,
             index_ray,
             index_tri) = m.ray.intersects_location(ray_origins=origins,
                                                    ray_directions=vectors)

            hit_count = g.np.bincount(index_ray,
                                      minlength=len(origins))

            assert (hit_count == 1).all()

    def test_on_edge(self):
        for use_embree in [True, False]:
            m = g.get_mesh('7_8ths_cube.stl')

            points = [[4.5, 0, -23], [4.5, 0, -2], [0, 0, -1e-6], [0, 0, -1]]
            truth = [False, True, True, True]
            result = g.trimesh.ray.ray_util.contains_points(m.ray, points)

            assert (result == truth).all()

    def test_multiple_hits(self):
        '''
        '''
        # Set camera focal length (in pixels)
        f = g.np.array([1000., 1000.])
        h, w = 256, 256

        # Set up a list of ray directions - one for each pixel in our (256,
        # 256) output image.
        ray_directions = g.trimesh.util.grid_arange([[-h / 2, -w / 2], [h / 2, w / 2]],
                                                    step=2.0)
        ray_directions = g.np.column_stack((ray_directions,
                                            g.np.ones(len(ray_directions)) * f[0]))

        # Initialize the camera origin to be somewhere behind the cube.
        cam_t = g.np.array([0, 0, -15.])
        # Duplicate to ensure we have an camera_origin per ray direction
        ray_origins = g.np.tile(cam_t, (ray_directions.shape[0], 1))

        for use_embree in [True, False]:
            # Generate a 1 x 1 x 1 cube using the trimesh box primitive
            cube_mesh = g.trimesh.primitives.Box(extents=[2, 2, 2],
                                                 use_embree=use_embree)

            # Perform 256 * 256 raycasts, one for each pixel on the image
            # plane. We only want the 'first' hit.
            index_triangles, index_ray = cube_mesh.ray.intersects_id(
                ray_origins=ray_origins,
                ray_directions=ray_directions,
                multiple_hits=False)
            assert len(g.np.unique(index_triangles)) == 2

            index_triangles, index_ray = cube_mesh.ray.intersects_id(
                ray_origins=ray_origins,
                ray_directions=ray_directions,
                multiple_hits=True)
            assert len(g.np.unique(index_triangles)) > 2


    def test_contain_single(self):
        # not watertight
        mesh = g.get_mesh("teapot.stl", use_embree=False)

        # sample a grid of points (n,3)
        points = mesh.bounding_box.sample_grid(step=2.0)
        # to a contains check on every point
        contained = mesh.ray.contains_points(points)

        assert len(points) == len(contained)
        
        # not contained and should surface a bug
        for point in mesh.bounding_box.vertices:
            mesh.ray.contains_points([point])
            
if __name__ == '__main__':
    g.trimesh.util.attach_to_log()
    g.unittest.main()
