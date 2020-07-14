# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_lesson2.ipynb (unless otherwise specified).

__all__ = ['MNIST_URL', 'path', 'Model', 'logsumexp', 'log_softmax', 'LogSoftmax', 'nograd', 'Optimizer', 'basic_model',
           'Dataset', 'SequentialSampler', 'DataLoader', 'fit', 'Runner', 'Callback', 'Learn', 'ModelMode', 'DataBunch',
           'BasicCallback', 'LinearScheduler', 'lin_scheduler', 'Scheduler', 'CosineScheduler', 'LinearScheduler',
           'CombinedScheduler', 'Recorder']

# Cell
from solutions.lesson1 import *
from fastai.datasets import *
import torch
from torch import nn
import numpy as np
from functools import wraps
from typing import List, Tuple, Callable
from functools import partial
import math

# Cell
MNIST_URL='http://deeplearning.net/data/mnist/mnist.pkl'
path = download_data(MNIST_URL, ext=".gz")
X_train, y_train, X_valid, y_valid = get_data(path)

# Cell
class Model(nn.Module):
    def __init__(self, layers):
        self._modules = {}
        for idx, layer in enumerate(layers):
            self._modules[f'layer{idx}'] = layer

    def __call__(self, x):
        for _, layer in self.named_children(): x = layer(x)
        return x

# Cell
def logsumexp(vec):
    max_elem = vec.max()
    return max_elem + (vec - max_elem).exp().sum(-1).log()

# Cell
def log_softmax(vec):
    return vec - vec.logsumexp(dim=(0,), keepdim=True)

# Cell
class LogSoftmax(nn.Module):
    def forward(self, x):
        self.input = x
        self.output = torch.log_softmax(self.input, dim=-1)
        return self.output

    def backward(self):
        correct_labels = (self.output.grad > 0).float()
        msg = "LogSoftmax must be used with CE loss, found more than one output dim with nonzero gradients for the same example"
        assert correct_labels.sum(axis=0).max() == 1, msg
        self.input.grad = (correct_labels - self.output) * self.output.grad

# Cell
def nograd(f):
    @wraps(f)
    def inner(*args, **kwargs):
        with torch.no_grad():
            return f(*args, **kwargs)
    return inner

# Cell
class Optimizer:
    def __init__(self, model, lr):
        self.hp = {
            "lr": lr
        }
        params = []
        for _, layer in model.named_children():
            if hasattr(layer, 'weight'):
                params.append(layer)
        self.params = params

    @nograd
    def step(self):
        for param in self.params:
            param.weight.sub_(param.weight.grad * self.hp['lr'])
            param.bias.sub_(param.bias.grad * self.hp['lr'])

    @nograd
    def zero_grad(self):
        for param in self.params:
            param.zero_grad()

# Cell
def basic_model(nh, torch_softmax=False):
    return nn.Sequential(
        nn.Linear(784, nh),
        nn.ReLU(),
        nn.Linear(nh, 10),
        nn.LogSoftmax() if torch_softmax else LogSoftmax()
    )

# Cell
class Dataset:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getitem__(self, index):
        return self.x[index], self.y[index]

    def __len__(self):
        return self.x.shape[0]

# Cell
class SequentialSampler:
    def __init__(self, ds):
        self.ds = ds

    def __iter__(self):
        for i in range(len(self.ds)):
            yield(i)

    def __len__(self):
        return len(self.ds)

# Cell
class DataLoader:
    def __init__(self, ds, bs, sampler=None):
        self.ds = ds
        self.bs = bs

        if callable(sampler):
            self.sampler = sampler(ds)
        else:
            self.sampler = sampler or SequentialSampler(ds)

    def __iter__(self):
        it = iter(self.sampler)
        nbatches = math.ceil(len(self) / self.bs)
        for _ in range(nbatches):
            try:
                idxs = []
                for _ in range(self.bs):
                    idxs.append(next(it))
                yield self.ds[idxs]
            except StopIteration:
                yield self.ds[idxs] # flush the final partial batch

    def __len__(self):
        return len(self.ds)

