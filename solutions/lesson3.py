# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_lesson3.ipynb (unless otherwise specified).

__all__ = ['get_mnist_data', 'stats', 'Lambda', 'GeneralReLU', 'current_gpu', 'AverageStatsCallback', 'accuracy',
           'Hook', 'ListContainer', 'Hooks', 'BatchNorm', 'init_cnn_', 'conv_layer', 'get_model', 'get_runner',
           'RunningBatchNorm']

# Cell
import torch
from torch import nn
from torch.optim import Adam
from solutions.lesson1 import *
from solutions.lesson2 import *
from fastai.datasets import download_data
from torch.functional import F
from functools import partial

# Cell
def get_mnist_data():
    """Returns X_train, y_train, X_test, y_test for MNIST dataset."""
    MNIST_URL='http://deeplearning.net/data/mnist/mnist.pkl'
    path = download_data(MNIST_URL, ext=".gz")
    return get_data(path)

# Cell
def stats(x):
    return x.mean(), x.std()

# Cell
class Lambda(nn.Module):
    def __init__(self, f):
        super().__init__()
        self.f = f

    def forward(self, x):
        return self.f(x)

# Cell
class GeneralReLU(nn.Module):
    def __init__(self, a=0.01, subtract=0.4):
        super().__init__()
        self.a = a
        self.subtract = subtract

    def forward(self, x):
        return F.leaky_relu(x, self.a) - self.subtract

# Cell
def current_gpu():
    print(torch.cuda.get_device_name(torch.cuda.current_device()))

# Cell
class AverageStatsCallback(Callback):
    def __init__(self, f, name):
        self.f = f
        self.name = name

    def on_epoch_start(self):
        self.value = 0.
        self.count = 0

    def on_batch_end(self):
        if runner.mode == ModelMode.VALID:
            batch_count = self.runner.xb.size()[0]
            self.count += batch_count
            self.value += self.f(self.runner.pred, self.runner.yb) * batch_count

    def on_epoch_end(self):
        if runner.mode == ModelMode.VALID:
            print("{} after epoch {}: {}".format(self.name, self.runner.epochs, self.value/self.count))

# Cell
def accuracy(preds, actuals):
    return (torch.argmax(preds, axis=1) == actuals).float().sum()/(preds.size()[0])

# Cell
class Hook:
    def __init__(self, f, m):
        self.f = f
        self.m = m
        self.hook = m.register_forward_hook(partial(f, self))

    def remove(self):
        self.hook.remove()

    def __del__(self): self.remove()

    def __repr__(self): return "Hook(" + self.f.__name__ + ")"

# Cell
class ListContainer:
    def __init__(self, *items):
        self.items = list(items)

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self.items[idx]

        if isinstance(idx, list):
            if len(idx) == 0:
                return []

            if isinstance(idx[0], int):
                return [self.items[i] for i in idx]

            if isinstance(idx[0], bool) and len(idx) == len(self.items):
                return [self.items[i] for i in range(len(self.items)) if idx[i]]

        raise ValueError("idx must be an integer, list of integers, or list of bools.")

    def __setitem__(self, idx, item):
        self.items[idx] = item

    def __iter__(self): return iter(self.items)

    def __repr__(self):
        if len(self.items) <= 10:
            return str(self.items)
        else:
            strs = [str(i) for i in self.items[:10]]
            strs.append("...")
            return str(strs).replace("\'", "")

    def __len__(self): return len(self.items)

    def __str__(self): return self.__repr__()

# Cell
class Hooks(ListContainer):
    def __init__(self, f, model):
        super().__init__(*[Hook(f, l) for l in model])

    def remove(self):
        for hook in self.items: hook.remove()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.remove()

    def __del__(self):
        self.remove()

