from collections import namedtuple, defaultdict
from disjoint_set import DisjointSet
import itertools

'''
Simple (non-performant) implementation of 
  egg: fast and extensible equality saturation
  https://dl.acm.org/doi/pdf/10.1145/3434304
'''

ENode = namedtuple('Enode', ['op', 'operands'])

class Pattern:
  def __init__(self, op, *sub_patterns):
    self.op = op
    self.sub_patterns = sub_patterns
    self.is_leaf = not sub_patterns

  def get_sub_pattern(self, i):
    '''
    ### interface
    id -> Pattern
    '''
    return self.sub_patterns[i]

  def get_live_in(self):
    '''
    ### interface
    '''
    assert self.is_leaf
    return self.op

  def match_local(self, n):
    '''
    ### interface
    '''
    return self.op == n.op or self.is_leaf

  def apply(self, egraph, subst):
    if self.is_leaf:
      x = self.get_live_in()
      if x in subst:
        return egraph.get_id(subst[x])
      # x must be a constant
      return egraph.make(x)
    operands = [p.apply(egraph, subst) for p in self.sub_patterns]
    return egraph.make(self.op, *operands)

class Rewrite:
  def __init__(self, lhs, rhs, subst):
    # lhs and rhs are patterns
    self.lhs = lhs
    self.rhs = rhs
    # mapping <live-ins of lhs> -> <live-ins of rhs>
    self.subst = subst

  def apply(self, egraph, subst):
    '''
    ### interface
    subst -> enode
    '''
    return self.rhs.apply(
        egraph,
        {x2 : subst[x1]
          for x1, x2 in self.subst.items()})

def merge_substs(substs):
  merged = {}
  for subst in substs:
    if subst is None:
      return None
    for k, v in subst.items():
      if k in merged and merged[k] != v:
        return None
      merged[k] = v
  return merged

class EGraph:
  def __init__(self):
    self.counter = 0
    # node -> ids
    self.ids = {}
    # equivalence class over ids
    self.ec = DisjointSet()
    # mapping ids/values (not nodes) -> [(user, class id of user)]
    self.users = defaultdict(set)
    self.worklist = set()

  def size(self):
    return len(self.ids)

  def canonicalize(self, n):
    return ENode(n.op, tuple(self.ec.find(i) for i in n.operands))

  def make(self, op, *operands):
    return self.add(ENode(op, operands))

  def add(self, n):
    n = self.canonicalize(n)
    if n in self.ids:
      return self.ids[n]
    i = self.counter
    self.counter += 1
    self.ids[n] = i
    for j in n.operands:
      self.users[self.ec.find(j)].add((n, self.ec.find(i)))
    return i

  def get_id(self, n):
    assert n in self.ids
    return self.ec.find(self.ids[n])

  def merge(self, i, j):
    i = self.ec.find(i)
    j = self.ec.find(j)
    if i == j:
      return i

    users = self.users[i].union(self.users[j])
    self.ec.union(i, j)
    i = self.ec.find(i)
    self.worklist.add(i)
    self.users[i] = users
    return i

  def rebuild(self):
    while len(self.worklist) > 0:
      worklist = { self.ec.find(i) for i in self.worklist }
      self.worklist = set()
      for i in worklist:
        self.repair(i)

  def repair(self, i):
    for n, j in self.users[i]:
      if n in self.ids:
        del self.ids[n]
      self.ids[self.canonicalize(n)] = self.ec.find(j)

    new_users = {}
    for n, j in self.users[i]:
      n = self.canonicalize(n)
      if n in new_users:
        self.merge(j, new_users[n])
      new_users[n] = self.ec.find(j)
    self.users[i] = set(new_users.items())

  def equal(self, i, j):
    return self.ec.connected(i, j)

  def match_class(self, i, pat):
    for n, j in self.ids.items():
      if i == j:
        yield from self.match_node(n, pat)

  def match_node(self, n, pat):
    if not pat.match_local(n):
      return

    if pat.is_leaf:
      # match the live-in to n
      yield {pat.get_live_in(): n}
      return

    sub_matches = [self.match_class(operand, pat.get_sub_pattern(operand_id))
        for operand_id, operand in enumerate(n.operands)]
    for substs in itertools.product(*sub_matches):
      subst = merge_substs(substs)
      if subst is not None:
        yield subst

  def match(self, pat):
    for n, i in self.ids.items():
      for subst in self.match_node(n, pat):
        yield i, subst

def saturate(egraph, rewrites, max_iters=1000):
  for i in range(max_iters):
    size = egraph.size()

    matches = []
    for rw in rewrites:
      for i, subst in egraph.match(rw.lhs):
        matches.append((i, subst, rw))

    for i, subst, rw in matches:
      egraph.merge(i, rw.apply(egraph, subst))

    egraph.rebuild()

    if size == egraph.size():
      return i