# Cell
def fit(model, optimizer, dl, epochs=1):
    losses = []
    for _ in range(epochs):
        for X_b, y_b in dl:
            pred = model(X_b)
            loss = nll(pred, y_b)
            losses.append(loss.item())

            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
    print(losses[-1])

# Cell
class Runner(object):
    def __init__(self, learn, cbs=None, cb_funcs=None):
        self.learn = learn
        cb_funcs = cb_funcs or []
        cbs = cbs or []
        self.cbs = cbs + [cb_func(self) for cb_func in cb_funcs]

        self.train_losses = []
        self.train_counts = []
        self.valid_losses = []
        self.valid_counts = []

        self.batches = 0

    def train(self):
        self.mode = ModelMode.TRAIN

    def valid(self):
        self.mode = ModelMode.VALID

    def mode(self):
        return self.mode

    def one_batch(self, xb, yb):
        if self('on_batch_start'): return
        self.xb, self.yb = xb, yb
        self.pred = self.learn.model(xb)
        loss = self.learn.loss(self.pred, yb)

        if self.mode == ModelMode.TRAIN:
            self.batches += 1
            self.train_losses.append(loss.item())
            self.train_counts.append(len(xb))
            loss.backward()
            if not self('on_step_start'): self.learn.optimizer.step()
            self.learn.optimizer.zero_grad()
            self('on_step_end')

        if self.mode == ModelMode.VALID:
            self.valid_losses.append(loss.item())
            self.valid_counts.append(len(xb))

        if self('on_batch_end'): return True

    def all_batches(self):
        if self('on_epoch_start'): return
        dl = self.learn.data.train_dl if self.mode == ModelMode.TRAIN else self.learn.data.valid_dl
        for xb, yb in dl:
            self.one_batch(xb, yb)
        self('on_epoch_end')

    def fit(self, epochs=1):
        self.total_batches = math.ceil(len(self.learn.data.train_dl) / self.learn.data.train_dl.bs) * epochs
        self('on_train_start')
        self.epochs = 0
        for _ in range(epochs):
            self.train()
            if self.all_batches(): return

            self.valid()
            if self.all_batches(): return
            print("Validation loss: {0:.4f}".format(self.loss(ModelMode.VALID)))
            self.epochs += 1
        self('on_train_end')

    def loss(self, mode: int):
        if mode == ModelMode.TRAIN:
            values, counts = self.train_losses, self.train_counts
        elif mode == ModelMode.VALID:
            values, counts = self.valid_losses, self.valid_counts
        else:
            raise ValueError("mode must be one of ModelMode.TRAIN or ModelMode.VALID.")

        total = sum(counts)
        weights = [i/total for i in counts]
        return sum([value*weight for value, weight in zip(values, weights)])

    def __call__(self, name):
        for cb in sorted(self.cbs, key=lambda x: x._order):
            f = getattr(cb, name, None)
            if f and f(): return True
        return False

# Cell
class Callback:
    _order = 0

    def on_train_start(self):
        pass

    def on_epoch_start(self):
        pass

    def on_batch_start(self):
        pass

    def on_forward_start(self):
        pass

    def on_forward_end(self):
        pass

    def on_backward_start(self):
        pass

    def on_backward_end(self):
        pass

    def on_batch_end(self):
        pass

    def on_epoch_end(self):
        pass

    def on_train_end(self):
        pass

    def __call__(self, runner: Runner):
        self.runner = runner
        return self

    def __getattr__(self, attr):
        if attr == "runner":
            raise ValueError("No runner has been set; use __call__ to set a runner on this callback.")

# Cell
class Learn:
    def __init__(self, model, optimizer, data, loss):
        self.model = model
        self.optimizer = optimizer
        self.data = data
        self.loss = loss

# Cell
class ModelMode:
    TRAIN = 0
    VALID = 1
    TEST = 2

# Cell
class DataBunch:
    def __init__(self, train_dl, valid_dl, test_dl=None, c=None):
        self.train_dl = train_dl
        self.valid_dl = valid_dl
        self.test_dl = test_dl
        self.c = c