# Cell
class BatchNorm(nn.Module):
    def __init__(self, nf, eps=1e-5, mom=0.1):
        super().__init__()
        self.eps = eps
        self.mom = mom
        self.gamma = nn.Parameter(torch.ones(nf, 1, 1))
        self.beta = nn.Parameter(torch.zeros(nf, 1, 1))
        self.register_buffer('mean', torch.zeros(1, nf, 1, 1))
        self.register_buffer('var', torch.ones(1, nf, 1, 1))

    def update_stats(self, x):
        mean, var = x.mean(dim=(0,2,3), keepdim=True), x.var(dim=(0,2,3), keepdim=True)
        self.mean.lerp_(mean, self.mom)
        self.var.lerp_(var, self.mom)
        return self.mean, self.var

    def forward(self, x):
        if self.training:
            with torch.no_grad():
                m, v = self.update_stats(x)
        else:
            m, v = self.mean, self.var

        x_hat = (x - m) / (v + self.eps).sqrt()
        return self.gamma * x_hat + self.beta

# Cell
def init_cnn_(mdl):
    for layer in mdl.children():
        if isinstance(layer, nn.Conv2d):
            print("initializing conv2d...")
            nn.init.kaiming_normal_(layer.weight)
            if hasattr(layer, 'bias'):
                nn.init.zeros_(layer.bias)
        if isinstance(layer, nn.Sequential): init_cnn_(layer)

def conv_layer(ni, nf, size, stride=2, bn=True, **kwargs):
    layers = [
        nn.Conv2d(ni, nf, size, stride, padding=size//2),
        GeneralReLU(**kwargs)
    ]
    # TODO: make running bn an choice via args
    if bn: layers.append(RunningBatchNorm(nf))
    return nn.Sequential(*layers)

def get_model():
    conv_layers = [
        conv_layer(1, 8, 5),
        conv_layer(8, 16, 3),
        conv_layer(16, 32, 3),
        conv_layer(32, 64, 3),
        conv_layer(64, 10, 3),
    ]

    mdl = nn.Sequential(
        *conv_layers,
        nn.AdaptiveAvgPool2d(1),
        nn.LogSoftmax(dim=1),
        Lambda(torch.squeeze)
    )

    init_cnn_(mdl)

    return mdl

# Cell
def get_runner(lr, loss, data, cbs):
    mdl = get_model()
    opt = Adam(mdl.parameters(), lr=lr)
    learn = Learn(mdl, opt, data, loss)
    return Runner(learn, cb_funcs=cbs)

# Cell
class RunningBatchNorm(nn.Module):
    def __init__(self, nf, eps=1e-5, mom=0.1):
        super().__init__()
        self.eps = eps
        self.mom = mom
        self.gamma = nn.Parameter(torch.ones(nf, 1, 1))
        self.beta = nn.Parameter(torch.zeros(nf, 1, 1))
        self.register_buffer('counts', torch.tensor(0.))
        self.register_buffer('sum', torch.zeros(1, nf, 1, 1))
        self.register_buffer('sum_squares', torch.zeros(1, nf, 1, 1))
        self.register_buffer('mean', torch.zeros(1, nf, 1, 1))
        self.register_buffer('var', torch.ones(1, nf, 1, 1))
        self.register_buffer('examples', torch.tensor(0.))

    def update_stats(self, x):
        self.sum.detach_()
        self.sum_squares.detach_()
        bs,nc,_,_ = x.size()
        self.examples += bs

        # stats specific to batch
        _sum = x.sum(dim=(0,2,3), keepdim=True)
        _sum_squares = (x*x).sum(dim=(0,2,3), keepdim=True)
        _count = _sum.new_tensor(x.numel()/nc)
        _mom = _sum.new_tensor(1 - (1 - self.mom)/(math.sqrt(bs-1)))

        # linearly interpolated states
        self.sum.lerp_(_sum, _mom)
        self.sum_squares.lerp_(_sum_squares, _mom)
        self.counts.lerp_(_count, _mom)

        # compute aggregate mean and var based on lerp values
        self.mean = self.sum / self.counts
        self.var = self.sum_squares.div(self.counts).sub(self.mean * self.mean)
        if self.examples <= 20: self.var.clip_min_(0.01)

    def forward(self, x):
        if self.training: self.update_stats(x)
        x_hat = (x - self.mean) / (self.var + self.eps).sqrt()
        return self.gamma * x_hat + self.beta