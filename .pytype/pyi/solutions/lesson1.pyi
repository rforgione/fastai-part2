# (generated with --quick)

from typing import Any, List, NoReturn, Tuple

__all__: List[str]
gzip: module
math: module
pickle: module
tensor: module
torch: module

class Lin(Module):
    b: Any
    inp: Any
    out: Any
    w: Any
    def __init__(self, w, b) -> None: ...
    def backward(self) -> None: ...
    def forward(self, x) -> Any: ...

class Loss:
    def __call__(self, x, y) -> Any: ...
    def backward(self) -> NoReturn: ...
    def forward(self, x, y) -> NoReturn: ...

class MSE(Loss):
    inp: Any
    out: Any
    y: Any
    def backward(self) -> None: ...
    def forward(self, x, y) -> Any: ...

class Model:
    inp: Any
    layers: List[Module]
    loss: Loss
    out: Any
    def __call__(self, x, y) -> Any: ...
    def __init__(self, layers: List[Module], loss: Loss) -> None: ...
    def backward(self) -> None: ...
    def forward(self, x, y) -> Any: ...

class Module:
    def __call__(self, x) -> Any: ...
    def backward(self) -> NoReturn: ...
    def forward(self, x) -> NoReturn: ...

class ReLU(Module):
    inp: Any
    out: Any
    def backward(self) -> None: ...
    def forward(self, x) -> Any: ...

def __getattr__(name) -> Any: ...
def d_linear(inp, output, w, b) -> None: ...
def d_mse(output, y) -> None: ...
def d_relu(inp, output) -> None: ...
def forward_and_backward(x, y) -> Any: ...
def get_data(data_path) -> Tuple[nothing, nothing, nothing, nothing]: ...
def linear(w, x, b) -> Any: ...
def mse(y, y_hat) -> Any: ...
def relu(z) -> Any: ...
def test_allclose(a, b) -> None: ...
