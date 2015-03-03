from __future__ import division

__copyright__ = "Copyright (C) 2014 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import numpy as np

class VertexRay:
    def __init__(self, ray, pos):
        self.ray = ray
        self.pos = pos

class _SplitFaceRecord(object):
    """
    .. attribute:: neighboring_elements
    .. attribute:: new_vertex_nr

        integer or None
    """
class Adj:
    """One vertex-associated entry of a ray.

    .. attribute:: elements

        A list of numbers of elements adjacent to
        the edge following :attr:`vertex`
        along the ray.

    .. attribute:: velements

        A list of numbers of elements adjacent to
        :attr:`vertex`.

    """
    def __init__(self, vertex=None, elements=[None, None], velements=[None, None]):
        self.vertex = vertex
        self.elements = elements
        self.velements = velements
    def __str__(self):
        return 'vertex: ' + str(self.vertex) + ' ' + 'elements: ' + str(self.elements) + ' velements: ' + str(self.velements)
#map pair of vertices to ray and midpoint
class PairMap:
    """Describes a segment of a ray between two vertices.

    .. attribute:: ray

        Index of the ray in the *rays* list.

    .. attribute:: d

        A :class:`bool` denoting direction in the ray,
        with *True* representing "positive" and *False*
        representing "negative".

    .. attribute:: midpoint

        Vertex index of the midpoint of this segment.

        *None* if no midpoint has been assigned yet.
    """

    def __init__(self, ray=None, d = True, midpoint=None):
        self.ray = ray
        #direction in ray, True means that second node (bigger index) is after first in ray
        self.d = d
        self.midpoint = midpoint
    def __str__(self):
        return 'ray: ' + str(self.ray) + ' d: ' + str(self.d) + ' midpoint: ' + str(self.midpoint)

