from egraph import *

def make_vars(egraph, var_list):
  return [egraph.make(x) for x in var_list.strip().split()]

def get_rewrites():
  a = Pattern('a')
  b = Pattern('b')
  c = Pattern('c')
  add = lambda a, b: Pattern('add', a, b)
  assoc = Rewrite(
      add(a, add(b, c)),
      add(add(a, b), c),
      {'a': 'a', 'b': 'b', 'c':'c'})
  comm = Rewrite(
      add(a, b), add(b, a), {'a': 'a', 'b': 'b'})
  return [assoc, comm]

def test1():
  egraph = EGraph()
  x = egraph.make('x')
  y = egraph.make('y')
  fx = egraph.make('f', x)
  fy = egraph.make('f', y)
  assert not egraph.equal(fx, fy)
  egraph.merge(fx, fy)
  egraph.rebuild()
  assert egraph.equal(fx, fy)

def test_assoc():
  egraph = EGraph()
  x = egraph.make('x')
  y = egraph.make('y')
  z = egraph.make('z')
  add = lambda a, b: egraph.make('add', a, b)
  e1 = add(x, add(y, z))
  e2 = add(add(x, y), z)
  assert not egraph.equal(e1, e2)
  saturate(egraph, get_rewrites())
  assert egraph.equal(e1, e2)

def test_assoc2():
  egraph = EGraph()
  a, b, c, d = make_vars(egraph, 'a b c d')
  add = lambda a, b: egraph.make('add', a, b)
  e1 = add(a, add(b, add(c, d)))
  e2 = add(add(add(a, b), c), d)
  assert not egraph.equal(e1, e2)
  saturate(egraph, get_rewrites())
  assert egraph.equal(e1, e2)

def test_assoc_and_comm():
  egraph = EGraph()
  a, b, c, d = make_vars(egraph, 'a b c d')
  add = lambda a, b: egraph.make('add', a, b)
  e1 = add(a, add(b, add(c, d)))
  e2 = add(d, add(add(a, b), c))
  assert not egraph.equal(e1, e2)
  saturate(egraph, get_rewrites())
  assert egraph.equal(e1, e2)

def run_tests(tests):
  num_passed = 0
  for test in tests:
    print(f'Running {test.__name__}')
    try:
      test()
      num_passed += 1
      print(f'\tpassed')
    except:
      print(f'\tfailed')
  print(f'Passed: {num_passed}/{len(tests)}')
  
run_tests([
  test1, 
  test_assoc,
  test_assoc2,
  test_assoc_and_comm])
