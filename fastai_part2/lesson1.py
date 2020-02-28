# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_lesson1.ipynb (unless otherwise specified).

__all__ = ['get_data', 'linear', 'relu', 'mse', 'd_mse', 'd_relu', 'd_linear', 'forward_and_backward', 'test_allclose',
           'Module', 'Loss', 'Model', 'Lin', 'ReLU', 'MSE']

# Cell
from torch import tensor
import torch
import pickle
from fastai.utils import *
from fastai.datasets import *
import gzip
import math
from typing import *

# Cell
def get_data():
  with gzip.open(data_path, mode="rb") as d:
    ((X_train, y_train), (X_valid, y_valid), _) = pickle.load(d, encoding='latin-1')
    X_train, y_train, X_valid, y_valid = map(torch.tensor, (X_train, y_train, X_valid, y_valid))
    return (X_train, y_train, X_valid, y_valid)

# Cell
def linear(w, x, b):
  return x@w + b

# Cell
def relu(z): return z.clamp_min(0.).float()

# Cell
def mse(y, y_hat): return (y_hat - y).pow(2).mean()

# Cell
def d_mse(output, y): output.g =  2.*(output - y) / output.shape[0]
def d_relu(inp, output): inp.g = (inp > 0).float() * output.g

# Cell
def d_linear(inp, output, w, b):
  inp.g = output.g@w.t()
  w.g = inp.t()@output.g
  b.g = output.g.sum(0)

# Cell
def forward_and_backward(x, y):
  # 50k x 1000
  z1 = linear(w1, x, b1)
  # 50k x 1000
  a1 = relu(z1)
  # 50k x 1
  z2 = linear(w2, a1, b2)
  # 1
  mse_ = mse(y, z2)

  # 50k x 1
  d_mse(z2, y)
  d_linear(a1, z2, w2, b2)
  d_relu(z1, a1)
  d_linear(x, z1, w1, b1)
  return mse_

# Cell
def test_allclose(a, b): assert torch.allclose(a, b, rtol=1e-3, atol=1e-5)

# Cell
class Module(object):

  def forward(self, x):
    raise NotImplementedError()

  def backward(self):
    raise NotImplementedError()

  def __call__(self, x):
     return self.forward(x)

# Cell
class Loss(object):
  def forward(self, x, y):
    raise NotImplementedError

  def backward(self):
    raise NotImplementedError

  def __call__(self, x, y):
    return self.forward(x, y)

# Cell
class Model(object):
  def __init__(self, layers: List[Module], loss: Loss):
    self.layers = layers
    self.loss = loss

  def forward(self, x, y):
    self.inp = x
    for l in self.layers: x = l(x)
    x = self.loss(x, y)
    self.out = x
    return x

  def backward(self):
    self.loss.backward()
    for l in self.layers[::-1]: l.backward()

  def __call__(self, x, y):
    return self.forward(x, y)

# Cell
class Lin(Module):
  def __init__(self, w, b):
    self.w = w
    self.b = b

  def forward(self, x):
    self.inp = x
    self.out = x@self.w + self.b
    return self.out

  def backward(self):
    self.inp.g = self.out.g @ self.w.t()
    self.w.g = self.inp.t() @ self.out.g
    self.b.g = self.out.g.sum(0)

class ReLU(Module):
  def forward(self, x):
    self.inp = x
    self.out = x.clamp_min(0).float()
    return self.out

  def backward(self):
    self.inp.g = (self.inp > 0).float() * self.out.g

class MSE(Loss):

  def forward(self, x, y):
    self.inp = x
    self.y = y
    self.out = (x - y).pow(2).mean()
    return self.out

  def backward(self):
    self.inp.g = 2. * (self.inp - self.y) / self.y.shape[0]