# Cell
class BasicCallback:
    _order = 0

    def __init__(self, runner: Runner):
        self.runner = runner

    def on_batch_end(self):
        print(self.runner.batches)
        if self.runner.batches == 10:
            print("Done!")
            return True

# Cell
class LinearScheduler:
    _order = 0
    def __init__(self, start: float, stop: float, hp: str, runner: Runner):
        self.start = start
        self.stop = stop
        self.runner = runner
        self.hp = hp

    def on_batch_end(self):
        pos = self.runner.batches / self.runner.total_batches
        new_hp = start + (self.stop - self.start) * pos
        self.runner.learn.optimizer.hp[self.hp] = new_hp
        if pos % 0.1 == 0:
            print("The {} is now {}".format(self.hp, new_hp))

# Cell
def lin_scheduler(start: float, stop: float, hp: str) -> partial: return partial(LinearScheduler, start, stop, hp)

# Cell
class Scheduler(Callback):
    pass

class CosineScheduler(Scheduler):
    _order = 0
    def __init__(self, start: float, stop: float, hp: str):
        self.start = start
        self.stop = stop
        self.hp = hp

    def on_batch_end(self, pos: float = None):
        if self.runner.mode == ModelMode.TRAIN:
            pos = pos or float(self.runner.batches) / float(self.runner.total_batches)
            new_hp = self.start + (1 + math.cos(math.pi*(1-pos))) * (self.stop - self.start) / 2
            for param_group in self.runner.learn.optimizer.param_groups:
                param_group[self.hp] = new_hp

class LinearScheduler(Scheduler):
    _order = 0
    def __init__(self, start: float, stop: float, hp: str):
        self.start = start
        self.stop = stop
        self.hp = hp

    def on_batch_end(self, pos: float = None):
        if self.runner.mode == ModelMode.TRAIN:
            pos = pos or self.runner.batches / self.runner.total_batches
            new_hp = self.start + pos * (self.start - self.stop)
            for param_group in self.runner.learn.optimizer.param_groups:
                param_group[self.hp] = new_hp

# Cell
class CombinedScheduler(Scheduler):
    _order = 0
    def __init__(self, percentages: List[float], *scheduler_fns: Callable[[Runner], Scheduler]):
        assert sum(percentages) == 1.
        self.percentages = percentages
        self.intervals = [(percentages[i-1], percentages[i]) for i in range(0,len(percentages))]
        self.phases = self._build_phases(percentages)
        self.scheduler_fns = scheduler_fns
        self.schedulers = None

    def on_batch_end(self):
        if self.runner.mode == ModelMode.TRAIN:
            if self.schedulers is None:
                print("Must build the schedulers by calling build_schedulers(runner) before calling on_batch_end.")

            # all schedulers must refer to the same runner
            assert all([i.runner == self.runner for i in self.schedulers])
            pos = self.runner.batches / self.runner.total_batches
            phase_idx = self._get_phase(pos)
            phase = self.phases[phase_idx]
            scheduler = self.schedulers[phase_idx]
            phase_pct = pos - phase[0]
            phase_size = phase[1] - phase[0]
            effective_pct = phase_pct / phase_size
            scheduler.on_batch_end(effective_pct)

    def _build_phases(self, pcts: List[float]) -> List[Tuple[float, float]]:
        pcts = [0] + pcts
        cumsum = torch.cumsum(torch.tensor(pcts), dim=-1).tolist()
        intervals = [(round(cumsum[i-1], 1), round(cumsum[i], 1)) for i in range(1, len(cumsum))]
        return intervals

    def _get_phase(self, pos: float) -> int:
        for idx, phase in enumerate(self.phases):
            if phase[0] < pos <= phase[1]:
                return idx

    def build_schedulers(self, runner: Runner):
        self.schedulers = [i(runner) for i in self.scheduler_fns]

    def __call__(self, runner: Runner):
        self.runner = runner
        self.build_schedulers(runner)
        return self

# Cell
class Recorder(Callback):
    _order=1

    def __init__(self):
        self.values = []

    def on_batch_end(self):
        if self.runner.mode == ModelMode.TRAIN:
            self.values.append(self.runner.learn.optimizer.hp.copy())