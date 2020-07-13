# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_lesson3.ipynb (unless otherwise specified).

__all__ = ['get_mnist_data', 'stats', 'Lambda', 'GeneralReLU', 'init_cnn_', 'conv_layer', 'get_model', 'current_gpu',
           'AccuracyCallback', 'BatchNorm1d']

# Cell
import torch
from torch import nn
from torch.optim import Adam
from solutions.lesson1 import *
from solutions.lesson2 import *
from fastai.datasets import download_data
from torch.functional import F

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
def init_cnn_(mdl):
    for layer in mdl.children():
        if isinstance(layer, nn.Conv2d):
            print("initializing conv2d...")
            nn.init.kaiming_normal_(layer.weight)
            if hasattr(layer, 'bias'):
                nn.init.zeros_(layer.bias)
        if isinstance(layer, nn.Sequential): init_cnn_(layer)

def conv_layer(ni, nf, size, stride=2, **kwargs):
    return nn.Sequential(
        nn.Conv2d(ni, nf, size, stride, padding=size//2),
        GeneralReLU(**kwargs)
    )

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
def current_gpu():
    print(torch.cuda.get_device_name(torch.cuda.current_device()))

# Cell
class AccuracyCallback(Callback):
    def __init__(self, runner):
        self.runner = runner

    def on_epoch_start(self):
        if runner.mode == ModelMode.VALID:
            self.correct = 0
            self.total = 0

    def on_batch_end(self):
        if runner.mode == ModelMode.VALID:
            self.total += self.runner.xb.shape[0]
            preds = torch.argmax(self.runner.pred, axis=1)
            self.correct += (preds == self.runner.yb).int().sum().item()

    def on_epoch_end(self):
        if runner.mode == ModelMode.VALID:
            print("Validation accuracy: {}".format(self.correct/self.total))

# Cell
class BatchNorm1d(nn.Module):
    def __init__(self, size, eps=1e-5, mom=0.1):
        super().__init__()
        self.eps = eps
        self.mom = mom
        self.register_buffer('gamma', torch.ones(size))
        self.register_buffer('beta', torch.zeros(size))
        self.mean = 0
        self.std = 1

    def forward(self, x):
        if self.mean is not None:
            self.mean = x.mean(axis=0) * self.mom + self.mean * (1 - self.mom)
        else:
            self.mean = x.mean(axis=0)

        if self.std is not None:
            self.std = x.std(axis=0) * self.mom + self.std * (1 - self.mom)
        else:
            self.std = x.std(axis=0)

        x_hat = (x - self.mean) / (self.std + self.eps)
        return self.gamma * x_hat + self.beta