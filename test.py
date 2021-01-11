from egraph import EGraph

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

test1()
