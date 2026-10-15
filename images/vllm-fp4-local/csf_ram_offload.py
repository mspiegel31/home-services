"""Honor vLLM's UVA budget when CSF experts materialize after construction."""

import math

import torch

from vllm.logger import init_logger
from vllm.model_executor.offloader import get_offloader
from vllm.model_executor.offloader.uva import UVAOffloader
from vllm.utils.torch_utils import get_accelerator_view_from_cpu_tensor

logger = init_logger(__name__)


def allocate_packed_weights(shapes, device, layer_name):
    offloader = get_offloader()
    weights = []
    for name, shape in zip(("w13_weight", "w2_weight"), shapes, strict=True):
        targeted = isinstance(offloader, UVAOffloader) and (
            not offloader.cpu_offload_params
            or any(
                f".{segment}." in f".{layer_name}.{name}."
                for segment in offloader.cpu_offload_params
            )
        )
        if targeted and offloader.cpu_offload_bytes < offloader.cpu_offload_max_bytes:
            if not offloader.uva_offloading or not offloader.pin_memory:
                raise RuntimeError("CSF expert RAM offload requires pinned-memory UVA")
            host = torch.zeros(shape, dtype=torch.uint8, device="cpu", pin_memory=True)
            weight = get_accelerator_view_from_cpu_tensor(host)
            offloader.cpu_offload_bytes += math.prod(shape)
            logger.info(
                "CSF RAM expert %s.%s: %.3f GiB; total UVA offload %.3f GiB",
                layer_name,
                name,
                math.prod(shape) / 2**30,
                offloader.cpu_offload_bytes / 2**30,
            )
        else:
            weight = torch.zeros(shape, dtype=torch.uint8, device=device)
        weights.append(weight)
    return tuple(weights)