class Refiner(object):
    def __init__(self, mesh):
        from llist import dllist, dllistnode
        self.last_mesh = mesh
        # Indices in last_mesh that were split in the last round of
        # refinement. Only these elements may be split this time
        # around.
        self.last_split_elements = None

        
        # {{{ initialization

        # a list of dllist instances containing Adj objects
        self.rays = []

        # mapping: (vertex_1, vertex_2) -> PairMap
        # where vertex_i represents a vertex number
        #
        # Assumption: vertex_1 < vertex_2
        self.pair_map = {}

        nvertices = len(mesh.vertices[0])
        
        # list of dictionaries, with each entry corresponding to
        # one vertex.
        # 
        # Each dictionary maps
        #   ray number -> dllist node containing a :class:`Adj`,
        #                 (part of *rays*)
        self.vertex_to_ray = []

        for i in xrange(nvertices):
            self.vertex_to_ray.append({})
        for grp in mesh.groups:
            iel_base = grp.element_nr_base
            for iel_grp in xrange(grp.nelements):
                #use six.moves.range
                for i in range(len(grp.vertex_indices[iel_grp])):
                    for j in range(i+1, len(grp.vertex_indices[iel_grp])):
                        vertex_pair = (min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]), \
                            max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]))
                        if vertex_pair not in self.pair_map:
                            els = []
                            els.append(iel_base+iel_grp)
                            fr = Adj(min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]), els)
                            to = Adj(max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]), [None, None])
                            self.rays.append(dllist([fr, to]))
                            self.pair_map[vertex_pair] = PairMap(len(self.rays) - 1)
                            self.vertex_to_ray[min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][len(self.rays)-1]\
                                = self.rays[len(self.rays)-1].nodeat(0)
                            self.vertex_to_ray[max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][len(self.rays)-1]\
                                = self.rays[len(self.rays)-1].nodeat(1)
                        else:
                            self.rays[self.pair_map[vertex_pair].ray].nodeat(0).value.elements.append(iel_base+iel_grp)
        
        # }}}

        #print mesh.groups[0].vertex_indices
        '''
        self.ray_vertices = np.empty([len(mesh.groups[0].vertex_indices) * 
            len(mesh.groups[0].vertex_indices[0]) * (len(mesh.groups[0].vertex_indices[0]) - 1) / 2, 2], 
                dtype=np.int32)
        self.ray_elements = np.zeros([len(mesh.groups[0].vertex_indices) * 
            len(mesh.groups[0].vertex_indices[0]) * (len(mesh.groups[0].vertex_indices[0]) - 1)
             / 2, 1, 2], dtype=np.int32)
        self.vertex_to_ray = []

        for i in mesh.vertices[0]:
            self.vertex_to_ray.append([]);
        count = 0
        for grp in mesh.groups:
            for i in range(0, len(grp.vertex_indices)):
                for j in range(0, len(grp.vertex_indices[i])):
                    for k in range(j + 1, len(grp.vertex_indices[i])):
                        self.ray_vertices[count][0] = grp.vertex_indices[i][j]
                        self.ray_vertices[count][1] = grp.vertex_indices[i][k]
                        temp1 = VertexRay(count, 0)
                        self.vertex_to_ray[grp.vertex_indices[i][j]].append(temp1)
                        temp2 = VertexRay(count, 1)
                        self.vertex_to_ray[grp.vertex_indices[i][k]].append(temp2)
                        count += 1
        ind = 0
        #print self.ray_vertices
        for i in self.ray_vertices:
            which = 0
            for grp in mesh.groups:
                for j in range(0, len(grp.vertex_indices)):
                    count = 0
                    for k in grp.vertex_indices[j]:
                        if k == i[0] or k == i[1]:
                            count += 1
                    #found an element sharing edge
                    if count == 2:
                        self.ray_elements[ind][0][which] = j
                        which += 1
                        if which == 2:
                            break
            ind += 1
        '''



    def get_refine_base_index(self):
        if self.last_split_elements is None:
            return 0
        else:
            return self.last_mesh.nelements - len(self.last_split_elements)

    def get_empty_refine_flags(self):
        return np.zeros(
                self.last_mesh.nelements - self.get_refine_base_index(),
                np.bool)

    #refine_flag tells you which elements to split as a numpy array of bools
    def refine(self, refine_flags):
        """
        :return: a refined mesh
        """

        # multi-level mapping:
        # {
        #   dimension of intersecting entity (0=vertex,1=edge,2=face,...)
        #   :
        #   { frozenset of end vertices : _SplitFaceRecord }
        # }
        '''
        import numpy as np
        count = 0
        for i in refine_flags:
            if i:
                count += 1
        
        le = len(self.last_mesh.vertices[0])

        vertices = np.empty([len(self.last_mesh.vertices), len(self.last_mesh.groups[0].vertex_indices[0])
            * count + le])
        vertex_indices = np.empty([len(self.last_mesh.groups[0].vertex_indices)
            + count*3, 
            len(self.last_mesh.groups[0].vertex_indices[0])], dtype=np.int32)
        indices_it = len(self.last_mesh.groups[0].vertex_indices)        
        for i in range(0, len(self.last_mesh.vertices)):
            for j in range(0, len(self.last_mesh.vertices[i])):
                vertices[i][j] = self.last_mesh.vertices[i][j]
        for i in range(0, len(self.last_mesh.groups[0].vertex_indices)):
            for j in range(0, len(self.last_mesh.groups[0].vertex_indices[i])):
                vertex_indices[i][j] = self.last_mesh.groups[0].vertex_indices[i][j]

        
        import itertools
        for i in range(0, len(refine_flags)):
            if refine_flags[i]:
                for subset in itertools.combinations(self.last_mesh.groups[0].vertex_indices[i], 
                    len(self.last_mesh.groups[0].vertex_indices[i]) - 1):
                    for j in range(0, len(self.last_mesh.vertices)):
                        avg = 0
                        for k in subset:
                            avg += self.last_mesh.vertices[j][k]
                        avg /= len(self.last_mesh.vertices)
                        self.last_mesh.vertices[j][le] = avg
                        le++
                vertex_indices[indices_it][0] = self.last_mesh.groups[0].vertex_indices[i][0]
        '''
        '''
        import numpy as np
        count = 0
        for i in refine_flags:
            if i:
                count += 1
        #print count
        #print self.last_mesh.vertices
        #print vertices
        if(len(self.last_mesh.groups[0].vertex_indices[0]) == 3):
            for group in range(0, len(self.last_mesh.groups)):
                le = len(self.last_mesh.vertices[0])
                vertices = np.empty([len(self.last_mesh.vertices), 
                    len(self.last_mesh.groups[group].vertex_indices[0])
                    * count + le])
                vertex_indices = np.empty([len(self.last_mesh.groups[group].vertex_indices)
                    + count*3, 
                    len(self.last_mesh.groups[group].vertex_indices[0])], dtype=np.int32)
                indices_i = 0        
                for i in range(0, len(self.last_mesh.vertices)):
                    for j in range(0, len(self.last_mesh.vertices[i])):
                        vertices[i][j] = self.last_mesh.vertices[i][j]
                #for i in range(0, len(self.last_mesh.groups[group].vertex_indices)):
                    #for j in range(0, len(self.last_mesh.groups[group].vertex_indices[i])):
                        #vertex_indices[i][j] = self.last_mesh.groups[group].vertex_indices[i][j]
                for fl in range(0, len(refine_flags)):
                    if(refine_flags[fl]):
                        i = self.last_mesh.groups[group].vertex_indices[fl]
                        for j in range(0, len(i)):
                            for k in range(j + 1, len(i)):
                                for l in range(0, 3):
                                    #print self.last_mesh.vertices[l][i[j]], ' ', self.last_mesh.vertices[l][i[k]], '=', ((self.last_mesh.vertices[l][i[j]] + self.last_mesh.vertices[l][i[k]]) / 2)
                                    vertices[l][le]=((self.last_mesh.vertices[l][i[j]] + self.last_mesh.vertices[l][i[k]]) / 2)
                                le += 1
                        vertex_indices[indices_i][0] = i[0]
                        vertex_indices[indices_i][1] = le-3
                        vertex_indices[indices_i][2] = le-2
                        indices_i += 1
                        vertex_indices[indices_i][0] = i[1]
                        vertex_indices[indices_i][1] = le-1
                        vertex_indices[indices_i][2] = le-3
                        indices_i += 1
                        vertex_indices[indices_i][0] = i[2]
                        vertex_indices[indices_i][1] = le-2
                        vertex_indices[indices_i][2] = le-1
                        indices_i += 1
                        vertex_indices[indices_i][0] = le-3
                        vertex_indices[indices_i][1] = le-2
                        vertex_indices[indices_i][2] = le-1
                        indices_i += 1
                    else:
                        for j in range(0, len(self.last_mesh.groups[group].vertex_indices[fl])):
                            vertex_indices[indices_i][j] = self.last_mesh.groups[group].vertex_indices[fl][j]
                        indices_i += 1
        '''
        import numpy as np
        # if (isinstance(self.last_mesh.groups[0], SimplexElementGroup) and 
        #           self.last_mesh.groups[0].dim == 2):
        print 'refining'
        if(len(self.last_mesh.groups[0].vertex_indices[0]) == 3):
            groups = []
            midpoint_already = {}
            nelements = 0
            nvertices = len(self.last_mesh.vertices[0])
            grpn = 0
            totalnelements=0

            # {{{ create new vertices array and each group's vertex_indices
            
            for grp in self.last_mesh.groups:
                iel_base = grp.element_nr_base
                nelements = 0
                #print grp.nelements
                for iel_grp in xrange(grp.nelements):
                    nelements += 1
                    if refine_flags[iel_base+iel_grp]:
                        nelements += 3
                        for i in range(0, len(grp.vertex_indices[iel_grp])):
                            for j in range(i+1, len(grp.vertex_indices[iel_grp])):
                                vertex_pair = (min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]), \
                                max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]))
                                if vertex_pair not in midpoint_already and self.pair_map[vertex_pair].midpoint is None:
                                    nvertices += 1
                                    midpoint_already[vertex_pair] = True
                groups.append(np.empty([nelements, len(self.last_mesh.groups[grpn].vertex_indices[grpn])], dtype=np.int32))
                grpn += 1
                totalnelements += nelements

            vertices = np.empty([len(self.last_mesh.vertices), nvertices])

            # }}}

            # {{{ bring over vertex_indices and vertices info from previous generation

            for i in range(0, len(self.last_mesh.vertices)):
                for j in range(0, len(self.last_mesh.vertices[i])):
                    # always use v[i,j]
                    vertices[i][j] = self.last_mesh.vertices[i][j]
            grpn = 0
            for grp in self.last_mesh.groups:
                for iel_grp in xrange(grp.nelements):
                    for i in range(0, len(grp.vertex_indices[iel_grp])):
                        groups[grpn][iel_grp][i] = grp.vertex_indices[iel_grp][i]
                grpn += 1
            grpn = 0

            # }}}

            vertices_idx = len(self.last_mesh.vertices[0])
            for grp in self.last_mesh.groups:
                iel_base = grp.element_nr_base
                indices_idx = len(grp.vertex_indices)
                
                # np.where
                for iel_grp in xrange(grp.nelements):
                    if refine_flags[iel_base+iel_grp]:

                        # {{{ split element

                        # {{{ go through vertex pairs in element

                        # stores indices of all midpoints for this element
                        # (in order of vertex pairs in elements)
                        verts = []

                        for i in range(0, len(grp.vertex_indices[iel_grp])):
                            for j in range(i+1, len(grp.vertex_indices[iel_grp])):
                                vertex_pair = (min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]), \
                                max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]))
                                
                                # {{{ create midpoint if it doesn't exist already

                                if self.pair_map[vertex_pair].midpoint is None:
                                    self.pair_map[vertex_pair].midpoint = vertices_idx
                                    vertex_pair1 = (min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]), vertices_idx)
                                    vertex_pair2 = (max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]), vertices_idx)
                                    self.pair_map[vertex_pair1] = PairMap(self.pair_map[vertex_pair].ray, self.pair_map[vertex_pair].d, \
                                        None)
                                    self.pair_map[vertex_pair2] = PairMap(self.pair_map[vertex_pair].ray, not self.pair_map[vertex_pair].d, \
                                        None)
                                    self.vertex_to_ray.append({})
                                    
                                    # try and collapse the two branches by setting up variables
                                    # ahead of time
                                    if self.pair_map[vertex_pair].d:
                                        velements = self.vertex_to_ray[min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray].value.elements
                                        self.rays[self.pair_map[vertex_pair].ray].insert(Adj(vertices_idx, [None, None], velements), \
                                            self.vertex_to_ray[max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray])
                                        self.vertex_to_ray[vertices_idx][self.pair_map[vertex_pair].ray] = \
                                            self.vertex_to_ray[max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray].prev
                                    else:
                                        velements = self.vertex_to_ray[max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray].value.elements
                                        self.rays[self.pair_map[vertex_pair].ray].insert(Adj(vertices_idx, [None, None], velements), \
                                            self.vertex_to_ray[min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray])
                                        self.vertex_to_ray[vertices_idx][self.pair_map[vertex_pair].ray] = \
                                            self.vertex_to_ray[min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray].prev
                                    
                                    # compute location of midpoint
                                    for k in range(0, 3):
                                        vertices[k][vertices_idx] = (self.last_mesh.vertices[k][grp.vertex_indices[iel_grp][i]]
                                            + self.last_mesh.vertices[k][grp.vertex_indices[iel_grp][j]]) / 2.0
                                    
                                    verts.append(vertices_idx)
                                    vertices_idx += 1
                                else:
                                    verts.append(self.pair_map[vertex_pair].midpoint)

                                # }}}
                        
                        # }}}

                        # {{{ fix connectivity

                        # new elements will be nels+0 .. nels+2
                        # (While those don't exist yet, we generate connectivity for them
                        # anyhow.)

                        ind = 0

                        # vertex_pairs = [(i,j) for i in range(3) for j in range(i+1, 3)]
                        for i in range(0, len(grp.vertex_indices[iel_grp])):
                            for j in range(i+1, len(grp.vertex_indices[iel_grp])):
                                vertex_pair = (min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]),
                                max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j]))
                                if self.pair_map[vertex_pair].d:
                                    start_node = self.vertex_to_ray[min(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray]
                                else:
                                    start_node = self.vertex_to_ray[max(grp.vertex_indices[iel_grp][i], grp.vertex_indices[iel_grp][j])][self.pair_map[vertex_pair].ray]
                                end_node = self.vertex_to_ray[self.pair_map[vertex_pair].midpoint][self.pair_map[vertex_pair].ray]

                                # hop along ray from start node to end node
                                while start_node != end_node:
                                    # start_node.value.elements.index(iel_base+iel_grp)
                                    if start_node.value.elements[0] == iel_base+iel_grp:
                                        start_node.value.elements[0] = iel_base+indices_idx+ind
                                    elif start_node.value.elements[1] == iel_base+iel_grp:
                                        start_node.value.elements[1] = iel_base+indices_idx+ind
                                    else:
                                        assert False
                                    start_node = start_node.next
                                ind += 1
                        ind = 0

                        # }}}

                        #generate new rays
                        from llist import dllist, dllistnode

                        for i in range(0, len(verts)):
                            for j in range(i+1, len(verts)):
                                vertex_pair = (min(verts[i], verts[j]), max(verts[i], verts[j]))
                                els = []
                                els.append(iel_base+iel_grp)
                                els.append(iel_base+indices_idx+ind)
                                
                                fr = Adj(min(verts[i], verts[j]), els)

                                # We're creating a new ray, and this is the end node
                                # of it.
                                to = Adj(max(verts[i], verts[j]), [None, None])

                                self.rays.append(dllist([fr, to]))
                                self.pair_map[vertex_pair] = PairMap(len(self.rays) - 1)
                                self.vertex_to_ray[min(verts[i], verts[j])][len(self.rays)-1]\
                                    = self.rays[len(self.rays)-1].nodeat(0)
                                self.vertex_to_ray[max(verts[i], verts[j])][len(self.rays)-1]\
                                    = self.rays[len(self.rays)-1].nodeat(1)

                        #generate actual elements
                        #middle element
                        vertex_pair = (min(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][1]), \
                        max(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][1]))
                        groups[grpn][iel_grp][0] = self.pair_map[vertex_pair].midpoint
                        vertex_pair = (min(grp.vertex_indices[iel_grp][1], grp.vertex_indices[iel_grp][2]), \
                        max(grp.vertex_indices[iel_grp][1], grp.vertex_indices[iel_grp][2]))
                        groups[grpn][iel_grp][1] = self.pair_map[vertex_pair].midpoint
                        vertex_pair = (min(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][2]), \
                        max(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][2]))
                        groups[grpn][iel_grp][2] = self.pair_map[vertex_pair].midpoint
                        #element 0
                        groups[grpn][indices_idx][0] = grp.vertex_indices[iel_grp][0]
                        vertex_pair = (min(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][1]), \
                        max(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][1]))
                        groups[grpn][indices_idx][1] = self.pair_map[vertex_pair].midpoint
                        vertex_pair = (min(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][2]), \
                        max(grp.vertex_indices[iel_grp][0], grp.vertex_indices[iel_grp][2]))
                        groups[grpn][indices_idx][2] = self.pair_map[vertex_pair].midpoint
                        indices_idx += 1
                        #element 1
                        groups[grpn][indices_idx][0] = grp.vertex_indices[iel_grp][1]
                        vertex_pair = (min(grp.vertex_indices[iel_grp][1], grp.vertex_indices[iel_grp][0]), \
                        max(grp.vertex_indices[iel_grp][1], grp.vertex_indices[iel_grp][0]))
                        groups[grpn][indices_idx][1] = self.pair_map[vertex_pair].midpoint
                        vertex_pair = (min(grp.vertex_indices[iel_grp][1], grp.vertex_indices[iel_grp][2]), \
                        max(grp.vertex_indices[iel_grp][1], grp.vertex_indices[iel_grp][2]))
                        groups[grpn][indices_idx][2] = self.pair_map[vertex_pair].midpoint
                        indices_idx += 1
                        #element 2
                        groups[grpn][indices_idx][0] = grp.vertex_indices[iel_grp][2]
                        vertex_pair = (min(grp.vertex_indices[iel_grp][2], grp.vertex_indices[iel_grp][0]), \
                        max(grp.vertex_indices[iel_grp][2], grp.vertex_indices[iel_grp][0]))
                        groups[grpn][indices_idx][1] = self.pair_map[vertex_pair].midpoint
                        vertex_pair = (min(grp.vertex_indices[iel_grp][2], grp.vertex_indices[iel_grp][1]), \
                        max(grp.vertex_indices[iel_grp][2], grp.vertex_indices[iel_grp][1]))
                        groups[grpn][indices_idx][2] = self.pair_map[vertex_pair].midpoint
                        indices_idx += 1

                        # }}}

                grpn += 1


        #print vertices
        #print vertex_indices
        from meshmode.mesh.generation import make_group_from_vertices
        #grp = make_group_from_vertices(vertices, vertex_indices, 4)
        grp = []
        grpn = 0
        for grpn in range(0, len(groups)):
            grp.append(make_group_from_vertices(vertices, groups[grpn], 4))

        from meshmode.mesh import Mesh
        #return Mesh(vertices, [grp], element_connectivity=self.generate_connectivity(len(self.last_mesh.groups[group].vertex_indices) \
        #            + count*3))
        
        self.last_mesh = Mesh(vertices, grp, element_connectivity=self.generate_connectivity(totalnelements, nvertices))
        return self.last_mesh
        split_faces = {}

        ibase = self.get_refine_base_index()
        affected_group_indices = set()

        for grp in self.last_mesh.groups:
            iel_base



    def generate_connectivity(self, nelements, nvertices):
        # medium-term FIXME: make this an incremental update
        # rather than build-from-scratch

        vertex_to_element = [[] for i in xrange(nvertices)]

        for grp in self.last_mesh.groups:
            iel_base = grp.element_nr_base
            for iel_grp in xrange(grp.nelements):
                for ivertex in grp.vertex_indices[iel_grp]:
                    vertex_to_element[ivertex].append(iel_base + iel_grp)

        element_to_element = [set() for i in xrange(nelements)]
        for grp in self.last_mesh.groups:
            iel_base = grp.element_nr_base
            for iel_grp in xrange(grp.nelements):
                for ivertex in grp.vertex_indices[iel_grp]:
                    element_to_element[iel_base + iel_grp].update(
                            vertex_to_element[ivertex])
        
        #print self.ray_elements
        for ray in self.rays:
            curnode = ray.first
            while curnode is not None:
                if curnode.value.elements[0] is not None:
                    element_to_element[curnode.value.elements[0]].update(curnode.value.elements)
                if curnode.value.elements[1] is not None:
                    element_to_element[curnode.value.elements[1]].update(curnode.value.elements)
                if curnode.value.velements[0] is not None:
                    element_to_element[curnode.value.velements[0]].update(curnode.value.velements)
                if curnode.value.velements[1] is not None:
                    element_to_element[curnode.value.velements[1]].update(curnode.value.velements)
                curnode = curnode.next
        '''
        for i in self.ray_elements:
            for j in i:
                #print j[0], j[1]
                element_to_element[j[0]].update(j)
                element_to_element[j[1]].update(j)
        '''
        #print element_to_element
        lengths = [len(el_list) for el_list in element_to_element]
        neighbors_starts = np.cumsum(
                np.array([0] + lengths, dtype=self.last_mesh.element_id_dtype))
        from pytools import flatten
        neighbors = np.array(
                list(flatten(element_to_element)),
                dtype=self.last_mesh.element_id_dtype)

        assert neighbors_starts[-1] == len(neighbors)
        result = []
        result.append(neighbors_starts)
        result.append(neighbors)
        return result







# vim: foldmethod=marker