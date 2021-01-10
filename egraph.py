from collections import namedtuple, defaultdict
from disjoint_set import DisjointSet
import itertools

ENode = namedtuple('Enode', ['op', 'operands'])

class Pattern:
  def __init__(self, op, *sub_patterns):
    self.op = op
    self.sub_patterns = sub_patterns
    self.is_leaf = not sub_patterns

  def get_sub_pattern(self, i):
    '''
    id -> Pattern
    '''
    return self.sub_patterns[i]

  def get_live_in(self):
    assert self.is_leaf
    return self.op

  def match_local(self, n):
    return self.op == n.op or self.is_leaf

  def apply(self, egraph, subst):
    if self.is_leaf:
      x = self.get_live_in()
      if x in subst:
        return egraph.get_id(subst[x])
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
    # node -> ids
    self.ids = {}
    # equivalence class over ids
    self.ec = DisjointSet()
    # mapping ids/values (not nodes) -> their users
    self.users = defaultdict(set)
    self.worklist = set()

  def canonicalize(self, n):
    return ENode(n.op, tuple(self.ec.find(i) for i in n.operands))

  def make(self, op, *operands):
    return self.add(ENode(op, operands))

  def add(self, n):
    n = self.canonicalize(n)
    if n in self.ids:
      return self.ids[n]
    i = len(self.ids)
    self.ids[n] = i
    for j in n.operands:
      self.users[self.ec.find(j)].add(n)
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
    new_ids = {}
    for n in self.users[i]:
      j = self.get_id(n)
      new_ids[self.canonicalize(n)] = j

    users = set()
    for n in self.users[i]:
      i = self.get_id(n)
      n = self.canonicalize(n)
      if n in users:
        self.merge(i, self.get_id(n))
      users.add(n)
    self.users[i] = users
    self.ids.update(new_ids)

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

def apply_rewrite(egraph, rw):
  substs = list(egraph.match(rw.lhs))
  for i, subst in substs:
    j = rw.apply(egraph, subst)
    egraph.merge(i, j)

def add(a, b):
  return Pattern('add', a, b)

eg = EGraph()
a = eg.make('a')
b = eg.make('b')
c = eg.make('c')
d = eg.make('d')
eg.make('add', a, 
    eg.make('add', b,
      eg.make('add', c, d)))

a = Pattern('a')
b = Pattern('b')
c = Pattern('c')
assoc = Rewrite(
    add(a, add(b, c)),
    add(add(a, b), c),
    {'a': 'a', 'b': 'b', 'c':'c'})
comm = Rewrite(
    add(a, b), add(b, a), {'a': 'a', 'b': 'b'})
for _ in range(10):
  apply_rewrite(eg, assoc)
  apply_rewrite(eg, comm)
  eg.rebuild()
from pprint import pprint
pprint(eg.ids)
pprint(list(eg.ec))

#x = eg.make('x')
#y = eg.make('y')
#a1 = eg.make('add', x, x)
#a2 = eg.make('add', y, y)
#eg.merge(x, y)
#eg.rebuild()
#
#x_plus_x = Pattern('add', Pattern('x'),  Pattern('x'))
#x_mul_2 = Pattern('mul', Pattern('x'), Pattern('2'))
#opt = Rewrite(x_plus_x, x_mul_2, {'x': 'x'})
#apply_rewrite(eg, opt)
#print(eg.ec)
